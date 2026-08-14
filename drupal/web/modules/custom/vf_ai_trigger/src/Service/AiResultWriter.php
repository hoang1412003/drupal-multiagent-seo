<?php

namespace Drupal\vf_ai_trigger\Service;

use Drupal\Core\Database\Connection;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\node\NodeInterface;
use Drupal\vf_ai_review\AiInputFingerprint;
use Drupal\vf_ai_review\AiReportRenderer;

/**
 * Ghi kết quả AI vào node theo compare-and-set, idempotent theo run_id.
 *
 * VÌ SAO KHÔNG DÙNG JSON:API PATCH: PATCH generic ghi đè bất kể bản đang ghi
 * lên revision nào. Một job chấm revision 10 hoàn tất SAU khi editor đã lưu
 * revision 11 sẽ xoá mất báo cáo của 11 và thay bằng báo cáo của nội dung cũ -
 * lỗi im lặng, không ai thấy, và báo cáo hiển thị lại trông hoàn toàn hợp lệ.
 *
 * Ở đây so sánh và ghi nằm trong CÙNG một transaction có khoá row, nên không
 * tồn tại khe giữa "kiểm tra" và "ghi".
 *
 * Ba kết quả có thể xảy ra, và cả ba đều là kết quả ĐÚNG chứ không phải lỗi:
 * - applied           : ghi thành công, tạo một revision mới.
 * - already_applied   : chính run này đã ghi rồi (client gửi lại vì mất
 *                       response). KHÔNG tạo revision thứ hai.
 * - content_superseded: nội dung đã có revision mới hơn. Từ chối ghi.
 *
 * Phần quyết định (validate/decide) là hàm THUẦN, không phụ thuộc Drupal, nên
 * test được bằng PHP thuần; phần chạm entity nằm riêng trong apply().
 */
class AiResultWriter {

  public const MAX_REQUEST_BYTES = 524288;
  public const MAX_SUGGESTIONS_BYTES = 65536;
  public const MAX_REPORT_JSON_BYTES = 393216;

  /**
   * Bốn field AI duy nhất được phép ghi. Không có field thứ năm.
   */
  public const AI_FIELDS = [
    'field_ai_status',
    'field_ai_score',
    'field_ai_suggestions',
    'field_ai_report_json',
  ];

  private const REQUIRED_KEYS = [
    'run_id',
    'external_content_id',
    'expected_revision_id',
    'content_hash',
    'content_hash_version',
    'status',
    'score',
    'suggestions',
    'report_json',
  ];

  private const STATUSES = ['publish', 'needs_revision', 'rejected'];

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManager,
    private readonly Connection $database,
  ) {}

  /**
   * Kiểm payload. Ném AiResultRequestException khi sai, KHÔNG tự sửa.
   *
   * Cố ý không truncate rồi ghi phần còn lại: ghi một nửa báo cáo là tạo dữ
   * liệu sai mà trông như dữ liệu đúng. Thà từ chối cả request.
   */
  public static function validate(array $body): array {
    $thua = array_diff(array_keys($body), self::REQUIRED_KEYS);
    if ($thua) {
      // Bắt luôn cả moderation_state / title / body ở đây: chúng là "key lạ".
      throw new AiResultRequestException(
        'khoa khong duoc phep: ' . implode(', ', $thua)
      );
    }
    $thieu = array_diff(self::REQUIRED_KEYS, array_keys($body));
    if ($thieu) {
      throw new AiResultRequestException(
        'thieu khoa: ' . implode(', ', $thieu)
      );
    }

    foreach (['run_id', 'external_content_id'] as $khoa) {
      if (!is_string($body[$khoa]) || !preg_match(
        '/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i',
        $body[$khoa]
      )) {
        throw new AiResultRequestException("$khoa phai la UUID");
      }
    }

    if (!is_string($body['expected_revision_id'])
      || !preg_match('/^[1-9][0-9]*$/', $body['expected_revision_id'])) {
      throw new AiResultRequestException('expected_revision_id phai la so nguyen duong');
    }

    if (!is_string($body['content_hash'])
      || !preg_match('/^[0-9a-f]{64}$/', $body['content_hash'])) {
      throw new AiResultRequestException('content_hash phai la 64 hex chu thuong');
    }

    if (!in_array($body['content_hash_version'], [1, 2], TRUE)) {
      throw new AiResultRequestException('content_hash_version chi duoc la 1 hoac 2');
    }

    if (!in_array($body['status'], self::STATUSES, TRUE)) {
      throw new AiResultRequestException('status khong hop le');
    }

    if ($body['score'] !== NULL
      && (!is_numeric($body['score']) || $body['score'] < 0 || $body['score'] > 100)) {
      throw new AiResultRequestException('score phai la NULL hoac so 0-100');
    }

    if (!is_string($body['suggestions'])) {
      throw new AiResultRequestException('suggestions phai la chuoi');
    }
    if (strlen($body['suggestions']) > self::MAX_SUGGESTIONS_BYTES) {
      throw new AiResultRequestException('suggestions vuot qua gioi han');
    }

    if (!is_array($body['report_json'])) {
      throw new AiResultRequestException('report_json phai la object');
    }
    $serialized = json_encode(
      $body['report_json'],
      JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR
    );
    if (strlen($serialized) > self::MAX_REPORT_JSON_BYTES) {
      throw new AiResultRequestException('report_json vuot qua gioi han');
    }

    $body['report_json_serialized'] = $serialized;
    return $body;
  }

  /**
   * Quyết định outcome từ request và trạng thái QUAN SÁT ĐƯỢC của node.
   *
   * $observed = [
   *   'revision_id'     => revision mới nhất hiện tại,
   *   'fingerprint'     => hash nội dung hiện tại theo ĐÚNG version request hỏi,
   *   'platform_run_id' => run_id trong báo cáo đang lưu (NULL nếu chưa có),
   * ]
   *
   * Thứ tự kiểm là có chủ đích: idempotency TRƯỚC conflict. Sau khi ghi xong,
   * revision đã tăng nên so revision sẽ báo content_superseded - nếu kiểm
   * conflict trước, một lần gửi lại do mất response sẽ bị hiểu nhầm thành
   * "nội dung đã đổi" và job bị kết thúc sai.
   */
  public static function decide(array $request, array $observed): string {
    if (!empty($observed['platform_run_id'])
      && hash_equals((string) $observed['platform_run_id'], (string) $request['run_id'])) {
      return 'already_applied';
    }
    if ((string) $observed['revision_id'] !== (string) $request['expected_revision_id']) {
      return 'content_superseded';
    }
    if (!hash_equals((string) $observed['fingerprint'], (string) $request['content_hash'])) {
      return 'content_superseded';
    }
    return 'applied';
  }

  /**
   * Hash nội dung hiện tại của một revision theo đúng phiên bản yêu cầu.
   */
  public static function fingerprintCua(NodeInterface $node, int $version): string {
    return $version === AiInputFingerprint::VERSION
      ? AiInputFingerprint::hash(vf_ai_review_input_fields($node))
      : AiReportRenderer::contentHash(vf_ai_review_hash_fields($node));
  }

  /**
   * run_id đã ghi trong báo cáo hiện tại, NULL nếu chưa có.
   */
  public static function runIdDaGhi(NodeInterface $node): ?string {
    if (!$node->hasField('field_ai_report_json')
      || $node->get('field_ai_report_json')->isEmpty()) {
      return NULL;
    }
    $report = (new AiReportRenderer())->decode(
      (string) $node->get('field_ai_report_json')->value
    );
    $run_id = $report['platform_run_id'] ?? NULL;
    return is_string($run_id) && $run_id !== '' ? $run_id : NULL;
  }

  /**
   * Áp kết quả vào node. Trả ['outcome' => ..., 'applied_revision_id' => ...].
   */
  public function apply(array $body): array {
    $request = self::validate($body);

    $storage = $this->entityTypeManager->getStorage('node');
    $khop = $storage->loadByProperties(['uuid' => $request['external_content_id']]);
    $node = $khop ? reset($khop) : NULL;
    if (!$node instanceof NodeInterface || $node->bundle() !== 'article') {
      throw new AiResultRequestException('khong tim thay article voi UUID do');
    }
    $nid = (int) $node->id();

    // Khoá row node TRƯỚC khi đọc revision mới nhất. Không khoá thì hai
    // callback song song đều thấy cùng một revision và cùng cho là mình đúng.
    $transaction = $this->database->startTransaction();
    try {
      $this->database->query(
        'SELECT nid FROM {node} WHERE nid = :nid FOR UPDATE',
        [':nid' => $nid]
      )->fetchField();

      $storage->resetCache([$nid]);
      $vid = $storage->getLatestRevisionId($nid);
      $latest = $storage->loadRevision($vid);

      $outcome = self::decide($request, [
        'revision_id' => (string) $vid,
        'fingerprint' => self::fingerprintCua($latest, (int) $request['content_hash_version']),
        'platform_run_id' => self::runIdDaGhi($latest),
      ]);

      if ($outcome !== 'applied') {
        return ['outcome' => $outcome, 'applied_revision_id' => NULL];
      }

      $latest->set('field_ai_status', $request['status']);
      $latest->set('field_ai_score', $request['score']);
      $latest->set('field_ai_suggestions', $request['suggestions']);
      $latest->set('field_ai_report_json', $request['report_json_serialized']);
      // KHÔNG chạm moderation_state: hệ thống này không tự xuất bản.
      $latest->setNewRevision(TRUE);
      $latest->setRevisionLogMessage('Ket qua danh gia AI (run ' . $request['run_id'] . ')');
      $latest->setRevisionCreationTime(\Drupal::time()->getRequestTime());
      $latest->setRevisionUserId(0);
      $latest->save();

      return [
        'outcome' => 'applied',
        'applied_revision_id' => (string) $latest->getRevisionId(),
      ];
    }
    catch (\Throwable $e) {
      $transaction->rollBack();
      throw $e;
    }
  }

}

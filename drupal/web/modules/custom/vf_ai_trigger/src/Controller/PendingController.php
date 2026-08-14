<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\node\NodeInterface;
use Drupal\vf_ai_trigger\Service\AiResultWriter;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;

/**
 * Feed các bài đang chờ chấm, dành cho vòng đối soát bên Multi-Agent.
 *
 * CHỈ TRẢ METADATA. Không có title/body/summary trong feed: nếu feed mang
 * toàn văn thì mỗi lần đối soát là một lần sao chép nội dung ra ngoài Drupal,
 * và nội dung đó sẽ nằm trong log/cache của mọi tầng trên đường đi. Bên
 * Multi-Agent fetch đúng revision cần chấm qua JSON:API, không qua feed này.
 *
 * Phân trang theo revision ID tăng dần chứ không theo offset: offset sẽ nhảy
 * mục khi có bài mới chen vào giữa hai trang.
 */
class PendingController extends ControllerBase {

  private const LIMIT_MIN = 1;
  private const LIMIT_MAX = 50;
  private const STATE = 'needs_review';

  public function __construct(
    private readonly EntityTypeManagerInterface $entityTypeManagerService,
  ) {}

  public static function create(ContainerInterface $container): static {
    return new static($container->get('entity_type.manager'));
  }

  public function pending(Request $request): JsonResponse {
    $limit = (int) $request->query->get('limit', self::LIMIT_MAX);
    $limit = max(self::LIMIT_MIN, min($limit, self::LIMIT_MAX));

    $sau = $request->query->get('after_revision_id', '0');
    if (!preg_match('/^\d+$/', (string) $sau)) {
      return $this->khongLuu(['error' => 'after_revision_id phai la so nguyen >= 0'], 400);
    }
    $sau = (int) $sau;

    $storage = $this->entityTypeManagerService->getStorage('node');
    // latestRevision(): bài đã xuất bản rồi tạo bản nháp needs_review có
    // revision mới nhất KHÔNG phải revision mặc định - query mặc định sẽ bỏ
    // sót đúng nhóm bài này.
    $vids = $storage->getQuery()
      ->accessCheck(TRUE)
      ->latestRevision()
      ->condition('type', 'article')
      ->condition('moderation_state', self::STATE)
      ->condition('vid', $sau, '>')
      ->sort('vid', 'ASC')
      ->range(0, $limit)
      ->execute();

    $items = [];
    $cuoi = NULL;
    foreach (array_keys($vids) as $vid) {
      $node = $storage->loadRevision($vid);
      if (!$node instanceof NodeInterface) {
        continue;
      }
      $items[] = [
        'external_content_id' => $node->uuid(),
        'external_revision_id' => (string) $node->getRevisionId(),
        'content_type' => 'cam_nang',
        'langcode' => $node->language()->getId(),
        'content_hash' => AiResultWriter::fingerprintCua($node, 2),
        'content_hash_version' => 2,
        'source_url' => $node->toUrl('canonical', ['absolute' => TRUE])->toString(),
      ];
      $cuoi = (int) $node->getRevisionId();
    }

    return $this->khongLuu([
      'items' => $items,
      // Hết trang thì trả NULL để client biết dừng, không để nó tự đoán bằng
      // cách so count() với limit (sai khi trang cuối vừa đúng bằng limit).
      'next_after_revision_id' => count($items) === $limit ? $cuoi : NULL,
    ]);
  }

  /**
   * Response không được cache: quyền và danh sách chờ đổi theo từng request.
   */
  private function khongLuu(array $payload, int $status = 200): JsonResponse {
    $response = new JsonResponse($payload, $status);
    $response->headers->set('Cache-Control', 'no-store');
    return $response;
  }

}

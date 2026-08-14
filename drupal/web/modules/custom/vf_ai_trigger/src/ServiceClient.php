<?php

namespace Drupal\vf_ai_trigger;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Logger\LoggerChannelFactoryInterface;
use Drupal\Core\Site\Settings;
use GuzzleHttp\ClientInterface;
use GuzzleHttp\Exception\ClientException;

/**
 * Gọi service Multi-Agent. Là NƠI DUY NHẤT module này chạm mạng.
 *
 * Mọi phương thức đều nuốt lỗi và trả về giá trị "không có" thay vì ném:
 * service phụ trợ chết TUYỆT ĐỐI không được làm sập việc lưu bài của editor.
 * Bài bị lọt sẽ được vòng đối soát bên Python bắt lại trong ≤5 phút.
 */
class ServiceClient {

  /**
   * Timeout ngắn, cố ý: endpoint bên kia chỉ làm một lệnh INSERT (vài ms).
   * Quá 2 giây nghĩa là service có vấn đề, và lúc đó chờ thêm chỉ làm editor
   * phải đợi lâu hơn chứ không cứu được gì.
   */
  private const TIMEOUT = 2;

  public function __construct(
    private readonly ClientInterface $httpClient,
    private readonly ConfigFactoryInterface $configFactory,
    private readonly LoggerChannelFactoryInterface $loggerFactory,
  ) {}

  private function baseUrl(): string {
    return rtrim((string) $this->configFactory->get('vf_ai_trigger.settings')
      ->get('service_url') ?: 'http://127.0.0.1:8900', '/');
  }

  /**
   * Token đọc từ settings.php, KHÔNG phải config entity.
   *
   * Config export ra file YAML là lộ secret vào git.
   */
  private function token(): string {
    return (string) Settings::get('vf_ai_service_token', '');
  }

  private function logger() {
    return $this->loggerFactory->get('vf_ai_trigger');
  }

  /**
   * Content type của platform ứng với bundle `article` của Drupal.
   */
  private const CONTENT_TYPE = 'cam_nang';

  /**
   * Payload gửi sang /api/v1/jobs. KHÔNG có `site_id`.
   *
   * Site do service suy ra từ chính credential. Nếu client tự khai site_id,
   * một token bị lộ sẽ ghi được sang site khác - phạm vi truy cập phải là
   * thuộc tính của bí mật, không phải của payload.
   */
  public static function payloadJob(
    string $uuid,
    string $revisionId,
    string $langcode,
    string $hash,
    string $source,
    bool $force,
  ): array {
    return [
      'external_content_id' => $uuid,
      'external_revision_id' => $revisionId,
      'content_type' => self::CONTENT_TYPE,
      'langcode' => $langcode,
      'content_hash' => $hash,
      'content_hash_version' => 2,
      'source' => $source,
      'force' => $force,
    ];
  }

  /**
   * Xếp một job. TRUE nghĩa là service đã nhận (kể cả khi nó báo trùng).
   *
   * 409 (dead_letter) KHÔNG phải lỗi: service đã hiểu đúng request, chỉ là
   * scope này đã bỏ cuộc trước đó (hết MAX_ATTEMPTS) - chặn có chủ đích,
   * không phải sự cố mạng/server. Bắt riêng bằng ClientException TRƯỚC
   * catch(\Throwable) chung, ghi mức notice (không phải warning) và trả FALSE
   * mà không làm Guzzle ném lên trên.
   *
   * 423 nghĩa là quản trị viên đã tạm dừng nhận bài - cũng là trạng thái vận
   * hành bình thường, không phải sự cố; ghi notice để người vận hành thấy lý
   * do bài không được chấm, thay vì để nó im lặng.
   */
  public function guiJob(
    string $uuid,
    string $revisionId,
    string $langcode,
    string $hash,
    string $source = 'event',
    bool $force = FALSE,
  ): bool {
    try {
      $this->httpClient->request('POST', $this->baseUrl() . '/api/v1/jobs', [
        'timeout' => self::TIMEOUT,
        'headers' => ['Authorization' => 'Bearer ' . $this->token()],
        'json' => self::payloadJob($uuid, $revisionId, $langcode, $hash, $source, $force),
      ]);
      return TRUE;
    }
    catch (ClientException $e) {
      $ma = $e->getResponse()->getStatusCode();
      if ($ma === 409) {
        $this->logger()->notice('Node @uuid dang o trang thai dead-letter (da het luot thu), can bam "Cham lai" neu muon thu lai.', [
          '@uuid' => $uuid,
        ]);
        return FALSE;
      }
      if ($ma === 423) {
        $this->logger()->notice('Service dang tam dung nhan bai (intake paused); node @uuid se duoc cham sau khi mo lai.', [
          '@uuid' => $uuid,
        ]);
        return FALSE;
      }
      if ($ma === 401 || $ma === 403) {
        // KHÔNG log token. Chỉ nói rõ đây là vấn đề credential tích hợp, vì
        // triệu chứng nhìn từ ngoài giống hệt "hệ thống chạy đúng, chỉ chậm".
        $this->logger()->warning('Service tu choi credential tich hop (@ma). Kiem lai VF_SERVICE_TOKEN o .env va $settings["vf_ai_service_token"] trong settings.php co khop nhau khong.', [
          '@ma' => $ma,
        ]);
        return FALSE;
      }
      $this->logger()->warning('Khong gui duoc job cho node @uuid: @loi', [
        '@uuid' => $uuid,
        '@loi' => $e->getMessage(),
      ]);
      return FALSE;
    }
    catch (\Throwable $e) {
      $this->logger()->warning('Khong gui duoc job cho node @uuid: @loi', [
        '@uuid' => $uuid,
        '@loi' => $e->getMessage(),
      ]);
      return FALSE;
    }
  }

  /**
   * Trạng thái job mới nhất của node. NULL khi không hỏi được.
   *
   * 404 nghĩa là bài chưa từng có job trong phạm vi site này - trả mảng rỗng
   * trạng thái 'none' chứ không phải NULL, vì NULL nghĩa là "không hỏi được".
   */
  public function trangThai(string $uuid): ?array {
    try {
      $res = $this->httpClient->request(
        'GET',
        $this->baseUrl() . '/api/v1/jobs/by-content/' . rawurlencode($uuid),
        [
          'timeout' => self::TIMEOUT,
          'headers' => ['Authorization' => 'Bearer ' . $this->token()],
        ]
      );
      $data = json_decode((string) $res->getBody(), TRUE);
      return is_array($data) ? $data : NULL;
    }
    catch (ClientException $e) {
      if ($e->getResponse()->getStatusCode() === 404) {
        return ['status' => 'none', 'job_id' => NULL, 'last_error' => NULL];
      }
      return NULL;
    }
    catch (\Throwable $e) {
      return NULL;
    }
  }

}

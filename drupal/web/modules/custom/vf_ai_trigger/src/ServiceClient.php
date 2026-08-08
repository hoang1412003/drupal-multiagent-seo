<?php

namespace Drupal\vf_ai_trigger;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Logger\LoggerChannelFactoryInterface;
use Drupal\Core\Site\Settings;
use GuzzleHttp\ClientInterface;

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
   * Xếp một job. TRUE nghĩa là service đã nhận (kể cả khi nó báo trùng).
   */
  public function guiJob(string $uuid, string $hash, string $source = 'event', bool $force = FALSE): bool {
    try {
      $this->httpClient->request('POST', $this->baseUrl() . '/jobs', [
        'timeout' => self::TIMEOUT,
        'headers' => ['Authorization' => 'Bearer ' . $this->token()],
        'json' => [
          'node_id' => $uuid,
          'content_hash' => $hash,
          'source' => $source,
          'force' => $force,
        ],
      ]);
      return TRUE;
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
   */
  public function trangThai(string $uuid): ?array {
    try {
      $res = $this->httpClient->request('GET', $this->baseUrl() . '/jobs/by-node/' . $uuid, [
        'timeout' => self::TIMEOUT,
        'headers' => ['Authorization' => 'Bearer ' . $this->token()],
      ]);
      $data = json_decode((string) $res->getBody(), TRUE);
      return is_array($data) ? $data : NULL;
    }
    catch (\Throwable $e) {
      return NULL;
    }
  }

}

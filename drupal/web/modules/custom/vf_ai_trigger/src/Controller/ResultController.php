<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\vf_ai_trigger\Service\AiResultRequestException;
use Drupal\vf_ai_trigger\Service\AiResultWriter;
use Symfony\Component\DependencyInjection\ContainerInterface;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;

/**
 * Nhận kết quả đánh giá từ Multi-Agent và ghi theo compare-and-set.
 *
 * Đây là NƠI DUY NHẤT bên ngoài được phép ghi bốn field AI. Không mở JSON:API
 * PATCH cho tài khoản machine: PATCH generic cho phép ghi mọi field và ghi đè
 * bất kể revision, tức là đúng hai thứ thiết kế này sinh ra để chặn.
 */
class ResultController extends ControllerBase {

  public function __construct(
    private readonly AiResultWriter $writer,
  ) {}

  public static function create(ContainerInterface $container): static {
    return new static($container->get('vf_ai_trigger.result_writer'));
  }

  public function results(Request $request): JsonResponse {
    if (strlen($request->getContent()) > AiResultWriter::MAX_REQUEST_BYTES) {
      return $this->tra(['code' => 'request_too_large'], 413);
    }

    try {
      $body = json_decode($request->getContent(), TRUE, 64, JSON_THROW_ON_ERROR);
    }
    catch (\JsonException $e) {
      return $this->tra(['code' => 'invalid_json'], 400);
    }
    if (!is_array($body)) {
      return $this->tra(['code' => 'invalid_json'], 400);
    }

    try {
      $ket_qua = $this->writer->apply($body);
    }
    catch (AiResultRequestException $e) {
      return $this->tra(['code' => 'invalid_request', 'detail' => $e->getMessage()], 400);
    }

    // 409 chứ không phải 200: client PHẢI phân biệt được "đã ghi" với "từ
    // chối vì nội dung đã đổi", vì hai trường hợp đó dẫn tới hai hành động
    // khác nhau (kết thúc job vs kết thúc job ở trạng thái superseded).
    if ($ket_qua['outcome'] === 'content_superseded') {
      return $this->tra(['code' => 'content_superseded'], 409);
    }

    return $this->tra([
      'outcome' => $ket_qua['outcome'],
      'applied_revision_id' => $ket_qua['applied_revision_id'],
    ]);
  }

  private function tra(array $payload, int $status = 200): JsonResponse {
    $response = new JsonResponse($payload, $status);
    $response->headers->set('Cache-Control', 'no-store');
    return $response;
  }

}

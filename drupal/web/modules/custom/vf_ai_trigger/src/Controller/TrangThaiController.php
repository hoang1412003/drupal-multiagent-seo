<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Proxy trạng thái job cho JS trong màn soạn bài.
 *
 * Vì sao qua Drupal chứ không để JS gọi thẳng service: service chỉ nghe trên
 * 127.0.0.1 và cần bearer token — đưa token xuống trình duyệt là phát tán bí
 * mật cho mọi người soạn bài.
 */
class TrangThaiController extends ControllerBase {

  public function trangThai(NodeInterface $node): JsonResponse {
    // Route nhận nid từ URL; service nói chuyện bằng UUID.
    $kq = \Drupal::service('vf_ai_trigger.client')->trangThai($node->uuid());
    if ($kq === NULL) {
      // Không hỏi được service. KHÔNG bịa "none" — đó là nói dối rằng bài
      // chưa từng được xếp hàng.
      return new JsonResponse(['status' => 'khong_ro'], 200);
    }
    return new JsonResponse($kq, 200);
  }

}

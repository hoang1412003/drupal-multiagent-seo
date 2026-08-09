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

    // last_error là message exception thô từ worker Python
    // (f"{e.__class__.__name__}: {e}" trong worker.py), có thể lộ đường dẫn
    // nội bộ, URL, chi tiết hạ tầng. Người chỉ có quyền 'xem bao cao ai'
    // (mặc định là content_editor) chỉ cần biết BÀI CÓ ĐANG ĐƯỢC CHẤM
    // KHÔNG, không cần và không nên thấy stack trace của hạ tầng. Chỉ ai có
    // 'dieu khien ai' — cùng ranh giới quyền dự án đã đặt cho thao tác tốn
    // tiền — mới được xem để chẩn đoán.
    if (!\Drupal::currentUser()->hasPermission('dieu khien ai')) {
      unset($kq['last_error']);
    }

    return new JsonResponse($kq, 200);
  }

}

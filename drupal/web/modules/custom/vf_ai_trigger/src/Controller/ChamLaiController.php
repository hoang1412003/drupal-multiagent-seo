<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;
use Drupal\vf_ai_review\AiInputFingerprint;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Ép chấm lại một bài, kể cả khi nội dung không đổi.
 *
 * Quyền tách riêng ('dieu khien ai', không phải 'xem bao cao ai') vì thao tác
 * này TIÊU TIỀN API THẬT — architecture.md mục 5.7 đã đặt ra ranh giới đó.
 */
class ChamLaiController extends ControllerBase {

  public function chamLai(NodeInterface $node): JsonResponse {
    // Route nhận bất kỳ node: \d+, không lọc theo bundle ở tầng routing.
    // Nút chỉ vẽ trên node 'article' (vf_ai_trigger_form_node_form_alter()
    // chặn từ trước), nhưng ẨN NÚT KHÔNG PHẢI LÀ PHÂN QUYỀN: người có quyền
    // 'dieu khien ai' vẫn gọi thẳng được URL cho bất kỳ node id nào. Nếu
    // không chặn ở đây, họ ép chấm được một node không phải article — tiêu
    // tiền API thật cho một bài mà pipeline không được thiết kế để chấm
    // (_vf_ai_trigger_ban_job() cũng từ chối âm thầm với lý do tương tự).
    // Dùng 403 (không phải 404): node THẬT SỰ TỒN TẠI, chỉ là thao tác này
    // không áp dụng cho bundle của nó — đây là từ chối hành động, không
    // phải "không tìm thấy tài nguyên".
    if ($node->bundle() !== 'article') {
      return new JsonResponse(['ok' => FALSE], 403);
    }

    // Chấm lại ĐÚNG revision đang hiển thị, không phải revision mặc định:
    // người duyệt bấm nút khi đang đọc bản nháp needs_review.
    $hash = AiInputFingerprint::hash(vf_ai_review_input_fields($node));
    $ok = \Drupal::service('vf_ai_trigger.client')->guiJob(
      $node->uuid(),
      (string) $node->getRevisionId(),
      $node->language()->getId(),
      $hash,
      'manual',
      TRUE
    );

    return new JsonResponse(['ok' => $ok], $ok ? 202 : 503);
  }

}

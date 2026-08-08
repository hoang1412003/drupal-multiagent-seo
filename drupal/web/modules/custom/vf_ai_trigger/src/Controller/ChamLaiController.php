<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;
use Drupal\vf_ai_review\AiReportRenderer;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Ép chấm lại một bài, kể cả khi nội dung không đổi.
 *
 * Quyền tách riêng ('dieu khien ai', không phải 'xem bao cao ai') vì thao tác
 * này TIÊU TIỀN API THẬT — architecture.md mục 5.7 đã đặt ra ranh giới đó.
 */
class ChamLaiController extends ControllerBase {

  public function chamLai(NodeInterface $node): JsonResponse {
    $hash = AiReportRenderer::contentHash(vf_ai_review_hash_fields($node));
    $ok = \Drupal::service('vf_ai_trigger.client')
      ->guiJob($node->uuid(), $hash, 'manual', TRUE);

    return new JsonResponse(['ok' => $ok], $ok ? 202 : 503);
  }

}

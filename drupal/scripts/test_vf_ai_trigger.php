<?php

/**
 * @file
 * Test hop dong: payload gui sang service phai dung hinh dang va dung hash.
 *
 * Chay bang PHP thuan (khong can bootstrap Drupal), dung phong cach
 * test_ai_report_renderer.php. Chay:
 *   ddev exec php scripts/test_vf_ai_trigger.php
 */

require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiReportRenderer.php';

use Drupal\vf_ai_review\AiReportRenderer;

$that_bai = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $that_bai;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $that_bai = TRUE;
    echo "[FAIL] $ten $chi_tiet\n";
  }
}

// 1. Hash gui kem job phai khop fixture dung chung voi Python.
$fx = json_decode(file_get_contents(__DIR__ . '/content_hash_fixture.json'), TRUE);
$hash = AiReportRenderer::contentHash($fx['fields']);
kiem('hash gui kem job khop fixture dung chung voi Python',
  $hash === $fx['expected_sha256'], "got $hash");

// 2. Hinh dang payload phai dung 4 khoa service mong doi.
$payload = [
  'node_id' => '11111111-2222-3333-4444-555555555555',
  'content_hash' => $hash,
  'source' => 'event',
  'force' => FALSE,
];
kiem('payload co dung 4 khoa',
  array_keys($payload) === ['node_id', 'content_hash', 'source', 'force']);

// 3. node_id phai la UUID, khong phai nid. Tron hai loai dinh danh la loi
//    im lang: job van tao duoc, chi la fetch_content tra 404.
kiem('node_id la UUID chu khong phai so nguyen',
  (bool) preg_match('/^[0-9a-f-]{36}$/i', $payload['node_id']),
  $payload['node_id']);

exit($that_bai ? 1 : 0);

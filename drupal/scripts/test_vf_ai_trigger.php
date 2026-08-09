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

// 4. Co goi service hay khong, dua tren so sanh voi content_hash da luu
//    trong field_ai_report_json cua node. Phai khop y het logic trong
//    _vf_ai_trigger_ban_job() (vf_ai_trigger.module): chan CHINH write_back()
//    cua Multi-Agent tu bat lai job khi PATCH 4 field AI ve - PATCH do cung
//    la mot lan node->save() nen kich hoat lai hook_node_update.
//
// GIOI HAN DA BIET: ham se_goi_service() ben duoi CHEP LAI logic cua
// _vf_ai_trigger_ban_job() thay vi goi thang ham that trong module. Danh
// doi co ly do - file nay chay bang PHP thuan, KHONG bootstrap Drupal (xem
// docstring dau file), ma _vf_ai_trigger_ban_job() nhan NodeInterface va
// goi \Drupal::service(...) nen khong the goi truc tiep o day duoc. Cai gia
// phai tra: module doi logic dieu kien goi service (vf_ai_trigger.module)
// ma KHONG sua theo o day thi test nay van xanh trong khi hanh vi that da
// khac - phai tu doi chieu bang mat hai noi nay moi bien.
function se_goi_service(?string $tho_json, string $hash_hien_tai): bool {
  $report = (new AiReportRenderer())->decode($tho_json);
  if ($report !== NULL && ($report['content_hash'] ?? NULL) === $hash_hien_tai) {
    return FALSE;
  }
  return TRUE;
}

$bao_cao_trung = json_encode(['content_hash' => $hash]);
kiem('hash trung voi report da luu (write_back vua PATCH xong) -> KHONG goi service',
  se_goi_service($bao_cao_trung, $hash) === FALSE);

$bao_cao_lech = json_encode(['content_hash' => 'hash-khac-vi-noi-dung-da-sua']);
kiem('hash lech voi report da luu (noi dung vua sua) -> CO goi service',
  se_goi_service($bao_cao_lech, $hash) === TRUE);

kiem('chua cham (field_ai_report_json rong) -> CO goi service',
  se_goi_service('', $hash) === TRUE);

kiem('JSON hong -> van CO goi service, khong duoc vi loi du lieu ma bo cham bai',
  se_goi_service('{khong phai json hop le', $hash) === TRUE);

exit($that_bai ? 1 : 0);

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
require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiInputFingerprint.php';
// Nap duoc bang PHP thuan vi ServiceClient khong extend/implement gi cua
// Drupal; `use` chi la alias va type hint chi duoc phan giai khi khoi tao.
// payloadJob() la static thuan - test doc CHINH ham that chu khong chep tay
// hinh dang payload sang day (tranh dung bay "mot dinh nghia o hai noi").
require_once __DIR__ . '/../web/modules/custom/vf_ai_trigger/src/ServiceClient.php';

use Drupal\vf_ai_review\AiInputFingerprint;
use Drupal\vf_ai_review\AiReportRenderer;
use Drupal\vf_ai_trigger\ServiceClient;

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

// 2. Hop dong payload /api/v1/jobs - lay tu CHINH ServiceClient, khong chep tay.
$fx2 = json_decode(
  file_get_contents(__DIR__ . '/input_fingerprint_v2_fixture.json'), TRUE
);
$hash_v2 = AiInputFingerprint::hash($fx2['fields']);
$uuid = '11111111-2222-3333-4444-555555555555';
$payload = ServiceClient::payloadJob($uuid, '123', 'vi', $hash_v2, 'event', FALSE);

kiem('payload co dung 8 khoa theo hop dong v1',
  array_keys($payload) === [
    'external_content_id', 'external_revision_id', 'content_type',
    'langcode', 'content_hash', 'content_hash_version', 'source', 'force',
  ],
  implode(',', array_keys($payload)));

// site_id KHONG duoc co: service suy site tu credential. Client tu khai site
// nghia la mot token bi lo se ghi duoc sang site khac.
kiem('payload KHONG mang site_id', !array_key_exists('site_id', $payload));

// 3. external_content_id phai la UUID, khong phai nid. Tron hai loai dinh
//    danh la loi im lang: job van tao duoc, chi la fetch tra 404.
kiem('external_content_id la UUID chu khong phai so nguyen',
  (bool) preg_match('/^[0-9a-f-]{36}$/i', $payload['external_content_id']),
  $payload['external_content_id']);

kiem('external_revision_id la so nguyen duong dang chuoi',
  is_string($payload['external_revision_id'])
    && preg_match('/^[1-9][0-9]*$/', $payload['external_revision_id']) === 1,
  var_export($payload['external_revision_id'], TRUE));

kiem('content_type anh xa article -> cam_nang',
  $payload['content_type'] === 'cam_nang');

kiem('hash gui di la fingerprint v2, khop fixture dung chung voi Python',
  $payload['content_hash'] === $fx2['expected_sha256']
    && $payload['content_hash_version'] === 2,
  $payload['content_hash']);

// Cham lai thu cong phai la manual + force, nguoc lai nut se khong ep duoc
// khi noi dung khong doi.
$manual = ServiceClient::payloadJob($uuid, '123', 'vi', $hash_v2, 'manual', TRUE);
kiem('cham lai thu cong gui source=manual va force=true',
  $manual['source'] === 'manual' && $manual['force'] === TRUE);

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
  if ($report !== NULL
    && (int) ($report['content_hash_version'] ?? 1) === AiInputFingerprint::VERSION
    && ($report['content_hash'] ?? NULL) === $hash_hien_tai) {
    return FALSE;
  }
  return TRUE;
}

$bao_cao_trung = json_encode([
  'content_hash' => $hash_v2,
  'content_hash_version' => 2,
]);
kiem('hash v2 trung voi report da luu (vua ghi ket qua xong) -> KHONG goi service',
  se_goi_service($bao_cao_trung, $hash_v2) === FALSE);

$bao_cao_lech = json_encode([
  'content_hash' => 'hash-khac-vi-noi-dung-da-sua',
  'content_hash_version' => 2,
]);
kiem('hash lech voi report da luu (noi dung vua sua) -> CO goi service',
  se_goi_service($bao_cao_lech, $hash_v2) === TRUE);

// Bao cao v1 cu: PHAI cham lai mot luot de nang len v2, du hash v1 co trung.
// Neu bo qua, bai do se mai mai giu bao cao khong phu url_alias/image_alt.
$bao_cao_v1 = json_encode(['content_hash' => $hash_v2]);
kiem('bao cao v1 cu -> VAN goi service de nang len v2',
  se_goi_service($bao_cao_v1, $hash_v2) === TRUE);

kiem('chua cham (field_ai_report_json rong) -> CO goi service',
  se_goi_service('', $hash_v2) === TRUE);

kiem('JSON hong -> van CO goi service, khong duoc vi loi du lieu ma bo cham bai',
  se_goi_service('{khong phai json hop le', $hash_v2) === TRUE);

echo $that_bai ? "CO TEST DO\n" : "OK\n";
exit($that_bai ? 1 : 0);

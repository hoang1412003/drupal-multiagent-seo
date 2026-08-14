<?php

/**
 * @file
 * Kiểm role `ai_service` KHÔNG có quyền nguy hiểm.
 *
 * Test này là hàng rào cho một sai lầm rất dễ mắc: cấp thêm quyền "cho tiện"
 * khi debug rồi quên gỡ. Tài khoản machine chạy tự động 24/7 nên mọi quyền
 * thừa đều là bề mặt tấn công thường trực.
 *
 * Chạy (từ drupal/):
 *   ddev drush php:script scripts/test_ai_service_role.php
 */

use Drupal\user\Entity\Role;

require_once __DIR__ . '/configure_ai_service_role_constants.php';

$that_bai = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $that_bai;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $that_bai = TRUE;
    echo "[FAIL] $ten" . ($chi_tiet ? " - $chi_tiet" : '') . "\n";
  }
}

$role = Role::load(VF_AI_SERVICE_ROLE_ID);
kiem('role ai_service ton tai', $role !== NULL);
if ($role === NULL) {
  echo "CO TEST DO - chay configure_ai_service_role.php -- --apply truoc\n";
  exit(1);
}

$dang_co = $role->getPermissions();

kiem(
  'co dung bay quyen trong allowlist, khong hon',
  count(array_diff($dang_co, VF_AI_SERVICE_ROLE_PERMISSIONS)) === 0
    && count(array_diff(VF_AI_SERVICE_ROLE_PERMISSIONS, $dang_co)) === 0,
  'thua: ' . implode(', ', array_diff($dang_co, VF_AI_SERVICE_ROLE_PERMISSIONS))
    . ' | thieu: ' . implode(', ', array_diff(VF_AI_SERVICE_ROLE_PERMISSIONS, $dang_co))
);

// Hang rao thu hai: chan theo DONG TU DAU cua ten quyen, phong khi ai do noi
// long allowlist sau nay.
//
// So khop theo tu dau chu KHONG phai str_contains: `view any unpublished
// content` co chuoi con "publish" nhung la quyen CHI DOC hoan toan vo hai.
// Dung str_contains o day tung lam test do oan - va mot test do oan lau ngay
// se bi nguoi ta tat di, mat luon hang rao that.
$dong_tu_cam = [
  'edit', 'delete', 'create', 'administer', 'bypass', 'revert', 'use',
];
$nguy_hiem = [];
foreach ($dang_co as $quyen) {
  $dau = strtok(strtolower($quyen), ' ');
  if (in_array($dau, $dong_tu_cam, TRUE)) {
    $nguy_hiem[] = $quyen;
  }
}
kiem(
  'khong quyen nao bat dau bang dong tu ghi/quan tri',
  $nguy_hiem === [],
  implode(', ', $nguy_hiem)
);

$cam_tuyet_doi = array_intersect($dang_co, VF_AI_SERVICE_ROLE_PHAI_GO);
kiem(
  'khong co quyen nao trong danh sach cam tuyet doi',
  $cam_tuyet_doi === [],
  implode(', ', $cam_tuyet_doi)
);

kiem(
  'moi quyen deu chi doc hoac thuoc namespace vf ai integration',
  array_reduce($dang_co, fn($ok, $q) => $ok && (
    str_starts_with($q, 'view ')
    || str_starts_with($q, 'access ')
    || $q === 'submit vf ai integration result'
  ), TRUE)
);

kiem('role khong duoc la admin', !$role->isAdmin());

// Chi exit() khi HONG. `drush php:script` coi exit(0) tuong minh la ket thuc
// bat thuong va tra ve status 1, tuc mot bo test xanh se bi bao la do.
echo $that_bai ? "CO TEST DO\n" : "OK\n";
if ($that_bai) {
  exit(1);
}

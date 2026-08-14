<?php

/**
 * @file
 * Tạo/sửa role `ai_service` với ĐÚNG bảy quyền, không hơn.
 *
 * MẶC ĐỊNH LÀ DRY-RUN. Chỉ thay đổi thật khi truyền đúng chữ `--apply`:
 * script này cấp quyền cho một tài khoản máy ghi được vào nội dung, nên
 * "chạy nhầm" phải là chuyện khó xảy ra chứ không phải mặc định.
 *
 * Script KHÔNG tạo user, KHÔNG đổi mật khẩu, KHÔNG chạm UID 1 và KHÔNG tự gán
 * role cho ai. Chủ site tự gán role này cho đúng tài khoản mang tên trong
 * DRUPAL_USER; capability test sau đó là bằng chứng việc gán đã đúng.
 *
 * Chạy (từ drupal/):
 *   ddev drush php:script scripts/configure_ai_service_role.php              # xem trước
 *   ddev drush php:script scripts/configure_ai_service_role.php -- --apply   # áp dụng
 */

use Drupal\user\Entity\Role;

require_once __DIR__ . '/configure_ai_service_role_constants.php';

$args = isset($extra) && is_array($extra) ? $extra : [];
$ap_dung = in_array('--apply', $args, TRUE);

$ton_tai = \Drupal::service('user.permissions')->getPermissions();
$thieu = array_values(array_diff(VF_AI_SERVICE_ROLE_PERMISSIONS, array_keys($ton_tai)));
if ($thieu) {
  echo "[LOI] quyen chua ton tai (module chua bat?): " . implode(', ', $thieu) . "\n";
  echo "Khong thay doi gi.\n";
  return;
}

$role = Role::load(VF_AI_SERVICE_ROLE_ID);
$moi = $role === NULL;
if ($moi) {
  echo "[SE TAO] role '" . VF_AI_SERVICE_ROLE_ID . "'\n";
}

$dang_co = $role === NULL ? [] : $role->getPermissions();
$se_them = array_values(array_diff(VF_AI_SERVICE_ROLE_PERMISSIONS, $dang_co));
$se_go = array_values(array_intersect($dang_co, VF_AI_SERVICE_ROLE_PHAI_GO));
// Bất kỳ quyền nào ngoài allowlist cũng bị gỡ: role này phải khớp CHÍNH XÁC
// danh sách, không được tích luỹ quyền qua thời gian.
$se_go = array_values(array_unique(array_merge(
  $se_go,
  array_diff($dang_co, VF_AI_SERVICE_ROLE_PERMISSIONS)
)));

foreach ($se_them as $quyen) {
  echo "[SE THEM] $quyen\n";
}
foreach ($se_go as $quyen) {
  echo "[SE GO]   $quyen\n";
}
if (!$moi && !$se_them && !$se_go) {
  echo "Role da dung, khong co gi de doi.\n";
}

if (!$ap_dung) {
  echo "\nDRY-RUN. Them `-- --apply` de ap dung that.\n";
  return;
}

if ($moi) {
  $role = Role::create([
    'id' => VF_AI_SERVICE_ROLE_ID,
    'label' => 'AI service (machine)',
  ]);
}
foreach ($se_go as $quyen) {
  $role->revokePermission($quyen);
}
foreach (VF_AI_SERVICE_ROLE_PERMISSIONS as $quyen) {
  $role->grantPermission($quyen);
}
$role->save();

echo "\nDa ap dung. Role '" . VF_AI_SERVICE_ROLE_ID . "' co "
  . count($role->getPermissions()) . " quyen.\n";
echo "Buoc tiep theo (KHONG lam tu dong): gan role nay cho tai khoan trong "
  . "DRUPAL_USER, roi chay capability test de chung minh quyen that su du.\n";

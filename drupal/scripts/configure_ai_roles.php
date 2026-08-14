<?php

/**
 * @file
 * Tạo/sửa ba role MVP: content_editor, site_admin, ai_service.
 *
 * MẶC ĐỊNH LÀ DRY-RUN. Chỉ đổi thật khi truyền đúng chữ `--apply`.
 *
 * Script KHÔNG tạo user, KHÔNG đổi mật khẩu, KHÔNG chạm UID 1 và KHÔNG gán
 * role cho ai. Chủ site tự gán role cho đúng người; test capability và
 * test_ai_roles.php là bằng chứng việc gán đã đúng.
 *
 * FAIL CLOSED: thiếu bất kỳ quyền nào trong ma trận (module chưa bật, workflow
 * chưa tạo) thì dừng và không đổi gì. Cấp một phần sẽ tạo ra role trông như
 * đã cấu hình xong nhưng thật ra thiếu quyền, và lỗi đó chỉ lộ ra lúc chạy.
 *
 * Chạy (từ drupal/):
 *   ddev drush php:script scripts/configure_ai_roles.php               # xem trước
 *   ddev drush php:script scripts/configure_ai_roles.php -- --apply    # áp dụng
 */

use Drupal\user\Entity\Role;

require_once __DIR__ . '/ai_roles_matrix.php';

$args = isset($extra) && is_array($extra) ? $extra : [];
$ap_dung = in_array('--apply', $args, TRUE);

$ton_tai = array_keys(\Drupal::service('user.permissions')->getPermissions());

// Fail closed TRƯỚC khi đổi bất cứ gì.
$thieu = [];
foreach (VF_AI_ROLES as $role_def) {
  foreach ($role_def['phai_co'] as $quyen) {
    if (!in_array($quyen, $ton_tai, TRUE)) {
      $thieu[] = $role_def['id'] . ': ' . $quyen;
    }
  }
}
if ($thieu) {
  print "[LOI] quyen chua ton tai (module chua bat? workflow chua tao?):\n";
  foreach ($thieu as $dong) {
    print "  $dong\n";
  }
  print "Khong thay doi gi.\n";
  return;
}

$co_thay_doi = FALSE;

foreach (VF_AI_ROLES as $role_def) {
  $role = Role::load($role_def['id']);
  $moi = $role === NULL;
  $dang_co = $moi ? [] : $role->getPermissions();

  if ($moi) {
    print "[SE TAO] role '{$role_def['id']}' ({$role_def['label']})\n";
    $co_thay_doi = TRUE;
  }

  $se_them = array_values(array_diff($role_def['phai_co'], $dang_co));

  // Quyền bị cấm luôn gỡ. Với ai_service thì gỡ luôn mọi thứ ngoài allowlist.
  $se_go = array_values(array_intersect($dang_co, $role_def['cam']));
  if (!empty($role_def['khop_chinh_xac'])) {
    $se_go = array_values(array_unique(array_merge(
      $se_go,
      array_diff($dang_co, $role_def['phai_co'])
    )));
  }

  foreach ($se_them as $quyen) {
    print "[SE THEM] {$role_def['id']}: $quyen\n";
    $co_thay_doi = TRUE;
  }
  foreach ($se_go as $quyen) {
    print "[SE GO]   {$role_def['id']}: $quyen\n";
    $co_thay_doi = TRUE;
  }

  if (!$ap_dung) {
    continue;
  }

  if ($moi) {
    $role = Role::create(['id' => $role_def['id'], 'label' => $role_def['label']]);
  }
  // KHÔNG bao giờ bật cờ is_admin: role có cờ đó bỏ qua mọi kiểm tra quyền,
  // và lúc ấy cả ma trận này thành trang trí.
  if (method_exists($role, 'setIsAdmin')) {
    $role->setIsAdmin(FALSE);
  }
  foreach ($se_go as $quyen) {
    $role->revokePermission($quyen);
  }
  foreach ($role_def['phai_co'] as $quyen) {
    $role->grantPermission($quyen);
  }
  $role->save();
}

if (!$co_thay_doi) {
  print "Ba role da dung, khong co gi de doi.\n";
}

if (!$ap_dung) {
  print "\nDRY-RUN. Them `-- --apply` de ap dung that.\n";
  return;
}

print "\nDa ap dung ba role.\n";
print "Buoc tiep theo (KHONG lam tu dong): gan role cho dung tai khoan. "
  . "Script nay khong bao gio tao user hay gan role.\n";

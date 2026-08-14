<?php

/**
 * @file
 * Kiểm ma trận quyền của ba role MVP và in ra bảng đọc được bằng máy.
 *
 * Test này là hàng rào cho một sai lầm rất dễ mắc: cấp thêm quyền "cho tiện"
 * khi debug rồi quên gỡ. Nó chạy được cả trước và sau khi apply, và phải đỏ
 * nếu bất kỳ role nào chạm vào quyền bị cấm.
 *
 * Chạy (từ drupal/):
 *   ddev drush php:script scripts/test_ai_roles.php
 */

use Drupal\user\Entity\Role;

require_once __DIR__ . '/ai_roles_matrix.php';

$that_bai = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $that_bai;
  if ($dieu_kien) {
    print "[PASS] $ten\n";
  }
  else {
    $that_bai = TRUE;
    print "[FAIL] $ten" . ($chi_tiet ? " - $chi_tiet" : '') . "\n";
  }
}

foreach (VF_AI_ROLES as $role_def) {
  $id = $role_def['id'];
  $role = Role::load($id);

  kiem("role '$id' ton tai", $role !== NULL);
  if ($role === NULL) {
    continue;
  }

  $dang_co = $role->getPermissions();

  // Cờ is_admin bỏ qua MỌI kiểm tra quyền. Role nào bật cờ đó thì cả ma trận
  // này không còn ý nghĩa gì.
  kiem("'$id' khong bat co is_admin", !$role->isAdmin());

  $thieu = array_values(array_diff($role_def['phai_co'], $dang_co));
  kiem("'$id' co du quyen toi thieu", $thieu === [], implode(', ', $thieu));

  $pham = array_values(array_intersect($dang_co, $role_def['cam']));
  kiem("'$id' khong co quyen bi cam", $pham === [], implode(', ', $pham));

  if (!empty($role_def['khop_chinh_xac'])) {
    $thua = array_values(array_diff($dang_co, $role_def['phai_co']));
    kiem("'$id' khop CHINH XAC allowlist, khong thua", $thua === [],
      implode(', ', $thua));
  }
}

// Bất biến liên role: ranh giới ghi.
$ai_service = Role::load('ai_service');
if ($ai_service !== NULL) {
  $quyen = $ai_service->getPermissions();
  $ghi = array_filter($quyen, function ($q) {
    $dau = strtok(strtolower($q), ' ');
    return in_array($dau, ['edit', 'delete', 'create', 'administer', 'bypass', 'use'], TRUE);
  });
  kiem(
    'ai_service khong co quyen ghi/quan tri/transition nao',
    $ghi === [],
    implode(', ', $ghi)
  );
  kiem(
    'ai_service chi ghi duoc qua result callback, khong qua JSON:API PATCH',
    !in_array('edit any article content', $quyen, TRUE)
  );
}

$editor = Role::load('content_editor');
if ($editor !== NULL) {
  kiem(
    'content_editor khong ep cham lai duoc (thao tac tieu tien API)',
    !in_array('dieu khien ai', $editor->getPermissions(), TRUE)
  );
}

$site_admin = Role::load('site_admin');
if ($site_admin !== NULL) {
  kiem(
    'site_admin ep cham lai duoc',
    in_array('dieu khien ai', $site_admin->getPermissions(), TRUE)
  );
  kiem(
    'site_admin KHONG tu cap quyen cho chinh minh duoc',
    !in_array('administer permissions', $site_admin->getPermissions(), TRUE)
  );
}

// Bảng đọc được bằng máy, để dán vào evidence.
print "\n--- MA TRAN QUYEN ---\n";
foreach (VF_AI_ROLES as $role_def) {
  $role = Role::load($role_def['id']);
  $so = $role === NULL ? 0 : count($role->getPermissions());
  $admin = $role !== NULL && $role->isAdmin() ? 'yes' : 'no';
  printf("%-16s so_quyen=%-3d is_admin=%s\n", $role_def['id'], $so, $admin);
}

print $that_bai ? "CO TEST DO\n" : "OK\n";
if ($that_bai) {
  exit(1);
}

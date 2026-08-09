<?php

/**
 * Tạo workflow "Kiểm duyệt nội dung" với state needs_review cho Article.
 *
 * State `needs_review` là tín hiệu DUY NHẤT kích hoạt hệ Multi-Agent chấm bài
 * (spec 2026-08-07 mục 4). Hệ thống AI không nằm trong bất kỳ transition nào:
 * chấm xong node vẫn ở needs_review, người duyệt tự quyết.
 *
 * QUAN TRỌNG: script này LUÔN ÉP cấu hình state/transition về đúng như định
 * nghĩa bên dưới, kể cả khi ai đó đã chỉnh tay qua giao diện admin — file
 * này là nguồn sự thật (config-as-code), không phải "tạo nếu chưa có rồi
 * thôi". Vì vậy mỗi state/transition đều in rõ mình đang "tao moi", "giu
 * nguyen", hay "GHI DE" (kèm giá trị cũ -> mới) để người chạy thấy ngay
 * mình vừa mất chỉnh sửa tay nào, thay vì phát hiện ra sau.
 *
 * Chạy lại được nhiều lần (idempotent theo nghĩa: chạy nhiều lần cho cùng
 * một kết quả cuối, không phải "bỏ qua nếu đã tồn tại").
 *
 * Chạy: ddev drush php:script scripts/create_workflow.php
 */

use Drupal\workflows\Entity\Workflow;

/**
 * Dien ta gia tri bool/null de in trong log GHI DE (khong dung tieng Viet
 * co dau trong gia tri de tranh loi encode tren console).
 */
function format_bool($value): string {
  if ($value === NULL) {
    return 'null';
  }
  return $value ? 'true' : 'false';
}

/**
 * So sanh cau hinh CU (truoc khi ghi de) voi cau hinh MOI (dinh nghia trong
 * script) cua 1 state, tra ve nhan mo ta cho dong echo.
 *
 * Chi lam phan ghi de (neu co) HIEN RA - khong doi hanh vi ghi de, viec ep
 * cau hinh ve dung dinh nghia van xay ra nhu cu.
 */
function describe_state_change(bool $is_new, ?array $before, array $cfg): string {
  if ($is_new) {
    return 'tao moi';
  }
  $doi = [];
  if ($before['label'] !== $cfg['label']) {
    $doi[] = "label: '{$before['label']}' -> '{$cfg['label']}'";
  }
  if ((int) $before['weight'] !== (int) $cfg['weight']) {
    $doi[] = "weight: {$before['weight']} -> {$cfg['weight']}";
  }
  if (($before['published'] ?? NULL) !== $cfg['published']) {
    $doi[] = 'published: ' . format_bool($before['published'] ?? NULL) . ' -> ' . format_bool($cfg['published']);
  }
  if (($before['default_revision'] ?? NULL) !== $cfg['default_revision']) {
    $doi[] = 'default_revision: ' . format_bool($before['default_revision'] ?? NULL) . ' -> ' . format_bool($cfg['default_revision']);
  }
  return $doi ? 'GHI DE ' . implode(', ', $doi) : 'giu nguyen';
}

/**
 * Tuong tu describe_state_change() nhung cho transition - script chi ep lai
 * danh sach 'from', khong dong tay label/to cua transition da ton tai.
 */
function describe_transition_change(bool $is_new, ?array $before, array $from): string {
  if ($is_new) {
    return 'tao moi';
  }
  $before_from = $before['from'];
  sort($before_from);
  $new_from = $from;
  sort($new_from);
  if ($before_from === $new_from) {
    return 'giu nguyen';
  }
  return 'GHI DE from: [' . implode(',', $before['from']) . '] -> [' . implode(',', $from) . ']';
}

$id = 'kiem_duyet_noi_dung';

$workflow = Workflow::load($id);
if (!$workflow) {
  $workflow = Workflow::create([
    'id' => $id,
    'label' => 'Kiem duyet noi dung',
    'type' => 'content_moderation',
  ]);
  echo "Da tao workflow: $id\n";
}
else {
  echo "Workflow da ton tai, cap nhat lai: $id\n";
}

$type_plugin = $workflow->getTypePlugin();

// weight: thu tu hien thi trong dropdown, khong phai thu tu chuyen tiep.
$states = [
  'draft' => ['label' => 'Draft', 'published' => FALSE, 'default_revision' => FALSE, 'weight' => 0],
  'needs_review' => ['label' => 'Needs Review', 'published' => FALSE, 'default_revision' => FALSE, 'weight' => 1],
  'published' => ['label' => 'Published', 'published' => TRUE, 'default_revision' => TRUE, 'weight' => 2],
  'archived' => ['label' => 'Archived', 'published' => FALSE, 'default_revision' => TRUE, 'weight' => 3],
];
// Chup lai cau hinh state HIEN TAI truoc khi ghi de, de biet dieu gi thay doi.
$states_before = $type_plugin->getConfiguration()['states'] ?? [];

foreach ($states as $state_id => $cfg) {
  $before = $states_before[$state_id] ?? NULL;
  $is_new = $before === NULL;

  if ($is_new) {
    $type_plugin->addState($state_id, $cfg['label']);
  }
  else {
    $type_plugin->setStateLabel($state_id, $cfg['label']);
  }
  $type_plugin->setStateWeight($state_id, $cfg['weight']);

  echo '  state: ' . $state_id . ' (' . describe_state_change($is_new, $before, $cfg) . ")\n";
}

// Drupal 10.6 KHONG co ham setStateTypeConfiguration() tren WorkflowTypeInterface
// (ban nhap ke hoach dung sai ten ham). published/default_revision phai ghi
// truc tiep vao mang configuration cua plugin roi setConfiguration() lai.
// (Thay doi cua 2 gia tri nay da duoc bao trong dong echo "state:" o tren,
// tinh tu $states_before nen khong can bao lai lan nua o day.)
$configuration = $type_plugin->getConfiguration();
foreach ($states as $state_id => $cfg) {
  $configuration['states'][$state_id]['published'] = $cfg['published'];
  $configuration['states'][$state_id]['default_revision'] = $cfg['default_revision'];
}
$type_plugin->setConfiguration($configuration);

$transitions = [
  'create_new_draft' => ['Create New Draft', ['draft', 'needs_review', 'published'], 'draft'],
  'gui_duyet' => ['Gui duyet', ['draft'], 'needs_review'],
  'publish' => ['Publish', ['needs_review', 'published'], 'published'],
  'archive' => ['Archive', ['published'], 'archived'],
  'khoi_phuc_draft' => ['Khoi phuc ve Draft', ['archived'], 'draft'],
];
// Chup lai cau hinh transition HIEN TAI truoc khi ghi de, cung ly do nhu tren.
$transitions_before = $type_plugin->getConfiguration()['transitions'] ?? [];

foreach ($transitions as $tid => [$label, $from, $to]) {
  $before = $transitions_before[$tid] ?? NULL;
  $is_new = $before === NULL;

  if ($is_new) {
    $type_plugin->addTransition($tid, $label, $from, $to);
  }
  else {
    $type_plugin->setTransitionFromStates($tid, $from);
  }

  echo '  transition: ' . $tid . ' (' . describe_transition_change($is_new, $before, $from) . ")\n";
}

// Ap workflow cho content type Article.
$type_plugin->addEntityTypeAndBundle('node', 'article');

$workflow->save();
echo "Da luu workflow. Article gio co state needs_review.\n";

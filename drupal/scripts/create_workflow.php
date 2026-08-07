<?php

/**
 * Tạo workflow "Kiểm duyệt nội dung" với state needs_review cho Article.
 *
 * State `needs_review` là tín hiệu DUY NHẤT kích hoạt hệ Multi-Agent chấm bài
 * (spec 2026-08-07 mục 4). Hệ thống AI không nằm trong bất kỳ transition nào:
 * chấm xong node vẫn ở needs_review, người duyệt tự quyết.
 *
 * Chạy lại được nhiều lần (idempotent).
 *
 * Chạy: ddev drush php:script scripts/create_workflow.php
 */

use Drupal\workflows\Entity\Workflow;

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
foreach ($states as $state_id => $cfg) {
  if (!$type_plugin->hasState($state_id)) {
    $type_plugin->addState($state_id, $cfg['label']);
  }
  else {
    $type_plugin->setStateLabel($state_id, $cfg['label']);
  }
  $type_plugin->setStateWeight($state_id, $cfg['weight']);
  echo "  state: $state_id\n";
}

// Drupal 10.6 KHONG co ham setStateTypeConfiguration() tren WorkflowTypeInterface
// (ban nhap ke hoach dung sai ten ham). published/default_revision phai ghi
// truc tiep vao mang configuration cua plugin roi setConfiguration() lai.
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
foreach ($transitions as $tid => [$label, $from, $to]) {
  if ($type_plugin->hasTransition($tid)) {
    $type_plugin->setTransitionFromStates($tid, $from);
  }
  else {
    $type_plugin->addTransition($tid, $label, $from, $to);
  }
  echo "  transition: $tid\n";
}

// Ap workflow cho content type Article.
$type_plugin->addEntityTypeAndBundle('node', 'article');

$workflow->save();
echo "Da luu workflow. Article gio co state needs_review.\n";

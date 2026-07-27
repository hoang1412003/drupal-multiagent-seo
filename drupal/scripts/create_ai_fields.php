<?php

/**
 * Tạo 4 field tùy chỉnh trên content type Article, dùng cho hệ Multi-Agent AI.
 *
 * 3 field OUTPUT (Multi-Agent ghi kết quả về): field_ai_status, field_ai_score,
 * field_ai_suggestions. 1 field INPUT (Multi-Agent đọc để chấm SEO/Compliance):
 * field_meta_description. Chi tiết: docs/architecture.md mục 2.3.
 *
 * Chạy: ddev drush php:script scripts/create_ai_fields.php
 */

use Drupal\field\Entity\FieldConfig;
use Drupal\field\Entity\FieldStorageConfig;

function create_field(string $field_name, string $type, string $bundle, string $label, array $storage_settings = []): void {
  if (!FieldStorageConfig::loadByName('node', $field_name)) {
    FieldStorageConfig::create([
      'field_name' => $field_name,
      'entity_type' => 'node',
      'type' => $type,
      'settings' => $storage_settings,
    ])->save();
    echo "Da tao field storage: $field_name ($type)\n";
  }
  else {
    echo "Field storage da ton tai, bo qua: $field_name\n";
  }

  if (!FieldConfig::loadByName('node', $bundle, $field_name)) {
    FieldConfig::create([
      'field_name' => $field_name,
      'entity_type' => 'node',
      'bundle' => $bundle,
      'label' => $label,
    ])->save();
    echo "Da gan field vao bundle '$bundle': $field_name\n";
  }
  else {
    echo "Field da gan vao bundle, bo qua: $field_name\n";
  }
}

// (OUTPUT) Lưu 1 trong 3 giá trị: publish / needs_revision / rejected
create_field('field_ai_status', 'list_string', 'article', 'AI Status', [
  'allowed_values' => [
    'publish' => 'Publish',
    'needs_revision' => 'Needs revision',
    'rejected' => 'Rejected',
  ],
]);

// (OUTPUT) Điểm tổng (0-100) do Aggregator tính
create_field('field_ai_score', 'float', 'article', 'AI Score');

// (OUTPUT) Gợi ý sửa, gom theo từng field
create_field('field_ai_suggestions', 'text_long', 'article', 'AI Suggestions');

// (INPUT) Meta description để SEO/Compliance Agent chấm
create_field('field_meta_description', 'string_long', 'article', 'Meta description');

echo "\nHoan tat tao 4 field.\n";

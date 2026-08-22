<?php

/**
 * @file
 * Tạo 3 bài demo trên Drupal từ file gốc trong `docs/`.
 *
 * Vì sao là script chứ không phải tạo tay: bài demo phải giống hệt nhau giữa
 * máy dev và máy deploy, nếu không thì kết quả chấm hai bên không so được với
 * nhau. Nội dung lấy thẳng từ file đã dùng cho gold set / functional-test nên
 * không có bản chép thứ hai để trôi lệch.
 *
 * Vì sao chạy bằng drush chứ không POST qua JSON:API: tài khoản tích hợp
 * `ai_service` có đúng bảy quyền và KHÔNG được tạo node (cố ý, quyền tối
 * thiểu). Nới quyền cho nó chỉ để nạp dữ liệu mẫu là hỏng đúng thứ đang bảo vệ.
 *
 * Bài được tạo ở trạng thái `draft` và KHÔNG có báo cáo AI — người demo tự
 * chuyển sang "Needs Review" để kích hoạt chấm ngay trước mặt người xem.
 *
 * Chạy lại nhiều lần được: bài đã tồn tại (khớp `title`) thì bỏ qua.
 *
 * Cách chạy trên máy chủ deploy (nginx + php-fpm, repo ở ~/drupal-multiagent-seo):
 *   cd ~/drupal-multiagent-seo/drupal
 *   ../vendor/bin/drush php:script scripts/seed_demo_articles.php
 *
 * Trên máy dev dùng DDEV thì `docs/` KHÔNG được mount vào container, nên phải
 * chỉ đường dẫn khác:
 *   ddev drush php:script /var/www/html/scripts/seed_demo_articles.php -- --docs=<duong-dan-trong-container>
 */

use Drupal\node\Entity\Node;

// Mặc định: docs/ nằm cạnh drupal/ trong cùng repo.
$thu_muc_docs = realpath(__DIR__ . '/../../docs');
foreach ($extra ?? [] as $tham_so) {
  if (str_starts_with($tham_so, '--docs=')) {
    $thu_muc_docs = substr($tham_so, 7);
  }
}

// (đường dẫn tương đối trong docs/, nhãn để in ra)
$bai = [
  'functional-tests/clean/C-008.txt' => 'C-008 · kỳ vọng publish',
  'goldset/raw/G-014.txt' => 'G-014 · kỳ vọng needs_revision',
  'goldset/raw/G-010.txt' => 'G-010 · kỳ vọng rejected',
];

if (!$thu_muc_docs || !is_dir($thu_muc_docs)) {
  echo "LOI: khong tim thay thu muc docs. Dung --docs=<duong-dan>.\n";
  return;
}

foreach ($bai as $duong_dan => $nhan) {
  $file = $thu_muc_docs . '/' . $duong_dan;
  if (!is_file($file)) {
    echo "BO QUA $nhan — khong thay file: $file\n";
    continue;
  }

  // Định dạng file: các dòng "khoá: giá trị", rồi một dòng "---", rồi body HTML.
  [$dau, $body] = explode("\n---\n", file_get_contents($file), 2);
  $truong = [];
  foreach (explode("\n", $dau) as $dong) {
    if (str_contains($dong, ':')) {
      [$k, $v] = explode(':', $dong, 2);
      $truong[trim($k)] = trim($v);
    }
  }

  $da_co = \Drupal::entityQuery('node')
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->condition('title', $truong['title'])
    ->range(0, 1)
    ->execute();
  if ($da_co) {
    printf("DA CO   %s (nid=%s)\n", $nhan, reset($da_co));
    continue;
  }

  $node = Node::create([
    'type' => 'article',
    // Phạm vi dự án là nội dung tiếng Việt và KB RAG lọc theo langcode='vi';
    // để mặc định của site sẽ tạo bài sai ngôn ngữ.
    'langcode' => 'vi',
    'title' => $truong['title'],
    'body' => [
      'value' => trim($body),
      'summary' => $truong['summary'] ?? '',
      // Format chỉ ảnh hưởng lúc HIỂN THỊ: phía Python đọc `body.value` thô
      // qua JSON:API nên việc chấm điểm không phụ thuộc giá trị này.
      'format' => 'basic_html',
    ],
    'field_meta_description' => $truong['meta_description'] ?? '',
    'moderation_state' => 'draft',
  ]);
  if (!empty($truong['url_alias'])) {
    $node->set('path', ['alias' => $truong['url_alias']]);
  }
  $node->save();

  printf("DA TAO  %s\n   nid=%d  %s\n", $nhan, $node->id(), $truong['title']);
}

echo "\nXong. Bai o trang thai 'draft', chua co bao cao AI.\n";
echo "De demo: mo /node/<nid>/edit, chuyen sang 'Needs Review' va luu.\n";

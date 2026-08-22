<?php

/**
 * @file
 * Tạo 3 bài demo trên Drupal từ bản xuất `scripts/demo-articles.json`.
 *
 * Vì sao là script chứ không phải tạo tay: bài demo phải giống hệt nhau giữa
 * máy dev và máy deploy, nếu không thì kết quả chấm hai bên không so được với
 * nhau.
 *
 * Vì sao xuất ra JSON chứ không đọc thẳng file gốc trong `docs/`: sau khi
 * người soạn chèn ảnh, CKEditor viết lại body (thêm `data-entity-uuid`, đổi
 * thứ tự thuộc tính) — body trong CSDL đã khác file `.txt` gốc. `docs/` vẫn là
 * nguồn chuẩn cho việc CHẤM ĐIỂM; file JSON này là bản chụp của đúng ba bài
 * đã chuẩn bị để demo, kèm đường dẫn ảnh.
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
 * ẢNH: file ảnh nằm trong `web/sites/default/files/`, mà thư mục đó bị
 * `.gitignore` loại khỏi repo. Phải chép sang server TRƯỚC khi chạy script này,
 * nếu không bài vẫn tạo được nhưng các thẻ `<img>` sẽ trỏ vào file không tồn
 * tại. Xem `docs/deployment-aws-demo.md` mục 6.7.
 *
 * Cách chạy:
 *   cd <repo>/drupal
 *   drush php:script scripts/seed_demo_articles.php
 */

use Drupal\file\Entity\File;
use Drupal\node\Entity\Node;

$duong_dan_json = __DIR__ . '/demo-articles.json';
if (!is_file($duong_dan_json)) {
  echo "LOI: khong thay $duong_dan_json\n";
  return;
}

$ds_bai = json_decode(file_get_contents($duong_dan_json), TRUE);
if (!is_array($ds_bai)) {
  echo "LOI: demo-articles.json khong doc duoc\n";
  return;
}

/**
 * Tra về entity file cho một URI, tạo mới nếu chưa có bản ghi.
 *
 * File vật lý phải được chép sẵn; hàm này chỉ đăng ký nó với Drupal.
 */
function _vf_demo_file(string $uri): ?File {
  $co = \Drupal::entityTypeManager()->getStorage('file')
    ->loadByProperties(['uri' => $uri]);
  if ($co) {
    return reset($co);
  }
  if (!file_exists($uri)) {
    return NULL;
  }
  $file = File::create(['uri' => $uri, 'status' => 1]);
  $file->save();
  return $file;
}

foreach ($ds_bai as $bai) {
  $da_co = \Drupal::entityQuery('node')
    ->accessCheck(FALSE)
    ->condition('type', 'article')
    ->condition('title', $bai['title'])
    ->range(0, 1)
    ->execute();
  if ($da_co) {
    printf("DA CO   nid=%-4s %s\n", reset($da_co), mb_substr($bai['title'], 0, 50));
    continue;
  }

  $gia_tri = [
    'type' => 'article',
    // Phạm vi dự án là nội dung tiếng Việt và KB RAG lọc theo langcode='vi';
    // để mặc định của site sẽ tạo bài sai ngôn ngữ.
    'langcode' => 'vi',
    'title' => $bai['title'],
    'body' => [
      'value' => $bai['body'],
      'summary' => $bai['summary'] ?? '',
      'format' => $bai['format'] ?? 'basic_html',
    ],
    'field_meta_description' => $bai['meta_description'] ?? '',
    'moderation_state' => 'draft',
  ];

  $node = Node::create($gia_tri);

  if (!empty($bai['url_alias'])) {
    $node->set('path', ['alias' => $bai['url_alias']]);
  }

  $thieu_anh = FALSE;
  if (!empty($bai['hero_image']['uri'])) {
    $file = _vf_demo_file($bai['hero_image']['uri']);
    if ($file) {
      $node->set('field_image', [
        'target_id' => $file->id(),
        'alt' => $bai['hero_image']['alt'] ?? '',
      ]);
    }
    else {
      $thieu_anh = TRUE;
    }
  }

  // Tag phải là term có thật; không tự tạo term mới để tránh đẻ ra bản trùng
  // tên chỉ khác khoảng trắng.
  $ids = [];
  foreach ($bai['tags'] ?? [] as $ten) {
    $tim = \Drupal::entityTypeManager()->getStorage('taxonomy_term')
      ->loadByProperties(['name' => $ten, 'vid' => 'tags']);
    if ($tim) {
      $ids[] = ['target_id' => reset($tim)->id()];
    }
  }
  if ($ids) {
    $node->set('field_tags', $ids);
  }

  $node->save();

  printf("DA TAO  nid=%-4d %s%s\n", $node->id(), mb_substr($bai['title'], 0, 50),
    $thieu_anh ? '   [!] thieu file anh dai dien' : '');
}

echo "\nXong. Bai o trang thai 'draft', chua co bao cao AI.\n";
echo "De demo: mo /node/<nid>/edit, chuyen sang 'Needs Review' va luu.\n";

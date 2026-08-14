<?php

/**
 * @file
 * Allowlist quyền của role `ai_service` - MỘT CHỖ DUY NHẤT.
 *
 * Script cấu hình và script kiểm tra cùng đọc file này. Nếu mỗi bên tự chép
 * một bản, hai bản sẽ trôi lệch và test sẽ xác nhận đúng cái nó tự định nghĩa
 * chứ không phải cái hệ thống thật đang có - đúng lỗi "một con số nằm ở nhiều
 * nơi" mà docs/config-spec.md mục 1 ghi lại như một bài học đã trả giá.
 */

const VF_AI_SERVICE_ROLE_ID = 'ai_service';

/**
 * Bảy quyền, đúng bằng những gì worker thực sự dùng.
 *
 * `view latest version` + `view any unpublished content`: đọc revision
 * needs_review (revision mới nhất KHÔNG phải revision mặc định).
 * `view article revisions`: đọc đúng một revision cũ theo resourceVersion.
 * Ba quyền vf ai: feed, capabilities, ghi kết quả.
 */
const VF_AI_SERVICE_ROLE_PERMISSIONS = [
  'access content',
  'view any unpublished content',
  'view latest version',
  'view article revisions',
  'access vf ai integration feed',
  'access vf ai integration capabilities',
  'submit vf ai integration result',
];

/**
 * Quyền phải GỠ nếu role cũ từng có.
 *
 * Tài khoản machine ghi bốn field AI qua result callback, không cần và không
 * được sửa nội dung bài.
 */
const VF_AI_SERVICE_ROLE_PHAI_GO = [
  'edit any article content',
  'create article content',
  'delete any article content',
  'administer nodes',
  'bypass node access',
];

<?php

/**
 * @file
 * Ma trận quyền của ba role MVP — MỘT CHỖ DUY NHẤT.
 *
 * `configure_ai_roles.php` và `test_ai_roles.php` cùng đọc file này. Mỗi bên
 * tự chép một bản thì hai bản sẽ trôi lệch và test sẽ xác nhận đúng cái nó tự
 * định nghĩa chứ không phải cái hệ thống thật đang có.
 *
 * Workflow của dự án là `kiem_duyet_noi_dung` (KHÔNG phải `editorial` mặc
 * định của Drupal): nó là workflow duy nhất có state `needs_review`, và
 * `gui_duyet` là transition đưa bài sang trạng thái đó.
 */

const VF_WORKFLOW_ID = 'kiem_duyet_noi_dung';

/**
 * Người viết. MVP không có người duyệt riêng — người viết cũng duyệt
 * (`docs/technical-debt.md` mục 8.9), nên role này CÓ transition `publish`.
 *
 * Nhưng chỉ publish QUA WORKFLOW. Không có `bypass node access` hay
 * `administer nodes`, nên không thể xuất bản vòng qua quy trình kiểm duyệt —
 * đó mới là "publish bypass" mà thiết kế cấm.
 */
const VF_ROLE_CONTENT_EDITOR = [
  'id' => 'content_editor',
  'label' => 'Content editor',
  'phai_co' => [
    'access content',
    'access content overview',
    'create article content',
    'edit own article content',
    'view own unpublished content',
    'view all revisions',
    'view latest version',
    'use kiem_duyet_noi_dung transition create_new_draft',
    'use kiem_duyet_noi_dung transition gui_duyet',
    'use kiem_duyet_noi_dung transition publish',
    'xem bao cao ai',
  ],
  'cam' => [
    // Bấm "Chấm lại" tiêu tiền API thật -> tách sang site_admin.
    'dieu khien ai',
    'administer users',
    'administer permissions',
    'administer nodes',
    'bypass node access',
    'administer site configuration',
    // Ba quyền machine: người thật không bao giờ cần.
    'access vf ai integration feed',
    'access vf ai integration capabilities',
    'submit vf ai integration result',
  ],
];

/**
 * Chủ site. Quản trị nội dung/workflow và được phép ép chấm lại.
 *
 * CỐ Ý không phải role `administrator`: role đó có cờ is_admin nên bỏ qua mọi
 * kiểm tra quyền, và lúc đó ma trận này thành vô nghĩa.
 *
 * Cũng KHÔNG có `administer permissions`: một người tự cấp được mọi quyền cho
 * chính mình thì thực chất là administrator, chỉ khác cái tên.
 */
const VF_ROLE_SITE_ADMIN = [
  'id' => 'site_admin',
  'label' => 'Site admin',
  'phai_co' => [
    'access content',
    'access content overview',
    'access administration pages',
    'access toolbar',
    'view the administration theme',
    'administer nodes',
    'administer url aliases',
    'view all revisions',
    'revert all revisions',
    'view own unpublished content',
    'view any unpublished content',
    'view latest version',
    'use kiem_duyet_noi_dung transition create_new_draft',
    'use kiem_duyet_noi_dung transition gui_duyet',
    'use kiem_duyet_noi_dung transition publish',
    'use kiem_duyet_noi_dung transition archive',
    'xem bao cao ai',
    'dieu khien ai',
  ],
  'cam' => [
    'administer permissions',
    'bypass node access',
    'access vf ai integration feed',
    'access vf ai integration capabilities',
    'submit vf ai integration result',
  ],
];

/**
 * Tài khoản máy. Allowlist PHẢI khớp chính xác Plan 4 — script này không được
 * nới rộng thêm quyền nào so với `configure_ai_service_role.php`.
 */
const VF_ROLE_AI_SERVICE = [
  'id' => 'ai_service',
  'label' => 'AI service (machine)',
  'phai_co' => [
    'access content',
    'view any unpublished content',
    'view latest version',
    'view article revisions',
    'access vf ai integration feed',
    'access vf ai integration capabilities',
    'submit vf ai integration result',
  ],
  'cam' => [
    'edit any article content',
    'create article content',
    'delete any article content',
    'administer nodes',
    'administer users',
    'administer permissions',
    'bypass node access',
    'dieu khien ai',
    'use kiem_duyet_noi_dung transition publish',
    'use kiem_duyet_noi_dung transition gui_duyet',
  ],
  // Chỉ role này bị ép khớp CHÍNH XÁC: nó chạy tự động 24/7 nên mọi quyền
  // thừa là bề mặt tấn công thường trực. Hai role người dùng thì `phai_co` là
  // sàn tối thiểu, chủ site được thêm quyền vận hành khác.
  'khop_chinh_xac' => TRUE,
];

const VF_AI_ROLES = [
  VF_ROLE_CONTENT_EDITOR,
  VF_ROLE_SITE_ADMIN,
  VF_ROLE_AI_SERVICE,
];

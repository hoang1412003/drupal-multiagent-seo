# Brief thiết kế Stitch — Console (giai đoạn 1)

**Ngày:** 2026-08-19 · **Nguồn dữ liệu:** `multiagent/console_ui/openapi.json`

Sáu prompt dưới đây dùng cho <https://stitch.withgoogle.com>. Mỗi prompt copy
nguyên khối, dán vào Stitch, **không đính kèm ảnh nào**.

## Cách dùng

1. Mỗi màn hình một prompt. Dán trọn cả bốn khối `CONTEXT` / `DATA` /
   `CONTROLS+STATES` / `STYLE`.
2. Khối `STYLE` **giống hệt nhau ở cả sáu prompt** và được chép đầy đủ trong
   từng prompt — không viết "như prompt trên", vì bạn copy từng prompt riêng lẻ.
3. Không đính kèm ảnh admin cũ. Chủ dự án muốn Stitch thiết kế lại tự do.
   Hệ quả: **prompt là ràng buộc duy nhất**, nên phần `DATA` phải giữ nguyên
   văn — mọi tên trường trong đó đều lấy từ `openapi.json`.

## Vì sao mỗi prompt có khối NAVIGATION và FORBIDDEN ACTIONS

Đợt thiết kế đầu (2026-08-20) cho thấy: nếu prompt chỉ mô tả **một màn hình**
mà không nói gì về khung ứng dụng bao quanh, Stitch sẽ **tự bịa một menu admin
nghe hợp lý** — "Quản lý Site", "Policy AI", "Lịch sử hệ thống" — và bỏ mất
Reviews. Nó cũng vẽ nút "Tạo Job Mới" dù API không có endpoint tạo job.

Bịa ra thứ không tồn tại nguy hiểm hơn vẽ xấu: Antigravity sẽ code theo thiết
kế, và bạn chỉ phát hiện khi bấm vào một menu dẫn tới hư không.

Khối `VIETNAMESE LABELS` cũng sinh từ cùng đợt đó: `queued` bị dịch thành
"Chờ duyệt", hàm ý có người phải bấm duyệt — hệ thống không hề có bước đó.

## Giá trị bộ lọc lấy từ API, không viết cứng

Ba dropdown (Trạng thái, Site, Nguồn) và dropdown Quyết định đều nạp từ một lời
gọi `GET /api/console/v1/filters`. Không viết cứng danh sách nào trong giao diện.

Lý do rất cụ thể: enum trạng thái **không nằm trong `openapi.json`** (`status`
khai là `str`), nên một danh sách viết cứng bị sai sẽ không phép kiểm nào bắt
được. Chính brief này từng ghi `succeeded` trong khi giá trị thật là `done`, và
chỉ lộ ra khi nhìn dữ liệu thật.

## Vì sao khối STYLE có một danh sách cấm

Mọi công cụ sinh giao diện đều mặc định trả về trang kiểu tiếp thị: hero
section, minh họa, số KPI cỡ lớn, biểu đồ tròn. Đó là thứ chiếm đa số trong dữ
liệu huấn luyện. Đối trọng duy nhất có tác dụng là một danh sách phủ định tường
minh, kèm một ràng buộc mật độ đo được (15 dòng bảng ở 1440px).

---

## 1. Login

```
CONTEXT
Login screen for an internal admin console of an AI content-review platform used
by staff at an EV company. Desktop-first. Single centred card on an otherwise
empty page. This is a work tool behind the firewall, not a public product page.
All UI labels in Vietnamese.

DATA
Only three inputs exist. Do not invent "remember me", SSO buttons, social login,
"forgot password", or a sign-up link — none of them are implemented.
- Tên đăng nhập (username, text)
- Mật khẩu (password, masked)
- Nút "Đăng nhập" (primary action)
On success the server returns: username, role (one of viewer/operator/admin),
must_change_password (boolean). When must_change_password is true the user is
sent straight to the change-password screen — design that redirect state as a
brief inline notice, not a modal.

CONTROLS + STATES — design all four:
1. Idle
2. Submitting (button shows a spinner and is disabled)
3. Error — a single inline banner above the form reading "Thông tin đăng nhập
   không hợp lệ". IMPORTANT: the same message is used whether the username does
   not exist or the password is wrong, so do NOT design separate per-field error
   states for these two cases.
4. Rate limited — banner reading "Tạm thời chưa thể đăng nhập. Vui lòng thử lại
   sau." with the submit button disabled.

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## 2. Dashboard

```
CONTEXT
Operations overview for an internal AI content-review platform. First screen
after login. The reader is an operator checking whether the pipeline is healthy
right now. Desktop-first, data-dense. All UI labels in Vietnamese.

DATA — show EXACTLY these, no invented metrics:
- Khoảng thời gian: date_from and date_to (YYYY-MM-DD). Defaults to the last 7
  days. Both dates are always required together.
- Hàng đợi (queue_counts): a count per job status. There are FIVE statuses,
  not four: queued / running / failed / done / superseded. Note it is "done",
  NOT "succeeded" — do not rename it. Render as a compact inline row, NOT as
  large KPI cards.
  CRITICAL — this block is NOT filtered by the date range. It is an all-time
  count of the job queue, while every other number on this screen is scoped to
  the selected dates. Label it explicitly (e.g. "Hàng đợi hiện tại — toàn thời
  gian") and visually separate it from the date-scoped section, otherwise a
  reader will assume both cover the same period and conclude the numbers are
  broken.
- Tổng số review (total_reviews): one integer. Scoped to the date range AND
  it EXCLUDES seeded test data (rows with is_fixture = true). The Reviews list
  screen does NOT exclude them, so the two screens will disagree — e.g. 5 here
  versus 13 there. Put a short caption under the date-scoped section saying it
  covers the selected range and excludes dữ liệu mẫu, so the difference reads
  as intentional rather than as a bug.
- Quyết định (decision_counts): counts per decision — publish, needs_revision,
  rejected, unknown.
- Thời lượng: duration_p50_ms and duration_p95_ms (milliseconds, may be null).
  Label them as trung vị / phân vị 95, and show "—" when null.
- Ghi ngược (writeback_counts) plus writeback_success_rate (a ratio 0..1, may be
  null; render as a percentage).
- Chi phí ước tính (cost_estimate): input_tokens, output_tokens, estimated_usd
  (may be null), currency, pricing_version, effective_at (the date that price
  table took effect — show it as a small caption under the cost, so a reader can
  tell an estimate was priced with an old table), source (a URL to the vendor
  pricing page — render it as a small external link, not as raw text), and
  unknown_models (a list of model names with no price on file — show a quiet
  warning when this list is not empty).
- Trạng thái worker: worker_status is exactly one of running / stale /
  unavailable. These are THREE DISTINCT states, not two — "stale" means it was
  running and has gone quiet, "unavailable" means it has never reported. Show
  them differently. Also worker_running, worker_stale (integers) and
  worker_last_seen_at (timestamp, may be null).
- Trạng thái connector: connector_status (a short string).

CONTROLS + STATES:
Controls are two date inputs (Từ ngày / Đến ngày) and an apply button. No
export, no auto-refresh toggle, no chart type switcher.
Design all four states:
1. Loading (skeleton blocks)
2. Empty — no reviews in range: "Không có dữ liệu trong khoảng đã chọn"
3. Error — inline banner
4. Invalid range — the API rejects a reversed range or only one date; show an
   inline validation message next to the date inputs.

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## 3. Jobs (danh sách)

```
CONTEXT
Job queue list for an internal AI content-review platform. An operator scans it
to find failures and retry them. Desktop-first, data-dense, this is the screen
people keep open all day. All UI labels in Vietnamese.

DATA — the table must show EXACTLY these columns, no others, no invented ones:
- Mã job        (public_id, UUID, shown shortened, monospace)   e.g. "a3f2…9c41"
- Thời gian tạo (created_at, ISO-8601 UTC)                      e.g. "19/08/2026 14:32"
- Site          (site_slug, short string)                       e.g. "vinfast-vn"
- ID nội dung   (external_content_id, string)                   e.g. "node-1842"
- Trạng thái    (status — a badge with EXACTLY these FIVE values, no others):
                queued / running / failed / done / superseded
                It is "done", NOT "succeeded". "superseded" means a newer job
                replaced this one.
- Số lần thử    (attempts, integer, right-aligned)              e.g. 2
- Nguồn         (source, short string)                          e.g. "event", "admin_retry"
- Phiên bản policy (policy_version, string)                     e.g. "cam-nang-vn-v1"
There is NO title column and NO author column — the platform does not store them.
Rows are NOT clickable as a whole; the Mã job cell is the link to the detail
screen.

CONTROLS + STATES:
Filters: Trạng thái (dropdown), Site (dropdown), Nguồn (dropdown), ID nội dung
(text, substring match), and a date range (Từ ngày / Đến ngày — both required
together or both empty).
All three dropdowns are populated from a single call to GET /filters, so none
of their values are hard-coded in the UI. Design each with a "Tất cả" option as
the default. Site options carry a slug, a display name, and an `active` flag —
show the name, and mark inactive sites with a muted "đã tắt" tag rather than
hiding them, because their historical jobs are still in the list. Nguồn values
are free-form strings from real data (e.g. "event", "reconcile", "admin_retry",
"manual-test-b7"), so the dropdown must tolerate an unfamiliar value and a list
that grows over time.
Pagination: "Trang 1 / 3 · 137 kết quả" with previous/next. Page size is 25 by
default and capped at 100. There is no infinite scroll and no export button.
Design all four states:
1. Loading (skeleton rows)
2. Empty ("Chưa có job nào khớp bộ lọc")
3. Error (inline banner with retry)
4. Invalid filter — the API returns a validation message; show it above the
   table while KEEPING the filter values the user typed.

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## 4. Job detail

```
CONTEXT
Detail screen for one job in an internal AI content-review platform. The reader
is diagnosing why a job failed and deciding whether to retry it. Desktop-first.
All UI labels in Vietnamese.

DATA — show EXACTLY these 22 fields, grouped as suggested, nothing invented:
Nhận dạng: public_id (UUID, monospace), correlation_id (UUID, monospace),
  supersedes_job_public_id (UUID or null — when present, label it "Thay thế cho
  job" and make it a link).
Trạng thái: status (badge: queued / running / failed / done / superseded —
  five values, and it is "done" NOT "succeeded"), attempts
  (integer), source (string), last_error (long free text, may be null — this is
  the field the reader came for, give it room and a monospace face).
Thời gian: created_at, updated_at (both ISO-8601 UTC).
Nội dung: external_content_id, external_revision_id (may be null), content_type,
  langcode.
Ngữ cảnh: site_slug, site_name, site_id (UUID), profile_id (UUID),
  policy_version.
Kết quả: run_public_id (UUID or null — link to the review detail screen when
  present), run_scored_at (timestamp or null), writeback_status (one of
  succeeded / failed / superseded / pending / unknown, or null),
  saved_result_available (boolean).
When a value is null show "—", never an empty cell and never "N/A".

CONTROLS + STATES:
One action only: a "Thử lại" button, and it appears ONLY when status = failed.
It is hidden entirely for the viewer role (visible to operator and admin).
The "Thử lại" action opens a confirmation dialog before it fires. The dialog
states that retrying re-runs the paid AI pipeline and may incur cost, has an
optional "Lý do" text field, and requires an explicit confirm click. Design both
the dialog and its submitting state. Retrying creates a NEW job, so after
success the screen navigates to that new job — show a brief confirmation of that.
Design all five states:
1. Loading
2. Loaded, status failed (retry available)
3. Loaded, status done or running (no retry button at all)
4. Not found — "Không tìm thấy job"
5. Conflict — retry rejected because the job is no longer failed: inline banner
   "Không thể thử lại job này."

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## 5. Reviews (danh sách)

```
CONTEXT
List of completed AI review results for an internal content-review platform. An
editor scans it to find articles the AI flagged. Desktop-first, data-dense.
All UI labels in Vietnamese.

DATA — the table must show EXACTLY these columns, no others, no invented ones:
- Mã review     (public_id, UUID, shortened, monospace)
- Thời gian chấm (scored_at, ISO-8601 UTC)
- Site          (site_slug)
- ID nội dung   (external_content_id)
- Quyết định    (decision — a badge with EXACTLY four possible values, and it
                may also be null): publish / needs_revision / rejected / unknown
- Điểm          (final_score, a number 0..100, MAY BE NULL — show "—" when null,
                right-aligned, monospace). The API returns full precision, up
                to 13 decimal places (a real value is 40.9090909090909). Round
                to ONE decimal place for display; showing the raw value makes
                the column ragged and unreadable.
- Hồ sơ         (profile_code, short string)
- Phiên bản policy (policy_version)
- Model         (model, e.g. "claude-sonnet-4-5-20250929" — this string is long,
                truncate with an ellipsis and show the full value on hover)
- Dữ liệu mẫu   (is_fixture, boolean — when true the row is seeded test data, not
                a real review. Mark it with a small neutral "mẫu" tag; do NOT
                hide the row and do NOT colour it like an error.)

CONTROLS + STATES:
Filters: Quyết định (dropdown), Site (dropdown), ID nội dung (text, substring
match), and a date range (both dates required together or both empty).
Both dropdowns are populated from GET /filters — the same call the Jobs screen
makes — so no value is hard-coded. Each has a "Tất cả" default. Pagination
identical to the Jobs screen. No export button.
NOTE: this list does NOT exclude seeded test data, and it is not date-scoped by
default — so its total will not match the Dashboard's "Tổng số review".
Design all four states:
1. Loading (skeleton rows)
2. Empty ("Chưa có review nào khớp bộ lọc")
3. Error (inline banner with retry)
4. Invalid filter — validation message above the table, filter values preserved.

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## 6. Review detail

```
CONTEXT
Detail of one AI review result for an internal content-review platform. This is
the densest screen in the product: an editor reads it to understand why the AI
reached its decision. Desktop-first. All UI labels in Vietnamese.

DATA — show EXACTLY these 28 fields, grouped as suggested, nothing invented:
Kết luận: decision (badge: publish / needs_revision / rejected / unknown, may be
  null), final_score (number 0..100, may be null — the API returns full
  precision, up to 13 decimal places; round to one decimal for display),
  veto_reason (text or null —
  when present this is WHY the decision was forced, so give it prominence),
  note (text or null), missing_agents (a list of agent names that did not
  report — when non-empty this is a warning, the result is incomplete).
Kết quả từng agent (agents): a list of AT MOST FOUR agents. Each agent has:
  - name (string, e.g. content_quality / seo / brand / compliance)
  - score (a number, a string, or null — do not assume it is always numeric)
  - criteria (a list of rows; each row is an object with a "criterion" label and
    a "value")
  - issues (a list of rows)
  - evidence (a list of rows)
  criteria / issues / evidence are free-form key–value rows whose keys vary
  between agents. Design them as a compact definition list that tolerates
  arbitrary labels and long values, NOT as a fixed-column table. Some values are
  the literal text "[đã ẩn]" (redacted) — render that as a neutral muted chip.
Vận hành: duration_ms (integer, may be null), model (string), usage_available
  (boolean), cost_estimate (input_tokens, output_tokens, estimated_usd may be
  null, currency, pricing_version, effective_at, source — a URL to the vendor
  pricing page, render as a small external link — and unknown_models list).
Ghi ngược: writeback_status (one of succeeded / failed / superseded /
  pending / unknown), writeback_error (text or null).
Ngữ cảnh: public_id, correlation_id, scored_at, site_id, site_slug, site_name,
  profile_id, profile_code, policy_version, external_content_id,
  external_revision_id (may be null), content_type, langcode, is_fixture
  (boolean), config_meta (an arbitrary JSON object — render collapsed by
  default), drupal_url (a link to the article on the Drupal site, may be null).
When a value is null show "—".

CONTROLS + STATES:
This screen is READ-ONLY. There is no approve button, no reject button, no
comment box, no edit action — none of them exist in the API.
The only interactive elements are: collapse/expand per agent, collapse/expand
for config_meta, and the external link to drupal_url.
Design all five states:
1. Loading
2. Loaded, all four agents present
3. Loaded, missing_agents non-empty — a warning banner that the result is partial
4. Loaded, veto_reason present — the decision was forced; make that visually
   unmistakable
5. Not found — "Không tìm thấy review"

NAVIGATION — the app shell around this screen. Do NOT invent menu items.
The left/top navigation has EXACTLY three destinations, in this order:
  Tổng quan · Jobs · Reviews
Nothing else exists. Do NOT add "Quản lý Site", "Nguồn dữ liệu", "Policy AI",
"Lịch sử hệ thống", "Báo cáo", "Cài đặt", or any settings/admin section — none
of them are implemented, and a menu item that leads nowhere is worse than no
menu at all.
The top-right corner shows: the signed-in username and role (e.g.
"admin · admin"), a "Đổi mật khẩu" link, and a "Đăng xuất" button. Nothing else
— no notification bell, no help icon, no avatar menu.

FORBIDDEN ACTIONS — this product cannot do these things, so do not draw buttons
for them:
- NO "Tạo Job Mới" / create / add / new button anywhere. Jobs are created
  automatically when an editor saves an article in Drupal; there is no manual
  creation path.
- NO delete, archive, bulk-select, or bulk-action controls.
- NO approve / reject / duyệt buttons. The AI decides; a human never approves
  inside this tool.
- NO export / download button.
The ONLY action in the entire product is "Thử lại" on a failed job, and it
lives on the job detail screen, not here.

VIETNAMESE LABELS for job status — use these exact words, they are not
interchangeable:
  queued      -> "Trong hàng đợi"   (waiting to be processed;
                                     NOT "Chờ duyệt" — nobody approves anything)
  running     -> "Đang chạy"
  failed      -> "Thất bại"
  done        -> "Hoàn thành"
  superseded  -> "Bị thay thế"      (a newer job replaced this one)

VIETNAMESE LABELS for review decision:
  publish         -> "Xuất bản"
  needs_revision  -> "Cần sửa"
  rejected        -> "Từ chối"
  unknown         -> "Chưa rõ"

SAMPLE DATA — use the example values given in the DATA block VERBATIM. Do not
substitute prettier-looking placeholders. Real values look like:
  site_slug       "drupal-vn-primary"        (NOT "Site_A")
  source          "event", "reconcile", "admin_retry", "manual-test-b7"
                                             (NOT "API", "Batch", "Webhook")
  policy_version  "cam-nang-vn-v1"           (NOT "v2.4.1")
  created_at      render as "19/08/2026 14:32" — Vietnamese day/month/year
                  order, NOT the raw ISO string and NOT mm/dd/yyyy
A designer who invents friendlier-looking data hides how the real screen will
feel when it is full of long UUIDs and slugs.

CONSISTENCY — every state of this screen shows the SAME table with the SAME
columns and the SAME filter bar. Only the content area changes between loading,
empty, error, and populated. Do not redesign the table for the error state.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, done green, failed red, superseded muted), shown
  as a quiet pill, never as a filled row.
- Tables: generous row height, tight horizontal padding, hairline row dividers
  rather than boxes, strong weight contrast between header and body, IDs and
  numbers in a monospace face and right-aligned.
- Hierarchy comes from typographic weight and spacing, not borders, cards, or
  shadows. At most one elevated surface per screen.
- Frosted glass (white 75%, 20px blur) for navigation and modals only, never
  behind data.
- NO hero section, NO illustrations, NO gradient fills, NO pie charts, NO icons
  beside every label, NO oversized KPI numbers.
- Density: about 15 table rows visible without scrolling at 1440px width.
- All UI labels in Vietnamese.
```

---

## Đối chiếu với hợp đồng

Mọi tên trường trong các khối `DATA` ở trên đều lấy từ
`multiagent/console_ui/openapi.json`. Kiểm lại bất cứ lúc nào bằng:

```
cd multiagent
.venv\Scripts\python.exe scripts	est_console_stitch_briefs.py
```

Script đó đọc từng tên trường trong file này và đối chiếu với schema trong
`openapi.json`, báo lỗi nếu có tên không tồn tại hoặc có trường trong hợp đồng
mà brief bỏ sót. Nó nằm trong nhóm `pure` của `run_test_group.py`, nên brief
lệch khỏi API sẽ làm đỏ suite chứ không im lặng.

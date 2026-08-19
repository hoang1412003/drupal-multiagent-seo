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

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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
- Hàng đợi (queue_counts): a small count per job status. The four statuses are
  queued, running, succeeded, failed. Render as a compact inline row, NOT as
  four large KPI cards.
- Tổng số review (total_reviews): one integer.
- Quyết định (decision_counts): counts per decision — publish, needs_revision,
  rejected, unknown.
- Thời lượng: duration_p50_ms and duration_p95_ms (milliseconds, may be null).
  Label them as trung vị / phân vị 95, and show "—" when null.
- Ghi ngược (writeback_counts) plus writeback_success_rate (a ratio 0..1, may be
  null; render as a percentage).
- Chi phí ước tính (cost_estimate): input_tokens, output_tokens, estimated_usd
  (may be null), currency, pricing_version, effective_at (the date that price
  table took effect — show it as a small caption under the cost, so a reader can
  tell an estimate was priced with an old table), and unknown_models (a list of
  model names with no price on file — show a quiet warning when this list is not
  empty).
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

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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
- Trạng thái    (status — a badge with EXACTLY four possible values):
                queued / running / succeeded / failed
- Số lần thử    (attempts, integer, right-aligned)              e.g. 2
- Nguồn         (source, short string)                          e.g. "event", "admin_retry"
- Phiên bản policy (policy_version, string)                     e.g. "cam-nang-vn-v1"
There is NO title column and NO author column — the platform does not store them.
Rows are NOT clickable as a whole; the Mã job cell is the link to the detail
screen.

CONTROLS + STATES:
Filters: Trạng thái (dropdown, the four values above), Site (dropdown), Nguồn
(dropdown), ID nội dung (text, substring match), and a date range (Từ ngày /
Đến ngày — both required together or both empty).
Pagination: "Trang 1 / 3 · 137 kết quả" with previous/next. Page size is 25 by
default and capped at 100. There is no infinite scroll and no export button.
Design all four states:
1. Loading (skeleton rows)
2. Empty ("Chưa có job nào khớp bộ lọc")
3. Error (inline banner with retry)
4. Invalid filter — the API returns a validation message; show it above the
   table while KEEPING the filter values the user typed.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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
Trạng thái: status (badge: queued / running / succeeded / failed), attempts
  (integer), source (string), last_error (long free text, may be null — this is
  the field the reader came for, give it room and a monospace face).
Thời gian: created_at, updated_at (both ISO-8601 UTC).
Nội dung: external_content_id, external_revision_id (may be null), content_type,
  langcode.
Ngữ cảnh: site_slug, site_name, site_id (UUID), profile_id (UUID),
  policy_version.
Kết quả: run_public_id (UUID or null — link to the review detail screen when
  present), run_scored_at (timestamp or null), writeback_status (string or null),
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
3. Loaded, status running (no retry button at all)
4. Not found — "Không tìm thấy job"
5. Conflict — retry rejected because the job is no longer failed: inline banner
   "Không thể thử lại job này."

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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
                right-aligned, monospace)
- Hồ sơ         (profile_code, short string)
- Phiên bản policy (policy_version)
- Model         (model, e.g. "claude-sonnet-4-5-20250929" — this string is long,
                truncate with an ellipsis and show the full value on hover)
- Dữ liệu mẫu   (is_fixture, boolean — when true the row is seeded test data, not
                a real review. Mark it with a small neutral "mẫu" tag; do NOT
                hide the row and do NOT colour it like an error.)

CONTROLS + STATES:
Filters: Quyết định (dropdown), Site (dropdown), ID nội dung (text), and a date
range (both dates required together or both empty). Pagination identical to the
Jobs screen. No export button.
Design all four states:
1. Loading (skeleton rows)
2. Empty ("Chưa có review nào khớp bộ lọc")
3. Error (inline banner with retry)
4. Invalid filter — validation message above the table, filter values preserved.

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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
  null), final_score (number 0..100, may be null), veto_reason (text or null —
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
  null, currency, pricing_version, effective_at, unknown_models list).
Ghi ngược: writeback_status (string), writeback_error (text or null).
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

STYLE — art direction (professional internal tool, aim for the visual restraint
of Linear or Stripe Dashboard, NOT a marketing page):
- Brand: primary #00237a, page background #f9f9f9, text #1a1c1c, font Inter.
  Support light and dark mode.
- Colour discipline: navy is reserved for the single primary action per screen.
  Everything else is neutral grey. The ONLY other colour is semantic status
  (queued grey, running blue, succeeded green, failed red), shown as a quiet
  pill, never as a filled row.
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

# Thiết kế Console: tách frontend admin thành React SPA

**Ngày:** 2026-08-19

**Trạng thái:** Thiết kế đã được chủ dự án duyệt qua brainstorming; chờ duyệt
văn bản trước khi lập kế hoạch triển khai.

**Phạm vi đợt này:** giai đoạn 1 — sáu màn hình lõi (đăng nhập, dashboard,
jobs, job detail, reviews, review detail) cộng luồng bắt buộc đổi mật khẩu
(dạng form chặn, không phải một mục trong điều hướng). Các màn hình users,
connection, audit, config-kb, evaluation **không** thuộc đợt này.

**Liên quan:**

- `docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`
  (thiết kế admin Jinja2 hiện hành, vẫn còn hiệu lực);
- `docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md`;
- `docs/evidence/platform-mvp-acceptance.md` (ma trận 11/11 phải giữ nguyên);
- `docs/editor-ui-design.md` mục 10 (bài học UI, đặc biệt 10.6).

## 1. Vấn đề cần giải quyết

Admin hiện tại render bằng Jinja2 + htmx trong cùng process FastAPI. Chủ dự án
muốn tách frontend thành ứng dụng React riêng, thiết kế giao diện bằng Stitch,
và giao phần code giao diện cho một agent khác (Antigravity). Việc này đặt ra
một yêu cầu mà admin hiện tại không có: **một hợp đồng dữ liệu tường minh, máy
kiểm tra được**, vì bên viết giao diện không đọc code Python.

Ràng buộc kèm theo: không được làm hỏng admin đang chạy, không được sửa tầng
truy vấn và tầng xác thực đã có test, và phải giữ mốc `all-offline` = 0 failure
0 skip.

## 2. Phát hiện quyết định phạm vi công việc

`admin/queries.py` đã tách sạch khỏi tầng render. Nó trả về các dataclass có
kiểu (`PageView`, `JobListItem`, `JobDetail`, `ReviewListItem`, `ReviewDetail`,
`DashboardView`); Jinja2 chỉ là lớp hiển thị bên trên.

Hệ quả: tầng API mới **không viết lại logic truy vấn**. Nó là lớp serialize
mỏng. Đây là lý do giai đoạn 1 khả thi mà không đụng vào code đã kiểm chứng.

## 3. Kiến trúc

```
   /admin           ──►  admin/  (Jinja2 + htmx, GIỮ NGUYÊN)   ─┐
                                                                ├─► queries.py ──► Postgres
   /api/console/v1  ──►  admin_api/  (JSON, MỚI)               ─┘   (KHÔNG SỬA)

   /console         ──►  StaticFiles(console_ui/dist)  ◄── React build
```

Bốn nguyên tắc:

1. `admin/queries.py`, `auth/sessions.py`, `auth/users.py`, `auth/csrf.py`
   **không sửa logic**. Chúng đã có test.
2. Package mới `src/review_platform/admin_api/` chỉ làm ba việc: nhận request →
   gọi `queries` → trả JSON qua Pydantic model.
3. Hai UI dùng chung cookie phiên `vf_admin_session`. Đăng nhập một lần dùng
   được cả hai; thu hồi phiên có hiệu lực với cả hai. Điều này **đòi hỏi mở
   rộng `path` của cookie** — xem 5.1.
4. Admin cũ giữ nguyên đường dẫn `/admin` trong suốt giai đoạn 1. Muốn bỏ
   Console chỉ cần gỡ hai lệnh mount.

### 3.1 Vì sao dùng session cookie chứ không phải JWT

Client là trình duyệt, và là trình duyệt của người có quyền cao nhất hệ thống.

- Cookie `HttpOnly` thì JavaScript không đọc được, nên XSS không đánh cắp được
  phiên. Token trong `localStorage` thì mọi script trên trang đều đọc được.
- Thu hồi phiên tức thì đã có sẵn: `admin/dependencies.py` gọi
  `sessions.revoke(...)` khi user bị vô hiệu hóa. JWT không làm được điều này
  nếu không dựng thêm blacklist — mà blacklist chính là bảng phiên.
- Không phải viết logic refresh token.

Auth kiểu token đã tồn tại trong dự án và nằm đúng chỗ của nó:
`src/review_platform/api/auth.py` dùng API key cho connector Drupal. Nguyên
tắc phân định: **client là trình duyệt thì dùng cookie, client là máy thì dùng
token/API key.**

### 3.2 Vì sao same-origin

FastAPI serve luôn thư mục build React tại `/console`; khi dev, Vite proxy
`/api` sang FastAPI. Cả hai môi trường đều same-origin, nên:

- không cần cấu hình CORS;
- không phải đổi cookie sang `SameSite=None`;
- production vẫn chỉ một process, không thêm runtime Node.

## 4. Hợp đồng API

Tiền tố: `/api/console/v1`.

| Method | Đường dẫn | Nguồn dữ liệu | Quyền |
|---|---|---|---|
| POST | `/auth/login` | `auth/` hiện có | công khai |
| GET | `/auth/me` | phiên hiện tại | đã đăng nhập |
| POST | `/auth/logout` | `sessions.revoke` | đã đăng nhập |
| POST | `/auth/change-password` | `auth/passwords` | đã đăng nhập |
| GET | `/dashboard` | `queries.dashboard` | viewer |
| GET | `/jobs` | `queries.list_jobs` | viewer |
| GET | `/jobs/{public_id}` | `queries.get_job` | viewer |
| POST | `/jobs/{public_id}/retry` | `reviews.retry_failed` | operator |
| GET | `/reviews` | `queries.list_reviews` | viewer |
| GET | `/reviews/{public_id}` | `queries.get_review` | viewer |

**Retry giữ nguyên cổng xác nhận chi phí.** `admin/job_routes.py:216` chặn
retry khi chưa xác nhận, vì retry chạy lại pipeline tức là **gọi API trả phí**.
Console API giữ cổng này dưới dạng trường `confirm_cost: bool` trong thân JSON;
thiếu xác nhận trả `400` mã `cost_not_confirmed`. Retry cũng tạo ra **job mới**
(`RetryResult.new_job_public_id`) chứ không cập nhật job cũ, nên response trả
chi tiết của job mới, và giao diện phải điều hướng sang job mới đó.

### 4.1 `/auth/me` — endpoint không có màn hình nào nhưng bắt buộc

Cookie là `HttpOnly` nên JavaScript không đọc được. Khi React khởi động, nó
không biết mình đã đăng nhập hay chưa. Nó gọi `/auth/me`:

- `200` → trả `{ username, role, must_change_password, csrf_token }`, vào app;
- `401` → chuyển sang màn hình đăng nhập.

Đây cũng là nguồn duy nhất cấp `csrf_token` cho SPA.

### 4.2 Ba quy ước áp dụng cho mọi endpoint

**Phân trang** — khớp trực tiếp `PageView`:

```json
{ "items": [], "page": 1, "page_size": 50, "total": 137, "total_pages": 3 }
```

**Lỗi** — một hình dạng duy nhất, để frontend chỉ viết một chỗ xử lý:

```json
{ "error": { "code": "invalid_filter", "message": "...", "field": "status" } }
```

**Mã trạng thái:**

| Mã | Nghĩa | Frontend làm gì |
|---|---|---|
| 401 | chưa đăng nhập / phiên đã bị thu hồi | chuyển về `/console/login` |
| 403 | sai role | hiện "không đủ quyền", không chuyển trang |
| 400 | thiếu xác nhận chi phí khi retry | mở lại hộp thoại xác nhận |
| 404 | không tìm thấy | trang trống có thông báo |
| 409 | xung đột trạng thái (retry job không `failed`) | banner lỗi tại chỗ |
| 422 | tham số lọc sai | banner lỗi tại chỗ, giữ bộ lọc |

**CSRF** — mọi `POST` gửi header `X-CSRF-Token`.

### 4.3 Trường dữ liệu

Các model Pydantic ánh xạ 1-1 với dataclass trong `queries.py`. Quy tắc
chuyển kiểu, áp dụng nhất quán:

| Kiểu Python | JSON | Ghi chú |
|---|---|---|
| `UUID` | string | dạng chuẩn có gạch nối |
| `datetime` | string ISO-8601, UTC, có hậu tố `Z` | đã có `_as_utc` trong `queries.py` |
| `date` | string `YYYY-MM-DD` | |
| `Decimal` | number | `final_score`, percentile, tỷ lệ |
| `tuple` | array | |
| `None` | `null` | **không** đổi thành chuỗi rỗng |

`ReviewDetail` là phần serialize phức tạp nhất: nó lồng
`agents: tuple[AgentResultView, ...]`, mỗi agent lại chứa `criteria`, `issues`,
`evidence` là tuple dict tự do. Ba trường này đã đi qua
`admin/sanitization.py` và **phải tiếp tục đi qua đó** trước khi trả JSON —
bỏ bước này là mở lại đường cho dữ liệu chưa làm sạch từ output của model.

## 5. Thay đổi trên code đang chạy

Bản đầu của mục này viết "chỉ hai chỗ, không đổi hành vi cũ". **Sai.** Khi lập
kế hoạch triển khai, đọc lại code phát hiện hai vấn đề chặn (5.1 và 5.2) buộc
phải sửa hành vi hiện có. Danh sách đúng gồm ba chỗ:

1. **`admin/router.py`** — mở rộng `path` của cookie phiên (xem 5.1).
2. **`admin/dependencies.py`** — `require_csrf` đọc thêm header `X-CSRF-Token`
   (**giữ nguyên** nhánh form để admin htmx không hỏng), và bổ sung dependency
   phiên riêng cho API (xem 5.2).
3. **`src/api.py`** (nơi khởi tạo `app = FastAPI(...)`, dòng 44) — mount router
   `admin_api` và mount `StaticFiles` cho `/console`, kèm catch-all trả
   `index.html` để React Router không trả 404 khi người dùng bấm F5 trên đường
   dẫn con.

### 5.1 Cookie phiên đang giới hạn ở `path="/admin"`

`router.py:206` đặt cookie `vf_admin_session` với `path="/admin"`, và xóa nó ở
`router.py:232` và `router.py:295` cũng với `path="/admin"`. Trình duyệt vì thế
**không gửi cookie tới `/api/console/v1/...` và `/console`**. Giả định "hai UI
dùng chung phiên" ở mục 3 không thể chạy nếu giữ nguyên.

Cách xử lý: đưa `path` về `"/"` qua một hằng số dùng chung
`SESSION_COOKIE_PATH` trong `dependencies.py`, sửa cả ba vị trí.

Không được để hai đường dẫn cùng tồn tại. Nếu Console đặt cookie ở `"/"` còn
admin cũ đặt ở `"/admin"`, trình duyệt sẽ giữ **hai cookie trùng tên**, và
`request.cookies.get()` của Starlette chỉ trả về một cái không xác định — lỗi
này rất khó truy.

Xử lý cookie cũ còn sót của người đang đăng nhập lúc triển khai: route đăng
nhập (cả cũ lẫn mới) gọi thêm `delete_cookie(SESSION_COOKIE, path="/admin")`
trước khi đặt cookie mới ở `"/"`, và route đăng xuất xóa ở **cả hai** đường
dẫn. Đây là code chuyển tiếp, gỡ được sau một chu kỳ hết hạn phiên (8 giờ).

Đánh giá rủi ro của việc mở rộng: cookie sẽ được gửi tới mọi đường dẫn cùng
origin, gồm `/api/v1/*` của connector. Endpoint đó xác thực bằng API key và bỏ
qua cookie nên không đổi hành vi. Cookie vẫn `HttpOnly` + `SameSite=lax`, nên
mở rộng path không mở thêm bề mặt tấn công đáng kể — đây cũng là cấu hình mặc
định của phần lớn ứng dụng web.

### 5.2 `current_session` trả redirect 303, API cần 401

`dependencies.current_session` khi không có phiên sẽ raise `HTTPException(303,
Location: /admin/login)`, và khi `must_change_password` thì redirect sang
`/admin/change-password`. Đúng cho trang HTML, **sai cho API JSON**: fetch của
trình duyệt sẽ tự đi theo redirect và SPA nhận về HTML trang đăng nhập với mã
200 thay vì 401.

Vì vậy `admin_api` **không dùng lại** `current_session`. Nó có dependency riêng
`console_session` trong `admin_api/dependencies.py`, dùng chung
`sessions.resolve/revoke/touch` nhưng:

- không có phiên hợp lệ → `401` với thân `{"error": {"code": "unauthenticated"}}`;
- `must_change_password = true` → mọi endpoint trả `403` với
  `{"error": {"code": "must_change_password"}}`, **trừ** `/auth/me`,
  `/auth/change-password` và `/auth/logout`.

`/auth/me` phải đi qua được ở trạng thái này, vì đó là cách SPA biết cần hiện
form đổi mật khẩu.

## 6. Bàn giao cho Antigravity

Hợp đồng là **`openapi.json` do FastAPI tự sinh**, không phải tài liệu viết
tay. Từ đó sinh `api-types.ts` bằng `openapi-typescript`. Antigravity code với
kiểu có sẵn, gõ sai tên trường thì `tsc` báo lỗi ngay.

Kèm một tài liệu ngắn `docs/console-ui/integration.md` mô tả những thứ OpenAPI
diễn đạt kém: luồng đăng nhập, vòng đời CSRF, quy ước 401/403.

## 7. Bộ khung React

Chủ dự án dựng khung (Claude), Antigravity chỉ viết màn hình.

```
console_ui/
├── vite.config.ts        proxy /api → FastAPI (giữ same-origin khi dev)
├── tailwind.config.js    token VinFast: #00237a, Inter, glass
└── src/
    ├── api/
    │   ├── api-types.ts  SINH TỰ ĐỘNG từ openapi.json — không sửa tay
    │   └── client.ts     fetch có kiểu, tự gắn X-CSRF-Token, tự bắt 401
    ├── auth/             AuthProvider · RequireAuth · RequireRole
    ├── layout/           AppShell rỗng, chờ đắp design Stitch
    ├── pages/            6 trang + form đổi mật khẩu, mỗi trang có sẵn hook gọi API
    └── router.tsx
```

Stack: Vite + React + TypeScript + React Router + TanStack Query + Tailwind.

Hai quyết định đáng ghi lại:

- **Cài sẵn Tailwind với token VinFast.** Stitch xuất code theo phong cách
  Tailwind nên dán được gần như nguyên xi; không cài sẵn thì Antigravity sẽ
  dùng bảng màu mặc định và mất màu thương hiệu.
- **Antigravity không được viết lời gọi mạng nào.** Mọi request đi qua
  `src/api/client.ts`. Đây vừa là ranh giới review rõ ràng, vừa bảo đảm CSRF và
  xử lý 401 không bị làm sai ở sáu chỗ khác nhau.

## 8. Brief thiết kế Stitch

Ghi vào `docs/console-ui/stitch-briefs.md`, sáu prompt, mỗi màn hình một.

**Không đính kèm ảnh chụp admin cũ.** Chủ dự án muốn Stitch thiết kế lại tự do,
không bị neo vào giao diện hiện tại. Hệ quả: prompt là ràng buộc duy nhất, nên
mỗi prompt phải có đủ bốn phần:

| Phần | Nội dung | Vì sao bắt buộc |
|---|---|---|
| `CONTEXT` | màn hình gì, ai dùng, desktop-first, data-dense | không có thì Stitch vẽ theo mẫu landing page |
| `DATA` | liệt kê **đúng** các trường API trả về, kèm kiểu và ví dụ | chống Stitch bịa ra cột không tồn tại |
| `STATES` | loading, rỗng, lỗi, không đủ quyền | Stitch mặc định chỉ vẽ trạng thái đẹp có dữ liệu |
| `STYLE` | art direction cụ thể + danh sách `NO ...` | xem 8.1 |

`DATA` **sinh từ `openapi.json`**, nên brief bắt buộc phải làm sau khi API
xong. Đây là ràng buộc thứ tự, không phải sở thích.

### 8.1 Vì sao `STYLE` phải có danh sách phủ định

Mọi công cụ sinh UI đều mặc định trả về giao diện kiểu trang tiếp thị, vì đó là
thứ chiếm đa số trong dữ liệu huấn luyện. Đối trọng là một danh sách cấm tường
minh: không hero section, không minh họa, không nền gradient, không biểu đồ
tròn, không số KPI cỡ lớn, không icon cạnh mọi nhãn. Kèm một ràng buộc mật độ
đo được: trên màn hình 1440px phải thấy khoảng 15 dòng bảng mà không cuộn.

Kỷ luật màu: navy `#00237a` chỉ dùng cho **một** hành động chính mỗi màn hình;
màu còn lại là xám trung tính; màu ngữ nghĩa chỉ dùng cho trạng thái và chỉ
hiện dưới dạng pill, không tô nền cả dòng.

## 9. Kiểm thử

**Backend.** Test cho mỗi endpoint: 401 khi chưa đăng nhập, 403 khi sai role,
hình dạng phân trang, hình dạng lỗi, chuyển kiểu `Decimal`/`datetime`/`None`.
Theo đúng quy ước sẵn có của dự án — file `scripts/test_console_api_*.py`, cùng
kiểu với `scripts/test_admin_audit_page.py` — và phải đăng ký vào
`scripts/run_test_group.py` để `all-offline` giữ mốc 0 failure 0 skip.

**Frontend.** Dự án **không có JS test harness** và đợt này **không dựng thêm**.
Giao diện chỉ được xác nhận bằng ảnh chụp chủ dự án gửi vào `img-for-ai-see/`.
Không được tuyên bố "đã kiểm thử giao diện" khi thực tế chỉ là đọc code.

### 9.1 Checklist review code Antigravity

| # | Kiểm tra | Cách |
|---|---|---|
| 1 | không sai tên/kiểu trường | `npx tsc --noEmit` |
| 2 | không tự viết lời gọi mạng | `grep -rn "fetch(\|axios" src/ --exclude-dir=api` phải rỗng |
| 3 | **không lưu token ở `localStorage`/`sessionStorage`** | grep |
| 4 | mọi POST đi qua `client.ts` | đọc diff |
| 5 | mỗi màn hình đủ bốn trạng thái | đọc diff + ảnh chụp |

Điểm 3 là điểm soi kỹ nhất: đây là lỗi phổ biến nhất khi một agent tự code
frontend auth, và nó phá đúng lý do chọn mô hình cookie ở mục 3.1.

## 10. Thứ tự thực hiện

```
1. Claude:      API + test              → verify: pytest xanh, all-offline 0 fail 0 skip
2. Claude:      openapi.json + api-types.ts → verify: tsc --noEmit sạch
3. Claude:      6 brief Stitch          → verify: mọi trường trong brief tra được trong openapi.json
4. Chủ dự án:   thiết kế trên Stitch
5. Claude:      khung React             → verify: đăng nhập thật vào được, /auth/me trả 200
6. Antigravity: 6 màn hình
7. Claude:      review theo 9.1
```

## 11. Ngoài phạm vi

- Năm màn hình còn lại (users, connection, audit, config-kb, evaluation).
- Xóa hoặc thay thế admin Jinja2.
- JS test harness.
- Đổi mô hình xác thực; đổi `api/` (API key cho connector).
- Sửa `queries.py`, `sessions.py`, `csrf.py`.

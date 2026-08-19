# Console API — hướng dẫn tích hợp cho frontend

**Ngày:** 2026-08-19 · **Hợp đồng:** `multiagent/console_ui/openapi.json`

Tài liệu này chỉ mô tả những gì OpenAPI diễn đạt kém: vòng đời phiên, CSRF, và
ý nghĩa mã lỗi. Mọi thứ khác — tên endpoint, tên trường, kiểu dữ liệu — lấy từ
`openapi.json`, **không lấy từ đây**. Khi hai bên mâu thuẫn, `openapi.json`
đúng.

Tiền tố: `/api/console/v1`.

## 1. Xác thực dùng cookie, không dùng token

Phiên nằm trong cookie `vf_admin_session`, cờ `HttpOnly` — **JavaScript không
đọc được nó, và điều đó là cố ý**. Nhờ vậy một lỗ XSS trên trang không lấy được
phiên. Hệ quả với người viết frontend:

- **Không** lưu bất cứ thứ gì liên quan đến phiên vào `localStorage` hay
  `sessionStorage`. Không có token nào để lưu.
- **Không** tự gắn header `Authorization`. Trình duyệt tự gửi cookie.
- Mọi `fetch` phải có `credentials: "same-origin"`. Đây là mặc định, nhưng ghi
  rõ để không ai đổi nhầm thành `"omit"` — cookie là thứ **duy nhất** xác thực
  request.

Frontend và API cùng origin: FastAPI serve bản build tại `/console`, còn khi
dev thì Vite proxy `/api` sang FastAPI. Vì vậy **không có CORS** và không cần
cấu hình gì thêm.

## 2. Vòng đời phiên

```
Khởi động app
      │
      ├─ GET /auth/me ──► 200 ──► lưu user + csrf_token, vào app
      │                     │
      │                     └─ must_change_password = true
      │                            └─► ép sang form đổi mật khẩu
      │
      └────────────────► 401 ──► chuyển sang màn hình đăng nhập
```

**`/auth/me` là endpoint quan trọng nhất dù không có màn hình nào.** Cookie là
`HttpOnly` nên khi app khởi động, JavaScript không có cách nào biết mình đã
đăng nhập hay chưa. Nó phải hỏi server.

Ba điều cần nhớ:

1. Gọi `/auth/me` **một lần khi app mount**, trước khi render route nào.
2. Đăng nhập thành công (`POST /auth/login`) trả về **cùng hình dạng** với
   `/auth/me`, nên dùng lại một chỗ xử lý.
3. Khi bất kỳ request nào trả `401`, coi như phiên đã mất: xóa state người dùng
   và chuyển về màn hình đăng nhập. Không thử refresh — không có refresh token.

## 3. CSRF

Mọi `POST` phải gửi header `X-CSRF-Token`. Giá trị lấy từ trường `csrf_token`
trong phản hồi của `/auth/me` hoặc `/auth/login`.

```
POST /api/console/v1/jobs/{public_id}/retry
X-CSRF-Token: <csrf_token>
Content-Type: application/json

{"confirm_cost": true, "reason": "Thử lại sau lỗi connector"}
```

Thiếu header → `403` mã `csrf_invalid`. Đây là lỗi lập trình, không phải lỗi
người dùng: đừng hiện nó như thông báo cho người dùng, hãy sửa code gọi API.

`csrf_token` gắn với phiên và không đổi trong suốt phiên. Sau khi đổi mật khẩu
thì mọi phiên bị hủy, nên phải đăng nhập lại và lấy token mới.

## 4. Mã lỗi

Mọi lỗi có **đúng một hình dạng**:

```json
{ "error": { "code": "invalid_filter", "message": "...", "field": "status" } }
```

`field` có thể là `null`. Nhờ hình dạng cố định, frontend chỉ cần một chỗ xử lý
lỗi duy nhất.

| Mã | `code` | Ý nghĩa | Giao diện làm gì |
|---|---|---|---|
| 400 | `cost_not_confirmed` | Retry chưa xác nhận chi phí | Mở lại hộp thoại xác nhận |
| 400 | `password_rejected` | Mật khẩu cũ sai **hoặc** mật khẩu mới yếu | Một thông báo chung. Không tách hai trường hợp — server cố tình không phân biệt |
| 401 | `unauthenticated` | Chưa đăng nhập hoặc phiên đã bị thu hồi | Chuyển về `/console/login` |
| 403 | `forbidden` | Sai role | Hiện "không đủ quyền", **không** chuyển trang |
| 403 | `must_change_password` | Phải đổi mật khẩu trước | Ép sang form đổi mật khẩu |
| 403 | `csrf_invalid` | Thiếu/sai header CSRF | Lỗi lập trình, ghi log |
| 404 | `not_found` | Không tìm thấy | Trang trống có thông báo |
| 409 | `conflict` | Xung đột trạng thái (retry job không `failed`) | Banner lỗi tại chỗ |
| 413 | — | Body vượt 64 KB | Không nên xảy ra; xem lại payload |
| 422 | `invalid_filter` | Tham số lọc sai | Banner tại chỗ, **giữ nguyên** bộ lọc người dùng đã nhập |
| 429 | `throttled` | Đăng nhập quá nhiều lần | Vô hiệu nút, hiện thông báo chờ |

Hai điểm dễ làm sai:

- **403 không được đẩy về trang đăng nhập.** Người dùng đã đăng nhập hợp lệ, chỉ
  là không đủ quyền. Đẩy về login sẽ tạo vòng lặp.
- **422 phải giữ nguyên giá trị lọc.** Xóa sạch bộ lọc khi báo lỗi là cách nhanh
  nhất làm người dùng bực.

## 5. Phân trang

Mọi endpoint danh sách trả **cùng một hình dạng**:

```json
{ "items": [], "page": 1, "page_size": 25, "total": 137, "total_pages": 3 }
```

`page_size` mặc định 25, tối đa 100. Truyền `page=0` hoặc `page_size=1000` sẽ
nhận `422`.

## 6. Ba cạm bẫy về dữ liệu

**Điểm số là `number`, nhưng có thể `null`.** `final_score` là `null` khi review
chưa chấm được. Hiện `—`, đừng hiện `0` — chúng khác nhau về ý nghĩa.

**`worker_status` có ba giá trị, không phải hai.** `running` / `stale` /
`unavailable`. `stale` nghĩa là worker từng chạy rồi im lặng; `unavailable`
nghĩa là chưa bao giờ chạy. Gộp hai cái này sẽ che mất một sự cố thật.

**Retry tạo job MỚI.** `POST /jobs/{id}/retry` trả về chi tiết của **job mới**,
không phải job cũ. Điều hướng sang job mới đó; nếu ở lại trang cũ, người dùng
sẽ tưởng retry không có tác dụng.

## 7. Nội dung từ AI — quy tắc hiển thị

`agents[].criteria`, `.issues`, `.evidence` trong review detail bắt nguồn từ
output của model. Backend **đã** che bí mật (giá trị bị che hiện thành
`[đã ẩn]`) và giới hạn kích thước — tối đa 4 agent, 50 dòng mỗi nhóm.

Backend **không** escape HTML, và cố ý không làm vậy: escape là việc của tầng
hiển thị. React escape mặc định, nên chỉ cần một quy tắc:

> **Cấm `dangerouslySetInnerHTML`** với bất kỳ dữ liệu nào từ API.

Vi phạm quy tắc này biến mọi trường tự do từ AI thành một lỗ XSS.

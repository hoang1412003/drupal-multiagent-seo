# Console UI

Frontend React cho Platform Admin, phục vụ tại `/console`. Backend là FastAPI
cùng origin, nên **không có CORS** và phiên nằm trong cookie `HttpOnly`.

## Chạy

```bash
npm install
npm run types      # sinh src/api/api-types.ts từ openapi.json
npm run dev        # Vite tại :5173, proxy /api sang FastAPI :8900
npm run typecheck  # tsc --noEmit — chạy trước khi báo xong
npm run build      # ra dist/, FastAPI serve tại /console
```

Backend phải chạy song song:

```bash
cd ..   # multiagent/
.venv\Scripts\python.exe -m uvicorn api:app --port 8900 --app-dir src
```

## Năm quy tắc bắt buộc

Đây không phải sở thích về phong cách. Mỗi quy tắc chặn một lỗi cụ thể.

**1. Không sửa `src/api/api-types.ts`.**
File này sinh tự động từ `openapi.json`. Sửa tay sẽ bị ghi đè ở lần
`npm run types` kế tiếp, và tệ hơn là làm kiểu lệch khỏi API thật. Cần trường
mới thì backend phải đổi trước.

**2. Không gọi `fetch` hay `axios` trực tiếp. Dùng `client` trong `src/api/client.ts`.**
`client` tự gắn header `X-CSRF-Token`, tự đặt `credentials`, và biến lỗi thành
`ConsoleApiError` có `code`. Viết `fetch` riêng nghĩa là làm lại ba việc đó ở
mỗi chỗ gọi, và sai một chỗ là một lỗ bảo mật. Kiểm tra:

```bash
grep -rn "fetch(\|axios" src/ --exclude-dir=api
```
Kết quả phải rỗng.

**3. Không lưu bất cứ thứ gì liên quan đến phiên vào `localStorage` hay `sessionStorage`.**
Phiên nằm trong cookie `HttpOnly` — JavaScript **không đọc được nó**, và đó là
cố ý: một lỗ XSS trên trang sẽ không lấy được phiên. Lưu token vào
`localStorage` phá bỏ đúng lớp bảo vệ đó. Không có token nào cần lưu.

**4. Cấm `dangerouslySetInnerHTML` với dữ liệu từ API.**
`agents[].criteria`, `.issues`, `.evidence` trong review detail bắt nguồn từ
output của model. Backend đã che bí mật và giới hạn kích thước nhưng **không**
escape HTML — escape là việc của tầng hiển thị, và React làm sẵn khi bạn render
bằng `{}`. Dùng `dangerouslySetInnerHTML` biến mọi trường tự do từ AI thành một
lỗ XSS.

**5. Mỗi màn hình đọc dữ liệu phải có đủ bốn trạng thái.**
Đang tải · rỗng · lỗi · không đủ quyền. Dùng `<AsyncBoundary>` trong
`src/pages/AsyncBoundary.tsx` — nó đã xử lý cả bốn. Riêng lỗi `403` **không
được** điều hướng về trang đăng nhập: người dùng đã đăng nhập hợp lệ, chỉ là
không đủ quyền, và điều hướng sẽ tạo vòng lặp.

## Cấu trúc

```
src/
├── api/
│   ├── api-types.ts   SINH TỰ ĐỘNG — không sửa
│   └── client.ts      lớp gọi API duy nhất
├── auth/
│   ├── AuthProvider   hỏi /auth/me khi khởi động, giữ user + csrf_token
│   ├── RequireAuth    chặn route khi chưa đăng nhập
│   └── RequireRole    ẩn UI theo role (chỉ là tiện nghi — server vẫn kiểm tra)
├── layout/AppShell    khung trang, cố ý để trần
├── pages/             7 trang, mỗi trang có sẵn hook gọi API + ghi chú TODO
└── router.tsx         basename "/console"
```

## Việc của bạn

Bảy trang trong `src/pages/` hiện chỉ in JSON thô. Mỗi trang có một ghi chú
`TODO(Antigravity)` nêu rõ thiết kế Stitch tương ứng. Việc cần làm là dựng giao
diện theo thiết kế đó, **dùng dữ liệu đã có sẵn trong biến** — không sửa phần
gọi API, không sửa `auth/`.

Thiết kế và ràng buộc dữ liệu: `docs/console-ui/stitch-briefs.md`
Luồng auth, CSRF, bảng mã lỗi: `docs/console-ui/integration.md`

## Ba cạm bẫy dữ liệu

- `final_score` **có thể null** — hiện `—`, đừng hiện `0`. Chúng khác nghĩa.
- `worker_status` có **ba** giá trị: `running` / `stale` / `unavailable`.
  `stale` là worker từng chạy rồi im lặng; `unavailable` là chưa bao giờ chạy.
  Gộp hai cái sau sẽ che mất một sự cố thật.
- Retry tạo **job mới**. `POST /jobs/{id}/retry` trả chi tiết job mới, không
  phải job cũ. Phải điều hướng sang job mới, nếu không người dùng tưởng retry
  không có tác dụng.

## Không có JS test harness

Dự án này **không có** bộ test JavaScript, và đợt này không dựng thêm. Nghĩa là
giao diện chỉ được xác nhận bằng **ảnh chụp màn hình**. Đừng báo "đã kiểm thử
giao diện" khi thực tế chỉ là đọc code — chạy `npm run typecheck`, mở trình
duyệt, và chụp lại.

## Về Tailwind

Bản cài là **Tailwind 4**, không có `tailwind.config.js`. Token thương hiệu khai
báo bằng CSS trong `src/index.css` qua `@theme`:

```css
@theme {
  --color-vf: #00237a;      /* dùng: bg-vf, text-vf, border-vf */
  --color-vf-hover: #001f68;
  --color-surface: #f9f9f9;
  --color-ink: #1a1c1c;
}
```

Cần token mới thì thêm vào khối `@theme` đó, đừng tạo `tailwind.config.js`.

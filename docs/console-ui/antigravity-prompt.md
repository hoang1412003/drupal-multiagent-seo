# Câu lệnh giao cho Antigravity

Mỗi lần chỉ giao **một màn hình**. Xong màn nào, xem và review màn đó rồi mới
sang màn tiếp theo — sai ở một màn thì sửa một lần, sai ở bảy màn thì sửa bảy
lần.

**Luôn đính kèm ảnh** `docs/console-ui/reference/jobs-list.png` cùng với câu
lệnh. Ảnh là chuẩn về hình thức.

---

## Màn hình 1 — Jobs (làm đầu tiên)

Copy toàn bộ khối dưới đây:

```
Dự án: multiagent/console_ui/ — React 19 + TypeScript + Tailwind 4, đã chạy được.
Backend đã xong hoàn toàn: 11 endpoint JSON, xác thực, phân trang, lọc.
Việc của bạn CHỈ là phần trình bày.

ĐỌC BỐN FILE NÀY TRƯỚC KHI VIẾT DÒNG CODE NÀO:
1. multiagent/console_ui/README.md    — 5 quy tắc bắt buộc
2. docs/console-ui/design-system.md   — bảng màu, công thức class Tailwind
3. docs/console-ui/stitch-briefs.md   — mục "3. Jobs": cột nào, cấm cái gì
4. docs/console-ui/integration.md     — mã lỗi, phân trang, endpoint /filters

Ảnh đính kèm là CHUẨN VỀ HÌNH THỨC. Làm cho giống nó.

VIỆC CẦN LÀM — CHỈ MÀN HÌNH JOBS:
Sửa hai file:
- multiagent/console_ui/src/layout/AppShell.tsx  (sidebar + thanh trên)
- multiagent/console_ui/src/pages/JobsPage.tsx   (thẻ lọc + bảng + phân trang)

Bảng phải có ĐÚNG 8 cột, không thêm không bớt:
Mã job · Thời gian tạo · Site · ID nội dung · Trạng thái · Số lần thử · Nguồn ·
Phiên bản policy

Đủ 4 trạng thái, dùng chung một khung (sidebar, thanh trên, thẻ lọc và ĐẦU
BẢNG luôn hiện, chỉ thân bảng đổi):
- đang tải  → skeleton xám, giữ đúng số cột
- rỗng      → "Chưa có job nào khớp bộ lọc" + nút "Xóa bộ lọc"
- lỗi       → banner đỏ phía trên bảng + nút "Thử lại"
- lọc sai   → thông báo trong thẻ lọc, GIỮ NGUYÊN giá trị người dùng đã nhập

RÀNG BUỘC — vi phạm là phải làm lại:
- KHÔNG sửa src/api/api-types.ts (file sinh tự động)
- KHÔNG gọi fetch/axios trực tiếp — mọi request qua client trong src/api/client.ts
- KHÔNG lưu bất cứ gì vào localStorage/sessionStorage
- KHÔNG dùng dangerouslySetInnerHTML
- KHÔNG viết cứng danh sách trạng thái — lấy từ useFilters() trong
  src/api/useFilters.ts
- KHÔNG thêm mục menu ngoài ba mục: Tổng quan, Jobs, Reviews
- KHÔNG thêm nút tạo/xóa/duyệt/xuất file

XONG THÌ:
Chạy `npx tsc --noEmit` trong multiagent/console_ui và báo kết quả.
Không tự ý làm màn hình khác.
```

---

## Sáu màn còn lại

Chờ màn Jobs được duyệt rồi mới làm. Dùng lại khối trên, đổi ba chỗ:

| Đổi chỗ nào | Jobs | Reviews | Dashboard | Job detail | Review detail | Login |
|---|---|---|---|---|---|---|
| Tên file trang | `JobsPage.tsx` | `ReviewsPage.tsx` | `DashboardPage.tsx` | `JobDetailPage.tsx` | `ReviewDetailPage.tsx` | `LoginPage.tsx` |
| Mục trong stitch-briefs | "3. Jobs" | "5. Reviews" | "2. Dashboard" | "4. Job detail" | "6. Review detail" | "1. Login" |
| Số cột / trường | 8 cột | 11 cột | 15 trường | 22 trường | 28 trường | 3 ô nhập |

`AppShell.tsx` chỉ sửa một lần ở màn Jobs, các màn sau dùng lại.

Riêng **Job detail** có thêm việc: nút "Thử lại" chỉ hiện khi `status = failed`
và chỉ với role operator/admin, kèm hộp thoại xác nhận chi phí. Bọc bằng
`<RequireRole role="operator">` có sẵn trong `src/auth/RequireRole.tsx`.

Riêng **Review detail** là màn chỉ đọc — không có nút duyệt/từ chối nào cả.

---

## Kiểm tra sau mỗi màn

Chạy trong `multiagent/console_ui`:

```bash
npx tsc --noEmit                                    # sai tên trường sẽ báo đỏ
grep -rn "fetch(\|axios" src/ --exclude-dir=api     # phải không ra kết quả nào
grep -rn "localStorage\|sessionStorage" src/        # phải không ra kết quả nào
grep -rn "dangerouslySetInnerHTML" src/             # phải không ra kết quả nào
```

Ba lệnh `grep` quan trọng hơn cả lệnh đầu. Nếu Antigravity tự viết `fetch`
hoặc lưu gì vào `localStorage`, nghĩa là nó đã hiểu sai mô hình xác thực và
phá đúng lớp bảo vệ mà dự án chọn cookie `HttpOnly` để có.

Rồi mở `http://localhost:5173/console/` và chụp màn hình.

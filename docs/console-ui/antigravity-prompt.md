# Câu lệnh giao cho Antigravity

Mỗi lần chỉ giao **một màn hình**. Xong màn nào, xem và review màn đó rồi mới
sang màn tiếp theo — sai ở một màn thì sửa một lần, sai ở bảy màn thì sửa bảy
lần.

## Dùng với CLI: chỉ cần một dòng

Mở terminal, vào thư mục gốc `D:\drupal-multiagent-seo`, khởi động Antigravity
CLI, rồi gõ đúng một dòng:

```
Đọc docs/console-ui/antigravity-prompt.md và làm theo đúng mục "NHIỆM VỤ 1 — Jobs". Chỉ làm màn hình đó, không làm màn khác.
```

Antigravity sẽ tự đọc file này và biết phải làm gì. Không cần copy khối lệnh
dài, không cần đính kèm ảnh.

---

## NHIỆM VỤ 1 — Jobs

**Bối cảnh.** Dự án `multiagent/console_ui/` là React 19 + TypeScript +
Tailwind 4, đã chạy được. Backend đã xong hoàn toàn: 11 endpoint JSON, xác
thực, phân trang, lọc. Việc cần làm **chỉ là phần trình bày**.

**Đọc bốn file này trước khi viết dòng code nào:**

1. `multiagent/console_ui/README.md` — 5 quy tắc bắt buộc
2. `docs/console-ui/design-system.md` — bảng màu, công thức class Tailwind
3. `docs/console-ui/stitch-briefs.md` mục "3. Jobs" — cột nào, cấm cái gì
4. `docs/console-ui/integration.md` — mã lỗi, phân trang, endpoint `/filters`

**Xem ảnh** `docs/console-ui/reference/jobs-list.png`. Đó là **chuẩn về hình
thức** — làm cho giống nó. Nếu công cụ của bạn đọc được ảnh thì mở ra xem;
nếu không, bám theo `design-system.md`, tài liệu đó mô tả lại chính ảnh này.

**Sửa đúng hai file:**

- `multiagent/console_ui/src/layout/AppShell.tsx` — sidebar + thanh trên
- `multiagent/console_ui/src/pages/JobsPage.tsx` — thẻ lọc + bảng + phân trang

**Bảng phải có đúng 8 cột, không thêm không bớt:**

```
Mã job · Thời gian tạo · Site · ID nội dung · Trạng thái · Số lần thử ·
Nguồn · Phiên bản policy
```

**Đủ 4 trạng thái, dùng chung một khung.** Sidebar, thanh trên, thẻ lọc và
**đầu bảng** luôn hiện; chỉ thân bảng đổi:

| Trạng thái | Thân bảng |
|---|---|
| đang tải | skeleton xám, giữ đúng số cột |
| rỗng | "Chưa có job nào khớp bộ lọc" + nút "Xóa bộ lọc" |
| lỗi | banner đỏ phía trên bảng + nút "Thử lại" |
| lọc sai | thông báo trong thẻ lọc, **giữ nguyên** giá trị người dùng đã nhập |

**Ràng buộc — vi phạm là phải làm lại:**

- KHÔNG sửa `src/api/api-types.ts` (file sinh tự động)
- KHÔNG gọi `fetch`/`axios` trực tiếp — mọi request qua `client` trong
  `src/api/client.ts`
- KHÔNG lưu bất cứ gì vào `localStorage`/`sessionStorage`
- KHÔNG dùng `dangerouslySetInnerHTML`
- KHÔNG viết cứng danh sách trạng thái — lấy từ `useFilters()` trong
  `src/api/useFilters.ts`
- KHÔNG thêm mục menu ngoài ba mục: Tổng quan, Jobs, Reviews
- KHÔNG thêm nút tạo/xóa/duyệt/xuất file
- KHÔNG cài thêm thư viện nào. Mọi thứ cần thiết đã có sẵn

**Xong thì:** chạy `npx tsc --noEmit` trong `multiagent/console_ui` và báo kết
quả. Không tự ý làm màn hình khác.

---

## Sáu nhiệm vụ còn lại

Chờ màn Jobs được duyệt rồi mới làm. Câu lệnh CLI y hệt, chỉ đổi tên nhiệm vụ.
Nội dung nhiệm vụ giống NHIỆM VỤ 1, đổi ba chỗ theo bảng:

| Nhiệm vụ | File trang | Mục trong stitch-briefs | Quy mô |
|---|---|---|---|
| 2 — Reviews | `ReviewsPage.tsx` | "5. Reviews" | 11 cột |
| 3 — Dashboard | `DashboardPage.tsx` | "2. Dashboard" | 15 trường |
| 4 — Job detail | `JobDetailPage.tsx` | "4. Job detail" | 22 trường |
| 5 — Review detail | `ReviewDetailPage.tsx` | "6. Review detail" | 28 trường |
| 6 — Login | `LoginPage.tsx` | "1. Login" | 3 ô nhập |
| 7 — Đổi mật khẩu | `ChangePasswordPage.tsx` | "1. Login" (biến thể) | 2 ô nhập |

`AppShell.tsx` chỉ sửa một lần ở nhiệm vụ 1, các nhiệm vụ sau dùng lại.

**Nhiệm vụ 4 (Job detail)** có thêm việc: nút "Thử lại" chỉ hiện khi
`status = failed` và chỉ với role operator/admin, kèm hộp thoại xác nhận chi
phí. Bọc bằng `<RequireRole role="operator">` có sẵn trong
`src/auth/RequireRole.tsx`. Phần logic gọi API đã viết sẵn trong
`JobDetailPage.tsx` — chỉ cần khoác giao diện lên, đừng viết lại.

**Nhiệm vụ 5 (Review detail)** là màn **chỉ đọc** — không có nút duyệt/từ chối
nào cả. Riêng `agents[].criteria/issues/evidence` là dữ liệu tự do từ output
của model: render bằng `{}` của React, tuyệt đối không `dangerouslySetInnerHTML`.

---

## Kiểm tra sau mỗi màn

Chạy trong `multiagent/console_ui`:

```bash
npx tsc --noEmit
grep -rn "fetch(\|axios" src/ --exclude-dir=api
grep -rn "localStorage\|sessionStorage" src/
grep -rn "dangerouslySetInnerHTML" src/
```

Lệnh đầu phải không báo lỗi. **Ba lệnh `grep` phải không ra kết quả nào** — và
chúng quan trọng hơn lệnh đầu. Nếu Antigravity tự viết `fetch` hoặc lưu gì vào
`localStorage`, nghĩa là nó đã hiểu sai mô hình xác thực và phá đúng lớp bảo vệ
mà dự án chọn cookie `HttpOnly` để có.

Rồi mở `http://localhost:5173/console/` và chụp màn hình.

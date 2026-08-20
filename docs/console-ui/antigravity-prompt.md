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
- KHÔNG tự viết hàm định dạng ngày/số/UUID — dùng `src/lib/format.ts`
  (`formatDateTime`, `formatDate`, `formatNumber`, `shortId`). Mọi cột thời
  gian phải ghi nhãn `TIMEZONE_LABEL` trong tiêu đề cột
- KHÔNG tự đặt tên tham số truy vấn — lấy đúng tên trong `openapi.json`
  (`external_id` chứ không phải `external_content_id`; `from`/`to` chứ không
  phải `date_from`/`date_to`). Server trả 422 nếu gõ sai tên

**Xong thì:** chạy `npx tsc --noEmit` trong `multiagent/console_ui` và báo kết
quả. Không tự ý làm màn hình khác.

---

## NHIỆM VỤ 2 — Reviews

**Bối cảnh.** Giống nhiệm vụ 1. Màn này là danh sách kết quả review đã chấm
xong — biên tập viên quét để tìm bài AI đánh dấu cần sửa.

**Đọc bốn file này trước khi viết dòng code nào:**

1. `multiagent/console_ui/README.md` — 5 quy tắc bắt buộc
2. `docs/console-ui/design-system.md` — bảng màu, công thức class, **mục 4b về
   hàm định dạng dùng chung**
3. `docs/console-ui/stitch-briefs.md` mục "5. Reviews" — cột nào, cấm cái gì
4. `docs/console-ui/integration.md` — mã lỗi, phân trang, endpoint `/filters`

**Xem `multiagent/console_ui/src/pages/JobsPage.tsx`** — màn Jobs đã làm xong và
đã được duyệt. Màn này cùng khuôn: thẻ lọc, bảng, phân trang. **Bám đúng cấu
trúc và class của nó**, đừng nghĩ ra bố cục mới.

**Sửa đúng một file:** `multiagent/console_ui/src/pages/ReviewsPage.tsx`.
`AppShell.tsx` đã xong ở nhiệm vụ 1, không đụng vào.

**Bảng phải có đúng 10 cột, không thêm không bớt:**

```
Mã review · Thời gian chấm (giờ VN) · Site · ID nội dung · Quyết định ·
Điểm · Hồ sơ · Phiên bản policy · Model · Dữ liệu mẫu
```

Ánh xạ sang trường API: `public_id`, `scored_at`, `site_slug`,
`external_content_id`, `decision`, `final_score`, `profile_code`,
`policy_version`, `model`, `is_fixture`. Trường `site_id` **không hiện** — bảng
hiện `site_slug` cho người đọc.

**Bốn điểm khác màn Jobs, chú ý kỹ:**

1. `decision` **có thể null**, và có 4 giá trị: `publish` (Xuất bản),
   `needs_revision` (Cần sửa), `rejected` (Từ chối), `unknown` (Chưa rõ). Lấy
   danh sách từ `useFilters().review_decisions`, đừng viết cứng. Pill dùng cùng
   khuôn với Jobs: publish=emerald, needs_revision=amber, rejected=red,
   unknown=gray.
2. `final_score` **có thể null** và API trả nguyên độ chính xác
   (`40.9090909090909`). Dùng `formatNumber(job.final_score)` — nó tự làm tròn
   1 chữ số và tự trả `—` khi null. **Đừng hiện `0` thay cho null.**
3. `model` là chuỗi dài (`claude-haiku-4-5-20251001`). Cắt bớt bằng
   `truncate max-w-[14rem]` và cho `title` để hover xem đầy đủ.
4. `is_fixture = true` nghĩa là dữ liệu mẫu, không phải review thật. Đánh dấu
   bằng một nhãn xám mờ "mẫu". **Đừng ẩn dòng, đừng tô như lỗi.**

**Bộ lọc — chỉ ba cái, ít hơn Jobs:** Quyết định (dropdown), Site (dropdown),
ID nội dung (text), và khoảng ngày (Từ ngày / Đến ngày). **Không có** bộ lọc
Nguồn ở màn này.

**Tên tham số truy vấn lấy đúng từ `openapi.json`:** `decision`, `site`,
`external_id`, `from`, `to`, `page`, `page_size`. Gõ sai tên server trả 422.

**Đủ 4 trạng thái**, dùng chung một khung như màn Jobs — sidebar, thẻ lọc và
**đầu bảng** luôn hiện, chỉ thân bảng đổi:

| Trạng thái | Thân bảng |
|---|---|
| đang tải | skeleton xám, giữ đúng 10 cột |
| rỗng | "Chưa có review nào khớp bộ lọc" + nút "Xóa bộ lọc" |
| lỗi | banner đỏ phía trên bảng + nút "Thử lại" |
| lọc sai | thông báo trong thẻ lọc, **giữ nguyên** giá trị người dùng đã nhập |

**Một điều phải ghi trong giao diện:** danh sách này **không** lọc theo ngày mặc
định và **không** loại dữ liệu mẫu, nên tổng số ở đây sẽ **không khớp** với
"Tổng số review" trên Dashboard (Dashboard lọc 7 ngày và loại dữ liệu mẫu). Ghi
một dòng chú thích nhỏ dưới tiêu đề để chênh lệch đọc ra là có chủ ý.

**Ràng buộc — giống hệt nhiệm vụ 1:**

- KHÔNG sửa `src/api/api-types.ts` (file sinh tự động)
- KHÔNG gọi `fetch`/`axios` trực tiếp — dùng `client` trong `src/api/client.ts`
- KHÔNG lưu bất cứ gì vào `localStorage`/`sessionStorage`
- KHÔNG dùng `dangerouslySetInnerHTML`
- KHÔNG viết cứng danh sách quyết định — lấy từ `useFilters()`
- KHÔNG tự viết hàm định dạng — dùng `src/lib/format.ts`
- KHÔNG thêm mục menu, không thêm nút tạo/xóa/duyệt/xuất file
- KHÔNG cài thêm thư viện nào
- KHÔNG sửa `AppShell.tsx` hay bất kỳ file nào ngoài `ReviewsPage.tsx`

**Xong thì:** chạy `npx tsc --noEmit` trong `multiagent/console_ui` và báo kết
quả. Không tự ý làm màn hình khác.

---

## Năm nhiệm vụ còn lại

Làm lần lượt, mỗi màn xong thì review rồi mới sang màn sau. Khi tới lượt màn
nào, nhiệm vụ đó sẽ được viết đủ ra như hai nhiệm vụ trên — **đừng suy ra từ
bảng**, vì chỉ dẫn gián tiếp là thứ đã làm lệch bản thiết kế Stitch hôm
2026-08-20.

Bảng dưới chỉ để biết trước quy mô:

| Nhiệm vụ | File trang | Mục trong stitch-briefs | Quy mô |
|---|---|---|---|
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

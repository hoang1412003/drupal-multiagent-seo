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

## NHIỆM VỤ 3 — Dashboard (Tổng quan)

**Đây là màn khó nhất trong ba màn đầu.** Đọc hết trước khi viết.

**Bối cảnh.** Màn đầu tiên sau khi đăng nhập. Người đọc là kỹ thuật viên vận
hành, đang muốn biết **hệ thống có đang khoẻ không, ngay lúc này**. Không phải
trang báo cáo cho lãnh đạo.

**Đọc bốn file này trước khi viết dòng code nào:**

1. `multiagent/console_ui/README.md` — 5 quy tắc bắt buộc
2. `docs/console-ui/design-system.md` — bảng màu, class, **mục 4b hàm định dạng**
3. `docs/console-ui/stitch-briefs.md` mục "2. Dashboard"
4. `docs/console-ui/integration.md` — mã lỗi, `/filters`

**Xem `JobsPage.tsx` và `ReviewsPage.tsx`** — hai màn đã duyệt. Dùng lại đúng
thẻ (card), nhãn ô lọc, nút, và bảng màu của chúng.

**Sửa đúng một file:** `multiagent/console_ui/src/pages/DashboardPage.tsx`.

---

### Điều quan trọng nhất: màn này trộn HAI phạm vi thời gian

Đây là chỗ dễ làm người dùng tưởng hệ thống hỏng.

| Khối | Phạm vi | Có bỏ dữ liệu mẫu? |
|---|---|---|
| `queue_counts` (hàng đợi) | **TOÀN THỜI GIAN** — không lọc ngày | không |
| Mọi khối còn lại | **chỉ khoảng ngày đã chọn** | **có, bỏ dữ liệu mẫu** |

Vì vậy giao diện **bắt buộc**:

- Tách `queue_counts` thành một khối riêng, đặt **trên cùng**, tiêu đề ghi rõ
  **"Hàng đợi hiện tại — toàn thời gian"**.
- Các khối còn lại gom vào một vùng có tiêu đề ghi rõ khoảng ngày, kèm chú
  thích nhỏ: **"Chỉ tính khoảng ngày đã chọn, không tính dữ liệu mẫu."**

Không tách thì người đọc thấy "Hoàn thành: 13" và "Tổng số review: 5" rồi kết
luận số liệu sai.

---

### 15 trường, không thêm không bớt

**Khối 1 — Hàng đợi hiện tại (toàn thời gian)**

`queue_counts` là một object đếm theo trạng thái, 5 khoá: `queued`, `running`,
`failed`, `done`, `superseded`. Lấy danh sách khoá từ
`useFilters().job_statuses`, **đừng viết cứng**. Nhãn tiếng Việt và màu dùng
đúng bảng của `JobsPage.tsx`.

Hiển thị thành **một hàng ngang gọn**, mỗi trạng thái là một pill kèm số.
**KHÔNG** dựng 5 thẻ KPI cỡ lớn.

**Khối 2 — Khoảng thời gian**

`date_from`, `date_to` (chuỗi `YYYY-MM-DD`). Hiện bằng `formatDate()`. Đây cũng
là giá trị hiện tại của bộ lọc ngày.

**Khối 3 — Kết quả review trong khoảng**

- `total_reviews` (số nguyên) — tổng
- `decision_counts` — object đếm theo 4 quyết định. Lấy khoá từ
  `useFilters().review_decisions`. Nhãn và màu dùng đúng bảng của
  `ReviewsPage.tsx`.

**Khối 4 — Thời lượng xử lý**

- `duration_p50_ms`, `duration_p95_ms` — **số hoặc null**. Nhãn "Trung vị" và
  "Phân vị 95". Đổi sang giây khi lớn hơn 1000ms cho dễ đọc (`7688` →
  `7,7 giây`). Dùng `formatNumber`, null hiện `—`.

**Khối 5 — Ghi ngược (writeback)**

- `writeback_counts` — object đếm 5 khoá: `succeeded`, `failed`, `superseded`,
  `pending`, `unknown`. Lấy khoá từ `useFilters().writeback_statuses`.
- `writeback_success_rate` — **tỷ lệ 0..1, có thể null**. Hiện dạng phần trăm
  (`1` → `100%`). Null hiện `—`.

**Khối 6 — Chi phí ước tính** (`cost_estimate`, 8 trường con)

- `input_tokens`, `output_tokens` (số nguyên, có dấu phân cách nghìn)
- `estimated_usd` (**có thể null**) — hiện kèm `currency`
- `pricing_version` (số nguyên) và `effective_at` (ngày) — gộp thành một chú
  thích nhỏ: "Bảng giá v1, hiệu lực 15/10/2025"
- `source` — **là một URL**. Hiện thành link ngoài nhỏ ("nguồn giá"), không in
  ra URL thô
- `unknown_models` — mảng tên model chưa có giá. Rỗng thì không hiện gì; có
  phần tử thì hiện cảnh báo mờ: "N model chưa có bảng giá, chi phí có thể
  thiếu"

**Khối 7 — Tình trạng worker**

- `worker_status` — **đúng ba giá trị, và chúng KHÁC NHAU**:

  | Giá trị | Nhãn tiếng Việt | Ý nghĩa | Màu |
  |---|---|---|---|
  | `running` | Đang chạy | bình thường | xanh lá |
  | `stale` | Mất tín hiệu | **từng chạy rồi im lặng** — đây là sự cố | đỏ |
  | `unavailable` | Chưa từng chạy | chưa bao giờ báo cáo | xám |

  **Gộp `stale` và `unavailable` làm một là che mất một sự cố thật.**

- `worker_running`, `worker_stale` (số nguyên) — số worker mỗi loại
- `worker_last_seen_at` (**có thể null**) — dùng `formatDateTime`, ghi nhãn
  `TIMEZONE_LABEL`
- `connector_status` — chuỗi tự do (giá trị thật: `"ok"`). Hiện thành pill:
  `ok` màu xanh lá, giá trị khác màu đỏ

---

### Bộ lọc

Chỉ hai ô: **Từ ngày** và **Đến ngày**, cùng nút "Lọc" và "Đặt lại".

Tên tham số truy vấn là **`from` và `to`** (xem `openapi.json`). Hai ngày phải
đi **cùng nhau** — truyền một cái server trả 422. Nếu người dùng chỉ điền một ô,
chặn ngay ở giao diện và báo tại chỗ, đừng gửi lên.

Mặc định khi không truyền gì: server tự lấy **7 ngày gần nhất**.

---

### Đủ 4 trạng thái

| Trạng thái | Hiện gì |
|---|---|
| đang tải | skeleton xám cho từng khối, giữ nguyên bố cục |
| rỗng | `total_reviews = 0`: vẫn hiện đủ khối, các số là `0` và `—`, kèm dòng "Không có dữ liệu trong khoảng đã chọn". **Đừng ẩn khối nào** |
| lỗi | banner đỏ + nút "Thử lại" |
| lọc sai | thông báo cạnh ô ngày, **giữ nguyên** giá trị đã nhập |

---

### Cấm — màn này dễ vi phạm nhất

- **KHÔNG biểu đồ tròn.** Không biểu đồ nào cả. Chưa có thư viện vẽ đồ thị và
  không được cài thêm.
- **KHÔNG số KPI cỡ đại** chiếm nửa màn hình.
- **KHÔNG** thẻ có gradient, bóng đổ dày, hay icon trang trí.
- KHÔNG sửa `src/api/api-types.ts`
- KHÔNG gọi `fetch`/`axios` trực tiếp — dùng `client`
- KHÔNG lưu gì vào `localStorage`/`sessionStorage`
- KHÔNG dùng `dangerouslySetInnerHTML`
- KHÔNG viết cứng danh sách trạng thái/quyết định — lấy từ `useFilters()`
- KHÔNG tự viết hàm định dạng — dùng `src/lib/format.ts`
- KHÔNG cài thêm thư viện nào
- KHÔNG sửa file nào ngoài `DashboardPage.tsx`

**Xong thì:** chạy `npx tsc --noEmit` và báo kết quả. Không tự ý làm màn khác.

---

## NHIỆM VỤ 4 — Job detail

**Màn này có hành động THẬT đầu tiên trong cả sản phẩm, và hành động đó tiêu
tiền.** Đọc kỹ phần "Nút Thử lại" trước khi viết.

**Bối cảnh.** Người đọc đang chẩn đoán vì sao một job thất bại và quyết định có
chạy lại hay không. Trường quan trọng nhất trên màn hình là `last_error`.

**Đọc bốn file này trước khi viết dòng code nào:**

1. `multiagent/console_ui/README.md` — 5 quy tắc bắt buộc
2. `docs/console-ui/design-system.md` — bảng màu, class, mục 4b hàm định dạng
3. `docs/console-ui/stitch-briefs.md` mục "4. Job detail"
4. `docs/console-ui/integration.md` — mã lỗi, đặc biệt `409` và `400`

**Xem `JobsPage.tsx`** — dùng lại đúng thẻ, pill trạng thái, và bảng màu.

**Sửa đúng một file:** `multiagent/console_ui/src/pages/JobDetailPage.tsx`.

---

### ĐỌC TRƯỚC: phần logic đã viết sẵn, KHÔNG được viết lại

File `JobDetailPage.tsx` **đã có sẵn** toàn bộ phần gọi API và xử lý retry:

- `useQuery` đọc chi tiết job
- `useMutation` gọi `POST /jobs/{id}/retry` với `confirm_cost: true`
- `onSuccess` điều hướng sang **job mới** (`navigate(/jobs/${jobMoi.public_id})`)
- `onError` bắt `ConsoleApiError` và đặt thông báo
- `<RequireRole role="operator">` bọc quanh nút

**Việc của bạn là KHOÁC GIAO DIỆN LÊN phần đó, không viết lại nó.** Cụ thể:

- Giữ nguyên `useMutation`, `onSuccess`, `onError` — không đổi tham số, không
  đổi thứ tự, không bỏ `replace: true`
- Giữ nguyên `confirm_cost: true` và **giữ nguyên việc nó chỉ được gửi sau khi
  người dùng bấm xác nhận** trong hộp thoại
- Giữ nguyên `<RequireRole role="operator">`

Lý do: `POST /retry` chạy lại pipeline AI, tức là **gọi API tính tiền thật**.
Server có cổng chặn `confirm_cost` — gửi `false` thì trả `400`. Viết lại phần
này là chỗ duy nhất trong cả dự án mà một lỗi code làm mất tiền.

---

### 22 trường, chia sáu nhóm

Bố cục hai cột: nhóm "Trạng thái" và "Kết quả" ở cột trái (rộng hơn), các nhóm
còn lại ở cột phải. `last_error` chiếm hết chiều ngang bên dưới.

**Nhóm 1 — Trạng thái** (nổi bật nhất)
- `status` — pill, 5 giá trị, nhãn và màu **y hệt `JobsPage.tsx`**
- `attempts` — số nguyên, "Đã thử N lần"
- `source` — chuỗi tự do (`event`, `reconcile`, `admin_retry`, …)

**Nhóm 2 — Lỗi**
- `last_error` — **có thể null**. Đây là thứ người đọc vào xem. Cho nó một
  khối riêng chiếm hết chiều ngang, nền xám nhạt, chữ monospace, xuống dòng
  được (`whitespace-pre-wrap break-words`), và cuộn dọc nếu quá dài
  (`max-h-64 overflow-y-auto`). Null thì **ẩn hẳn khối này**, đừng hiện khối
  rỗng.

**Nhóm 3 — Thời gian** (ghi nhãn `TIMEZONE_LABEL`)
- `created_at`, `updated_at` — dùng `formatDateTime`

**Nhóm 4 — Nội dung**
- `external_content_id`, `external_revision_id` (**có thể null**),
  `content_type`, `langcode`

**Nhóm 5 — Ngữ cảnh**
- `site_slug`, `site_name` — hiện `site_name` là chính, `site_slug` nhỏ bên dưới
- `site_id`, `profile_id` — UUID, dùng `shortId`, monospace
- `policy_version`

**Nhóm 6 — Nhận dạng và liên kết**
- `public_id` — UUID đầy đủ, monospace, có nút copy nếu tiện
- `correlation_id` — `shortId`, monospace
- `supersedes_job_public_id` (**có thể null**) — khi có, nhãn **"Thay thế cho
  job"** và là **link tới `/jobs/{id}`**
- `run_public_id` (**có thể null**) — khi có, nhãn **"Kết quả review"** và là
  **link tới `/reviews/{id}`**
- `run_scored_at` (**có thể null**) — `formatDateTime`
- `writeback_status` (**có thể null**) — pill, nhãn tiếng Việt theo bảng
  writeback trong `design-system.md`
- `saved_result_available` — boolean, hiện "Có"/"Không"

**Mọi giá trị null hiện `—`.** Không hiện ô trống, không hiện "N/A".

---

### Nút "Thử lại" — phần nhạy cảm nhất

**Chỉ hiện khi cả hai điều kiện đúng:**
1. `status === "failed"` — trạng thái khác thì **không vẽ nút, kể cả dạng mờ**
2. Role là operator hoặc admin — đã có `<RequireRole role="operator">` lo

**Bấm nút mở hộp thoại xác nhận, không gọi API ngay.** Hộp thoại phải có:

- Câu cảnh báo rõ: **"Thử lại sẽ chạy lại pipeline AI và có thể phát sinh chi
  phí."**
- Ô "Lý do" (không bắt buộc)
- Nút "Xác nhận thử lại" (nút chính) và "Hủy" (nút phụ)
- Trạng thái đang gửi: nút đổi chữ thành "Đang thử lại…" và bị vô hiệu

**Sau khi thành công**, code sẵn có đã điều hướng sang job mới. Thêm một dòng
thông báo ngắn trên màn hình mới rằng đây là job vừa tạo — nếu không, người
dùng thấy màn hình giống hệt và tưởng không có gì xảy ra.

**Khi lỗi**, hiện thông báo **trong hộp thoại**, không đóng hộp thoại:

| Mã | `code` | Thông báo gợi ý |
|---|---|---|
| 409 | `conflict` | "Không thể thử lại: job không còn ở trạng thái thất bại." |
| 403 | `forbidden` | "Bạn không có quyền thực hiện thao tác này." |
| 400 | `cost_not_confirmed` | Lỗi lập trình, không nên xảy ra — ghi console |

---

### Năm trạng thái

| Trạng thái | Hiện gì |
|---|---|
| đang tải | skeleton cho từng nhóm, giữ nguyên bố cục |
| job `failed` | đầy đủ + nút "Thử lại" + khối `last_error` |
| job `done`/`running`/… | đầy đủ, **không có nút Thử lại**, không có khối lỗi |
| không tìm thấy (404) | trang trống: "Không tìm thấy job" + link quay lại danh sách |
| không đủ quyền (403) | "Bạn không có quyền xem nội dung này", **không chuyển trang** |

---

### Ràng buộc

- **KHÔNG viết lại `useMutation` / `onSuccess` / `onError` / `RequireRole`**
- KHÔNG gửi `confirm_cost: true` trước khi người dùng bấm xác nhận
- KHÔNG vẽ nút Thử lại khi `status !== "failed"`
- KHÔNG sửa `src/api/api-types.ts`
- KHÔNG gọi `fetch`/`axios` trực tiếp — dùng `client`
- KHÔNG lưu gì vào `localStorage`/`sessionStorage`
- KHÔNG dùng `dangerouslySetInnerHTML` — `last_error` là văn bản tự do từ hệ
  thống, render bằng `{}` của React
- KHÔNG viết cứng danh sách trạng thái — lấy từ `useFilters()`
- KHÔNG tự viết hàm định dạng — dùng `src/lib/format.ts`
- KHÔNG thêm nút xóa/hủy job/sửa job — API không có
- KHÔNG cài thêm thư viện nào
- KHÔNG sửa file nào ngoài `JobDetailPage.tsx`

**Xong thì:** chạy `npx tsc --noEmit` và báo kết quả. Không tự ý làm màn khác.

---

## Ba nhiệm vụ còn lại

Làm lần lượt, mỗi màn xong thì review rồi mới sang màn sau. Khi tới lượt màn
nào, nhiệm vụ đó sẽ được viết đủ ra như hai nhiệm vụ trên — **đừng suy ra từ
bảng**, vì chỉ dẫn gián tiếp là thứ đã làm lệch bản thiết kế Stitch hôm
2026-08-20.

Bảng dưới chỉ để biết trước quy mô:

| Nhiệm vụ | File trang | Mục trong stitch-briefs | Quy mô |
|---|---|---|---|
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

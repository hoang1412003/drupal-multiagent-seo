# Handoff: Bảng báo cáo lỗi Multi-Agent trong màn soạn bài Drupal

## Tổng quan
Thiết kế lại khối "Đánh giá AI" hiện có trong form edit node (module `vf_ai_review`) của Drupal, để hiển thị lỗi từ 4 agent (SEO, Content Quality, Brand Voice, Compliance) rõ ràng, có thể thao tác (nhảy tới lỗi, đánh dấu đã xử lý, sửa nhanh), thay cho khối tĩnh hiện tại.

## Về các file thiết kế
Các file `.dc.html` trong bundle này là **thiết kế tham chiếu dựng bằng HTML** — mô phỏng đúng giao diện, hành vi, dữ liệu mẫu. Đây **không phải code để copy thẳng vào Drupal**. Việc cần làm là **dựng lại giao diện này trong môi trường thật của dự án**:
- Layout, CSS: chuyển thành Twig template (`.html.twig`) + PCSS/CSS theo chuẩn theme Claro (`web/core/themes/claro`), tương tự cách `vf_ai_review.module` + `AiReportRenderer.php` + `css/vf_ai_review.css` đang làm.
- Tương tác (nhảy lỗi, lọc, đánh dấu đã xử lý, sửa nhanh): viết lại bằng vanilla JS/Drupal behaviors (`Drupal.behaviors`), gắn qua `vf_ai_review.libraries.yml`, tương tự cách `vf_ai_trigger/js/vf_ai_trigger.js` đang poll trạng thái.
- KHÔNG nhúng nguyên file HTML này vào Drupal.

## Độ hoàn thiện (Fidelity)
**Hi-fi.** Màu sắc, khoảng cách, typography lấy đúng biến của theme Claro (`css/base/variables.pcss.css`, `css/components/form*.pcss.css`, `css/components/details.pcss.css`). Nội dung mẫu (bài "Hướng dẫn sạc pin VF8") là dữ liệu giả để minh hoạ — cần thay bằng dữ liệu thật từ `field_ai_report_json`.

## File thiết kế trong bundle
- `Phuong-an-1b.dc.html` — **bản được chọn**, dựng đầy đủ 7 trạng thái + tương tác thật. Mở trực tiếp bằng trình duyệt để xem/thao tác thử.
- `Ban-so-sanh-1a-1b-2a.dc.html` — 2 phương án ban đầu (1a: panel cột phải; 1b: băng sticky trên đầu) + bản gộp 2a, giữ lại để tham khảo hướng đã bị loại.
- `Hien-trang-Man-soan-bai.dc.html` — bản dựng lại đúng UI Claro **hiện tại** (trước khi thiết kế lại), dùng để so sánh trước/sau.

Mở các file `.dc.html` trực tiếp trong trình duyệt (double-click hoặc kéo vào tab) để xem đầy đủ, không cần server.

## Bối cảnh hệ thống (đọc trước khi code)
- Module Drupal liên quan: `web/modules/custom/vf_ai_review/` (hiển thị báo cáo trong form edit) và `web/modules/custom/vf_ai_trigger/` (bắn job chấm + poll trạng thái, JS tại `js/vf_ai_trigger.js`).
- File hiện tại cần thay thế/viết lại: `vf_ai_review.module` (hook_form_alter gắn khối vào form), `src/AiReportRenderer.php` (dựng HTML báo cáo từ JSON), `css/vf_ai_review.css`.
- Dữ liệu báo cáo AI đọc từ field JSON trên node (ví dụ `field_ai_report_json`) — cấu trúc gồm: điểm tổng, điểm theo agent (SEO/CQ/BV/CP), danh sách issue (mã lỗi như `SEO1`, `CQ3`, `BV1`, `CP8`, field liên quan, mức độ, mô tả, trích dẫn), `veto_reason` nếu bị chặn, timestamp chấm, số bản nội dung (revision) tại thời điểm chấm.
- Multi-agent backend ở `multiagent/src/agents/*.py` (seo.py, content_quality.py, brand_voice.py, compliance.py) và `multiagent/src/graph.py` (aggregator_node) — đây là nguồn sinh ra JSON báo cáo, tham khảo để biết đúng field/mã lỗi/severity đang tồn tại.

## 7 trạng thái cần hỗ trợ
Băng trạng thái (sticky, đầu form, dưới tab View/Edit) đổi toàn bộ nội dung + màu theo 1 trong 7 trạng thái:

1. **co_loi (Cần sửa)** — mặc định khi có issue nhưng không veto. Băng màu đỏ nhạt, đếm số vấn đề/số trường, có nút Trước/Sau + chip lọc mức (Chặn/Cần sửa/Gợi ý).
2. **chua_cham (Chưa chấm)** — bài chưa gửi agent. Băng xám, nút "Chấm ngay", ẩn hết thẻ lỗi/viền trường về mặc định.
3. **dang_cham (Đang chấm)** — hiện tiến độ từng agent (xong/đang chạy/chờ) + thanh progress, ẩn thẻ lỗi.
4. **dat (Đạt)** — băng xanh lá, mỗi trường hiện dòng "Không phát hiện vấn đề" (icon check), điểm theo agent toàn xanh.
5. **veto (Bị từ chối)** — băng đỏ đậm, badge "VETO", CHỈ hiện các issue severity=block, các issue khác ẩn, điểm theo agent hiện "veto" cho agent chặn.
6. **stale (Nội dung đã sửa sau chấm)** — băng xám, ghi rõ "kết quả cho bản #N", toàn bộ thẻ lỗi mờ đi (opacity ~0.5), nút "Chấm lại bản mới".
7. **thieu (Chấm chưa đầy đủ)** — băng đỏ nhạt, badge "3/4 agent", ẩn issue của agent bị lỗi, điểm theo agent hiện "lỗi" + lý do (timeout/job id) cho agent đó.

Quy tắc dùng chung mọi trạng thái (xem hàm `apply()` trong `<script>` của `Phuong-an-1b.dc.html`):
- Dòng cạnh nút Save ("Còn N lỗi chặn xuất bản…") luôn tính từ **số issue severity=block đang thực sự hiển thị** (không phải đếm tĩnh) — quan trọng để không bị sai khi chuyển qua lại giữa các trạng thái.
- Hộp báo cáo dưới mỗi field tự ẩn khi field đó không còn issue nào đang hiển thị; tiêu đề hộp ("AI phát hiện N vấn đề…") đếm lại theo số thẻ đang hiển thị.
- Viền field (Title input / Body CKEditor box / Meta textarea) đổi màu theo mức nghiêm trọng cao nhất đang có trong field: đỏ nếu có block, vàng nếu có fix, giữ xám mặc định nếu không có hoặc đã xử lý hết.

## Layout & thành phần chi tiết

### Băng trạng thái (sticky band)
- `position: sticky; top: 0`, `z-index` cao hơn nội dung, nền trắng, `box-shadow: 0 2px 8px rgba(0,0,0,.1)`, viền dưới `1px solid #dedfe4`.
- Padding `12px 24px`, `display:flex; flex-wrap:wrap; align-items:center; gap:14px`.
- Bên trái: badge trạng thái (pill, `border-radius:13px`, dot màu + label) → số vấn đề/trường → divider `1px` cao 22px màu `#dedfe4` → chip lọc mức (chỉ ở co_loi) → điểm tổng.
- Bên phải (căn `margin-left:auto`): "Lỗi n/N" → nút mũi tên Trước/Sau (`36×36px`, viền `#919297`) → nút "Chấm lại" → link "Ẩn báo cáo".

### Thẻ lỗi dưới mỗi field (rich card)
Mỗi field (Title/Body/Meta) có 1 hộp `border:1px solid #dedfe4; border-radius:3px` chứa:
- Header: "AI phát hiện N vấn đề ở trường này" (12.5px, bold, `#55565b`, nền `#f8f9fc`) + link "Thu gọn/Mở rộng".
- Danh sách thẻ, mỗi thẻ `display:flex; gap:12px; padding:12px`, `border-left:3px solid <màu mức>` (đỏ `#d72222` cho block, vàng `#b7791f` cho fix, xám `#8e929c` cho tip):
  - Badge mã lỗi (mono font, nền nhạt theo mức, ví dụ block: nền `#fdeaea` chữ `#a51b1b`; fix: nền `#fdf3d6` chữ `#7a5410`; tip: nền `#eceef2` chữ `#4a4b50`).
  - Tên nhóm agent cạnh mã lỗi (SEO/Chất lượng/Brand Voice/Tuân thủ).
  - Badge "CHẶN XUẤT BẢN" (nền đỏ đặc `#d72222`, chữ trắng) chỉ hiện với severity=block.
  - Tiêu đề lỗi (14.5px, 600), mô tả (13.5px, `#55565b`).
  - Trích dẫn nguyên văn nếu có (`font-style:italic`, nền `#fafafb`/`#fff`, viền trái `2px solid #dedfe4`).
  - Hàng hành động: checkbox "Đã xử lý", link "Không đồng ý", nút "Sửa thành…" nếu có gợi ý sửa tự động (chỉ có ở BV1 trong bản mẫu — tick logic cho các mã khác nếu backend hỗ trợ auto-fix).

### Cột phải (giữ nguyên khung Drupal)
- Card "Not published" (trạng thái xuất bản + last saved + author) — không đổi so với hiện tại.
- Card mới "Điểm theo agent": 4 dòng SEO/Chất lượng/Brand Voice/Tuân thủ, mỗi dòng thanh progress `80px × 5px` màu theo điểm (xanh ≥80, vàng 60-79, đỏ <60) + số điểm; dòng chú thích thời gian chấm + bản nội dung.
- Giữ nguyên toàn bộ `<details>` mặc định của Drupal: Revision log message, Menu settings, Comment settings, URL alias, Authoring information, Promotion options — KHÔNG được lược bớt (bản đầu tiên có lược, đã bỏ theo phản hồi).

### Field-level border theo mức (toggle được)
Viền `input`/box CKEditor/`textarea` đổi theo mức lỗi cao nhất trong field. Nên làm thành 1 tuỳ chọn bật/tắt ở phía dev/QA (tương ứng tweak `vienTruongTheoMuc` trong bản thiết kế) vì có thể gây nhiễu khi field vừa có input validation lỗi khác.

## Tương tác cần cài đặt
- **Trước/Sau**: duyệt tuần tự qua danh sách issue đang hiển thị (theo bộ lọc hiện tại), cuộn tới field/đoạn text liên quan (`scrollTo` mượt, offset ~160px cho sticky band), viền `2px solid #003ecc` cho thẻ đang chọn, và nháy sáng (keyframe `box-shadow` 2 lần) đoạn bôi vàng/đỏ tương ứng trong Body.
- **Chip lọc mức** (Tất cả/Chặn/Cần sửa/Gợi ý): ẩn/hiện thẻ theo `severity`, cập nhật lại "Lỗi n/N" theo tập đang lọc.
- **Đã xử lý** (checkbox trên từng thẻ): đánh dấu issue đã giải quyết (opacity mờ thẻ, đổi viền trái về xám), cập nhật lại đếm ở băng, header field, và dòng cảnh báo chặn xuất bản.
- **Sửa thành "VF 8"**: ví dụ auto-fix — ghi đè giá trị input Title, cập nhật trích dẫn hiển thị, tự tick "Đã xử lý", disable nút.
- **Thu gọn/Mở rộng** theo field, **Ẩn/Hiện báo cáo** toàn bộ (ẩn hết các hộp `data-report`, đổi text link).
- Toàn bộ tương tác nên là **progressive enhancement**: nếu JS lỗi, form vẫn dùng được bình thường (chỉ mất phần tương tác báo cáo).

## Design tokens (từ theme Claro — dùng lại, không tạo mới)
- Xanh chính (link/nút primary/focus): `#003ecc`, hover `#0036b1`.
- Chữ chính: `#232429`; chữ phụ: `#55565b` / `#6a6b70`; viền mặc định: `#919297` (input) / `#dedfe4` (khung/card).
- Nền phụ: `#f3f4f9` (vùng header trang), `#fafafa`/`#fbfbfd`/`#f8f9fc` (nền nhạt trong card).
- Mức nghiêm trọng: Chặn `#d72222` (nền nhạt `#fdeaea`, chữ đậm `#a51b1b`); Cần sửa `#b7791f` (nền nhạt `#fdf3d6`, chữ đậm `#7a5410`); Gợi ý `#8e929c` (nền nhạt `#eceef2`, chữ đậm `#4a4b50`); Đạt/thành công `#3f7a52` (nền nhạt `#e3f3e6`, chữ đậm `#265c35`).
- Font: kế thừa theme Claro — `BlinkMacSystemFont, -apple-system, "Segoe UI", Roboto, sans-serif`.
- Bo góc: `2px` (input/nút, đúng Claro), `3px` (card thẻ lỗi mới), `12–13px` (pill/chip/badge).
- Khoảng cách: theo lưới Claro hiện có (`margin-bottom:22–24px` giữa các field, `padding:11px 15px` trong input, `12px` trong thẻ lỗi).

## State / dữ liệu cần từ backend
Mỗi lần render cần một object báo cáo dạng:
```
{
  trangThai: "co_loi" | "chua_cham" | "dang_cham" | "dat" | "veto" | "stale" | "thieu",
  diemTong: number,
  diemTheoAgent: { seo, cq, bv, cp } | null (null nếu chưa chấm),
  agentLoi: { ma: "bv", lyDo: "timeout sau 30s", jobId: "4182" } | null,
  chamLuc: ISODate,
  banNoiDung: number,
  issues: [
    { id, ma: "CP8", agent: "compliance", field: "body"|"title"|"meta"|...,
      severity: "block"|"fix"|"tip", tieuDe, moTa, trichDan?, targetSelector?,
      autoFix?: { nhan: "Sửa thành \"VF 8\"", tim, thay } }
  ]
}
```
Ánh xạ với dữ liệu thật: `veto_reason` (từ `review_detail.html`/graph aggregator) → trạng thái `veto`; agent trả lỗi/timeout trong `graph.py` → trạng thái `thieu`; so sánh `content_hash`/revision hiện tại với revision đã chấm → trạng thái `stale`.

## Assets
Icon dùng file SVG gốc của theme Claro (không tạo icon mới): `chevron-right` (2 màu `#545560`/`#0036b1`), `checkmark` trắng trên nền tròn, `arrow-breadcrumb`. Lấy tại `web/core/themes/claro/images/icons/`.

## Việc KHÔNG cần làm lại
Toolbar Drupal admin, breadcrumb, tab View/Edit/Delete/Revisions, các field Title/Body/Tags/Image/Meta description, khối "Not published", các `<details>` mặc định — giữ nguyên markup/CSS hiện có của Claro, chỉ chèn thêm phần báo cáo AI mô tả ở trên.

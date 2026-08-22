# Thiết kế UI báo cáo trong giao diện soạn bài Drupal

**Phiên bản:** v1 (2026-07-27)
**Trạng thái:** **đã triển khai (2026-08-04)** — mức P1, xem `docs/superpowers/specs/2026-08-03-vf-ai-review-module-design.md`. Bốn chỗ trong tài liệu này đã được đính chính sau khi chạy thật: mục 2 (field vốn không hiện trên form), mục 4.4 (cơ chế `changed` hỏng), mục 5 (suy giảm mềm không tự động), mục 4.3 và mục 9 (2026-08-07: khối "đang chấm" và nút "chấm lại" chuyển từ polling sang event-driven, xem `architecture.md` mục 9)
**Liên quan:** `docs/architecture.md` mục 2.3 (write-back) và mục 9 (tự động hóa); `docs/roadmap.md` Sprint 2 ("Dựng UI báo cáo cơ bản")

---

## 1. Vì sao hạng mục này rủi ro nhất

Đề bài yêu cầu: *"trả báo cáo lỗi/rủi ro theo từng field **ngay trong giao diện editor**"*. Đây là **deliverable bắt buộc**, không phải nice-to-have - và cũng là thứ hội đồng nhìn thấy đầu tiên khi demo.

Ba lý do nó rủi ro hơn phần còn lại của backlog:

1. **Là phần duy nhất cần PHP/Drupal.** Toàn bộ phần còn lại của dự án là Python. Đây là ngăn xếp khác, quy ước khác, vòng lặp sửa-thử khác.
2. **Chưa có gì.** `drupal/web/modules/custom/` chưa tồn tại; chưa có dòng code Drupal nào ngoài script tạo field.
3. **Không thể "gần đúng".** Một pipeline chấm điểm sai vài phần trăm vẫn demo được; một giao diện vỡ thì không.

---

## 2. Trạng thái hiện tại và khoảng cách

Hiện `write_back()` ghi 3 field ([`drupal/scripts/create_ai_fields.php`](../drupal/scripts/create_ai_fields.php)):

| Field | Kiểu | Nội dung hiện tại |
|---|---|---|
| `field_ai_status` | `list_string` | `publish` / `needs_revision` / `rejected` |
| `field_ai_score` | `float` | 0-100, hoặc **null** khi chưa chấm được |
| `field_ai_suggestions` | `text_long` | Một chuỗi text dài, gom theo field bằng dấu `── Tiêu đề (title) ──` |

**Nếu không làm gì thêm**, người soạn bài mở node ra sẽ thấy 3 field này dưới dạng **widget nhập liệu**: một ô select, một ô số, một textarea đầy chữ. Tức là:

- Trông như form nhập liệu, không như báo cáo
- **Người soạn sửa được** giá trị AI ghi vào - dữ liệu đánh giá bị ghi đè, không ai biết
- Không phân biệt được mức nghiêm trọng, không nhóm được theo agent

Nó *chạy*, và về mặt chữ nghĩa thì "báo cáo có hiện trong editor". Nhưng không đạt tinh thần yêu cầu.

**Đính chính (2026-08-04).** Đoạn trên **mô tả sai tình trạng thực tế**. Kiểm tra `core.entity_form_display.node.article.default` cho thấy cả 4 field AI đều nằm trong danh sách `hidden` — Drupal **không tự thêm** field mới vào form display, mà `create_ai_fields.php` chỉ tạo field chứ không cấu hình hiển thị. Nghĩa là người soạn bài **chưa bao giờ nhìn thấy** chúng, cũng không sửa được. Rủi ro "người soạn ghi đè dữ liệu đánh giá" không tồn tại như tài liệu mô tả.

Việc ẩn 4 field bằng `#access => FALSE` trong module vẫn được giữ, nhưng vai trò đổi từ *sửa một lỗ hổng đang có* thành *lớp bảo vệ phòng khi ai đó kéo field vào form qua giao diện admin*.

**Vấn đề thật phát hiện cùng lúc:** `field_meta_description` cũng bị ẩn — nhưng đó là field **đầu vào**, người viết phải nhập được. Ẩn nó thì SEO Agent báo *"thiếu meta description"* mà người viết không tìm đâu ra ô để thêm, phá vỡ chính vòng lặp mà module này xây. Đã bổ sung phần cấu hình form display vào `drupal/scripts/create_ai_fields.php` để môi trường dựng lại từ đầu cũng ra kết quả đúng.

---

## 3. Ba mức triển khai

| Mức | Cách làm | Code | Kết quả |
|---|---|---|---|
| **P0 - phương án lùi** | Cấu hình "Manage form display" của core, kéo 3 field AI vào nhóm sidebar | 0 dòng | Chạy được, nhưng vẫn là widget sửa được. Chỉ dùng nếu hết thời gian |
| **P1 - khuyến nghị** | Module nhỏ `vf_ai_review`, dùng `hook_form_node_form_alter()` | ~150 dòng PHP + CSS | Khối báo cáo read-only + chú thích ngay dưới từng field |
| **P2 - nếu dư** | Field formatter/widget riêng, dùng lại được ở chỗ khác | Nhiều hơn | Không cần cho phạm vi đề tài |

**Chọn P1.** P0 để dành làm phương án lùi nếu tiến độ trượt - và nêu được phương án lùi trong tài liệu chính là quản trị rủi ro, không phải thiếu tham vọng.

---

## 4. Thiết kế P1

### 4.1. Hai mức hiển thị

**(a) Khối tổng quan** - đặt trong cột `advanced` (sidebar phải của form soạn bài, chỗ chứa "Thông tin xuất bản", "Tác giả"...), dạng `#type => 'details'`:

```
┌─ Đánh giá AI ────────────────────┐
│ Đề xuất:  ⚠ Cần sửa              │
│ Điểm:     76.5 / 100             │
│ Chấm lúc: 27/07/2026 14:32       │
│                                   │
│ 5 vấn đề trên 3 trường            │
│ • Tiêu đề (2)                     │
│ • Meta description (1)            │
│ • Nội dung (2)                    │
└───────────────────────────────────┘
```

**(b) Chú thích ngay dưới từng field** - chèn markup vào `#suffix` của chính widget field tương ứng:

```
Tiêu đề  [ Hướng dẫn sạc pin ô tô điện VinFast đúng cách    ]
         ⚠ SEO — tiêu đề 48 ký tự, nên trong khoảng 50-60
         ⚠ Brand Voice — viết "VF8", chuẩn là "VF 8"
```

**Mức (b) mới thật sự đáp ứng chữ "theo từng field ngay trong giao diện editor" của đề bài.** Mức (a) là tổng quan để người duyệt nắm nhanh; mức (b) là chỗ người viết thực sự sửa. Làm cả hai, và nêu rõ khi demo rằng (b) là phần đáp ứng yêu cầu.

Ánh xạ field báo cáo → widget trên form:

| `field` trong báo cáo | Vị trí chèn trên form |
|---|---|
| `title` | `$form['title']` |
| `body`, `summary` | `$form['body']` |
| `meta_description` | `$form['field_meta_description']` |
| `url_alias` | `$form['path']` |
| `image_alt` | `$form['field_image']` |

### 4.2. Khoá 3 field AI, không cho sửa

Ẩn hẳn widget của `field_ai_status`, `field_ai_score`, `field_ai_suggestions` khỏi form (`'#access' => FALSE`) - nội dung đã được render lại ở khối tổng quan, giữ widget chỉ tạo rủi ro người soạn sửa nhầm.

Không dùng `'#attributes' => ['readonly' => 'readonly']`: đó chỉ là thuộc tính HTML, không chặn được ở phía server.

### 4.3. Ba trạng thái phải phân biệt

**Cập nhật (2026-08-07):** hệ thống nay chạy event-driven (`architecture.md` mục 9.1), độ trễ thật đo được từ Save tới lúc job bắt đầu chạy là ~2 giây (không còn ~30 giây của polling); vòng đối soát mục 9.2 chỉ còn là lưới an toàn chạy mỗi 300 giây. Dù độ trễ đã ngắn hơn nhiều, "chưa có kết quả" (job đang `queued`/`running`) vẫn là trạng thái bình thường trong vài giây đầu, chứ không phải lỗi:

| Trạng thái | Điều kiện | Hiển thị |
|---|---|---|
| Chưa chấm | 3 field AI đều trống | *"Chưa được đánh giá. Chuyển bài sang 'Needs Review' để hệ thống chấm."* |
| Đã chấm | Có `field_ai_status` và `field_ai_score` | Khối báo cáo đầy đủ |
| **Chấm chưa đầy đủ** | Có `field_ai_status` nhưng `field_ai_score` **null** | Khối báo cáo + cảnh báo nổi bật: *"Một số tiêu chí không đánh giá được - cần người xem thủ công"* |

Trạng thái thứ ba tương ứng đúng trường hợp Compliance Agent lỗi (`architecture.md` mục 6.4). Điểm để trống chứ không phải 0 - và UI **không được** hiển thị ô trống đó thành "0 điểm", vì đó chính là hiểu nhầm mà bug đã sửa muốn tránh.

### 4.4. Kết quả cũ so với nội dung hiện tại - vấn đề dễ bỏ sót

Người viết sửa bài **sau khi** AI chấm là chuyện thường xuyên. Khi đó báo cáo đang hiển thị nói về một phiên bản nội dung không còn tồn tại - và người duyệt tin vào nó là rủi ro thật, đúng loại rủi ro hệ thống này sinh ra để giảm.

Xử lý: lúc chấm, lưu lại **mốc thời gian `changed` của node**. Khi render, so với `changed` hiện tại:

```
Nếu changed_hiện_tại > changed_lúc_chấm:
    Hiện băng cảnh báo: "⏱ Nội dung đã thay đổi sau khi chấm (14:32).
                         Kết quả bên dưới có thể không còn đúng."
    Làm mờ phần chi tiết
```

Cần thêm một field cho việc này - xem mục 5.

**Đính chính (2026-08-04): cơ chế so mốc `changed` ở trên HỎNG.** Chính lệnh PATCH của `write_back()` làm `changed` nhảy, nên so mốc đó sẽ **luôn** báo "nội dung đã thay đổi" ngay sau khi chấm — cảnh báo báo sai mọi lúc thì người duyệt học cách phớt lờ, tệ hơn là không có.

Bằng chứng đo trên DB: `changed` của nid 2/3/4 đúng bằng thời điểm chạy smoke test chấm lại (09:45:17 / 09:45:24 / 09:45:32).

**Đã thay bằng hash nội dung:** lúc chấm lưu `sha256(title + "\n" + body + "\n" + summary + "\n" + meta_description)`; lúc render tính lại từ giá trị hiện tại rồi so. Hash chỉ đổi khi nội dung **thật sự** đổi, vì PATCH không đụng 4 field đó.

Kiểm chứng thực tế sau khi triển khai: sửa tiêu đề → cảnh báo hiện; sửa trả lại như cũ → cảnh báo biến mất, dù `changed` lúc này đã muộn hơn `scored_at` 13 tiếng. Cơ chế cũ sẽ báo sai ở đúng tình huống này. Chi tiết: spec `2026-08-03-vf-ai-review-module-design.md` mục 4.3.

### 4.5. Không được trông như AI đã duyệt

Hệ thống chỉ **đề xuất**; nút Publish vẫn của người (`architecture.md` mục 2.3). UI phải phản ánh đúng điều đó bằng từ ngữ:

| Không dùng | Dùng |
|---|---|
| "Trạng thái: Đạt" | "**Đề xuất**: Có thể xuất bản" |
| "AI đã duyệt" | "**Đề xuất** của hệ thống đánh giá" |
| Nút "Xuất bản theo AI" | (không có nút nào) |

Đây không phải chi tiết câu chữ vụn vặt - nó là ranh giới trách nhiệm giữa hệ thống và người duyệt, và là điểm sẽ bị hỏi khi bảo vệ.

> ⚠️ **Dòng đầu của bảng trên đã HẾT HIỆU LỰC từ 2026-08-22.** Giao diện nay
> **không hiện nhãn đề xuất nào** (kể cả "Đề xuất: Có thể xuất bản"), vì ranh
> giới `publish`/`needs_revision` dựa trên ngưỡng chưa calibrate. Tinh thần của
> mục 4.5 giữ nguyên — và bỏ hẳn nhãn còn tuân thủ nó chặt hơn. Lý do đầy đủ và
> điều kiện để bật lại: [mục 10.7](#107-cố-ý-không-hiện-nhãn-publish--needs_revision).

---

## 5. Dữ liệu: text blob hay JSON

Hiện `field_ai_suggestions` là **một chuỗi text** nối bằng `── Tiêu đề (title) ──`. Để render theo mục 4.1(b) - chú thích đúng field, phân biệt agent, phân biệt mức nghiêm trọng - module PHP sẽ phải **parse ngược chuỗi đó**. Cách này mong manh: đổi một ký tự phân cách bên Python là vỡ giao diện bên PHP, mà không test nào bắt được.

**Giải pháp: thêm một field JSON, giữ nguyên field text.**

| Field | Vai trò | Ai đọc |
|---|---|---|
| `field_ai_suggestions` *(đã có)* | Text người đọc được | Người - khi **không** có module (P0) |
| `field_ai_report_json` *(thêm)* | Báo cáo có cấu trúc: `{field, agent, severity, message}[]` + `note`, `veto_reason`, `changed_at` | Module PHP - để render |

Ưu điểm của cách này là **suy giảm mềm (graceful degradation)**: không có module thì vẫn đọc được text; có module thì render đẹp từ JSON. Và không có coupling ngầm qua định dạng chuỗi.

**Đính chính (2026-08-04): suy giảm mềm KHÔNG tự động như câu trên hàm ý.** Vì 4 field AI bị ẩn trong form display (xem đính chính mục 2), tắt module đi thì người dùng **không thấy gì cả** chứ không phải "vẫn đọc được text".

Kiểm chứng thực tế: `ddev drush pmu vf_ai_review` → khối tổng quan và chú thích biến mất, form vẫn dùng bình thường không lỗi, **dữ liệu còn nguyên** (`field_ai_score` 79.25, `field_ai_suggestions` 2304 ký tự, `field_ai_report_json` 3081 ký tự).

Phát biểu đúng phải là: **tắt module mất phần hiển thị, không mất dữ liệu.** Muốn đọc lại mà không có module thì vào *Quản lý hiển thị form* kéo `field_ai_suggestions` ra — đúng là phương án lùi P0 ở mục 3, chỉ khác là nó cần một thao tác cấu hình chứ không tự có.

Chi phí: thêm một field vào `create_ai_fields.php`, và `write_back()` ghi 2 field thay vì 1. `field_ai_report_json` ẩn khỏi form (`'#access' => FALSE`), người dùng không bao giờ thấy JSON thô.

`changed_at` (mốc `changed` của node lúc chấm, mục 4.4) nằm luôn trong JSON - không cần field thứ năm.

---

## 6. Cấu trúc module

```
drupal/web/modules/custom/vf_ai_review/
├── vf_ai_review.info.yml       # khai báo module
├── vf_ai_review.module         # hook_form_node_form_alter()
├── vf_ai_review.libraries.yml  # khai báo CSS
├── src/AiReportRenderer.php    # tách logic render khỏi hook
└── css/vf_ai_review.css        # màu theo severity, bố cục khối
```

`vf_ai_review.info.yml`:

```yaml
name: 'VF AI Review'
type: module
description: 'Hiển thị kết quả đánh giá của hệ Multi-Agent AI trong giao diện soạn bài.'
core_version_requirement: ^10 || ^11
package: 'VF O2O'
```

Điểm móc chính là `hook_form_node_form_alter()` - hook chuẩn của Drupal để can thiệp vào form soạn node. Tách phần dựng mảng render sang `AiReportRenderer` để hook mỏng và phần render test được độc lập.

Bật module: `ddev drush en vf_ai_review -y`.

---

## 7. Ảnh hưởng lên code hiện có

| File | Thay đổi |
|---|---|
| `drupal/scripts/create_ai_fields.php` | Thêm `field_ai_report_json` (kiểu `string_long`) |
| `drupal/web/modules/custom/vf_ai_review/` | Mới - toàn bộ module |
| `multiagent/src/graph.py` | `write_back_node` dựng thêm cấu trúc JSON bên cạnh chuỗi text đang có |
| `multiagent/src/drupal_client.py` | `write_back()` nhận thêm tham số `report_json`, PATCH thêm một field |
| `multiagent/scripts/` | Test: JSON sinh ra đúng schema; `changed_at` được ghi |

Không thay đổi: kiến trúc 8 node, cơ chế veto, công thức Aggregator, 4 field hiện có.

---

## 8. Rủi ro và phương án lùi

| Rủi ro | Xử lý |
|---|---|
| Chưa từng viết module Drupal, vòng lặp sửa-thử chậm | Làm khối tổng quan (4.1a) trước - dễ hơn hẳn; chú thích theo field (4.1b) sau |
| Không kịp trước demo | Lùi về **P0**: cấu hình form display, chấp nhận widget sửa được. Nêu rõ giới hạn khi demo thay vì giấu |
| Sửa CSS/markup làm vỡ giao diện admin | Chỉ chèn vào node form, không đụng theme; module tắt được bằng `drush pmu` |
| Ánh xạ field báo cáo → widget sai tên | Mảng ánh xạ ở một chỗ duy nhất (mục 4.1), sai thì bỏ qua field đó thay vì lỗi trắng trang |

**Nguyên tắc:** khối tổng quan (4.1a) là phần bắt buộc phải xong. Chú thích theo từng field (4.1b) là phần đáp ứng đúng chữ của đề bài - ưu tiên cao, nhưng nếu phải cắt thì cắt sau cùng.

---

## 9. Chưa chốt

**Cập nhật (2026-08-07):** khối trạng thái "⏳ Đang chấm" và nút "Chấm lại" **đã làm**, không còn nằm trong danh sách chưa chốt — xem `architecture.md` mục 9 và spec `superpowers/specs/2026-08-07-needs-review-automation-design.md`. Module `vf_ai_trigger` (route `/vf-ai/status/{node}` cho JS poll, route `/vf-ai/rescore/{node}` cho nút chấm lại, cả hai đòi quyền `xem bao cao ai` / `dieu khien ai`) và `js/vf_ai_trigger.js` (poll mỗi 3 giây, tự nạp lại trang khi thấy `done`, tối đa 40 lần hỏi) đã chạy thật trong lần kiểm E2E (`docs/evidence/tu_dong_hoa_e2e.txt`).

| Hạng mục | Ghi chú |
|---|---|
| Vòng phản hồi người duyệt | Khối báo cáo là chỗ tự nhiên để đặt ô *"Không đồng ý với đánh giá này"* + lý do. Đây là hạng mục backlog riêng, vẫn **chưa triển khai**; không còn bị chặn bởi nhật ký truy vết (`operations.md` mục 4) - ở đây chỉ ghi nhận điểm móc |
| Hiển thị lịch sử các lần chấm | Hiện chỉ lưu kết quả mới nhất trong 4 field AI (ghi đè). `run_log` (Postgres, đã triển khai) giữ lịch sử đầy đủ. Thiết kế productization ngày 2026-08-12 sẽ hiển thị lịch sử chi tiết ở admin Multi-Agent; đưa lịch sử rút gọn vào editor vẫn là hạng mục tùy chọn riêng |
| Đa ngôn ngữ giao diện | Chuỗi hiển thị hiện hard-code tiếng Việt; Drupal có `t()` sẵn nhưng chưa cần trong phạm vi hiện tại |

**Ranh giới UI đã chốt ngày 2026-08-12:** người viết/người duyệt vẫn chỉ dùng màn soạn bài Drupal này; họ không cần tài khoản Multi-Agent. Trang quản trị độc lập phục vụ viewer/operator/admin để theo dõi nhiều job, chi phí và lỗi vận hành, không thay thế báo cáo theo field trong editor. Xem [`superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`](superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md).

---

## 10. Thiết kế lại khối báo cáo (2026-08-16)

Mục 4 mô tả bản P1 đã chạy từ tháng 7. Mục này ghi bản **thiết kế lại** dựa trên bundle handoff `Trang hiển thị lỗi Agent/design_handoff_ai_review_panel/` (bản được chọn: `Phuong-an-1b.dc.html`). Nó **không thay thế** mục 4 — hai nguyên tắc gốc giữ nguyên: module **chỉ đọc**, và **escape mọi giá trị động**.

⚠️ Đây **không** phải "P2" ở mục 3. P2 nghĩa là field formatter/widget riêng, vẫn không cần.

### 10.1. Vì sao làm bây giờ, và vì sao chỉ làm được một phần

Việc này bị hoãn có chủ đích tới khi xong chuỗi đo lường (xong 2026-08-16). Lý do: thiết kế đòi ba thứ backend chưa có, mà hai trong số đó phải sửa `agents/*.py` + `graph.py` — **đúng đường chấm điểm đang khoá**.

**Phạm vi đã chốt: chỉ PHP/JS/CSS, không sửa một dòng Python nào.** Nhờ vậy diff đường chấm vẫn rỗng và E1/E5/E6 còn hiệu lực.

**Ba thứ cắt khỏi bản handoff, kèm lý do:**

| Cắt | Vì sao |
|---|---|
| Nút "Sửa thành…" (auto-fix) | `report_json` không có `autoFix`. Bịa dữ liệu để UI đẹp là sai. |
| Link "Không đồng ý" | Đây là H11 (vòng phản hồi biên tập viên), **chưa triển khai**, cần backend ghi feedback có cấu trúc. |
| Card "Điểm theo agent" · badge mã tiêu chí (`CP8`) · số revision | Cần `agents/*.py` hoặc `worker.py`. Badge tạm hiện **mã agent** (`CP`/`CQ`/`BV`/`SEO`). |

Tầng PHP viết kiểu **"có dữ liệu thì hiện, không có thì ẩn"**, nên khi nào mở khoá được đường chấm thì chỉ cần bật dữ liệu lên, không phải viết lại giao diện.

### 10.2. Bảy trạng thái — đều suy được từ dữ liệu đã có

| Trạng thái | Suy từ |
|---|---|
| `chua_cham` | `report === NULL` |
| `dang_cham` | `vf_ai_trigger` đã poll sẵn qua `data-vf-ai-status-url` (mục 9) |
| `stale` | so `content_hash` — module **đã tính rồi** (biến `$stale`, mục 4.4) |
| `veto` | `veto_reason` khác rỗng |
| `thieu` | `missing_agents` không rỗng |
| `dat` | `fields` rỗng |
| `co_loi` | mặc định |

### 10.3. Ánh xạ severity 4 mức → 3 mức hiển thị

| `report_json` | Hiển thị | Ghi chú |
|---|---|---|
| `critical` | `block` (Chặn xuất bản) | |
| `medium` | `fix` (Cần sửa) | |
| `low` | `tip` (Gợi ý) | |
| `null` | `fix` | Ba agent ngoài Compliance không định nghĩa severity (`graph._issue_to_json`) |

**`block` chỉ đến từ `critical` — đây là ràng buộc, không phải quy ước.** `critical` đúng bằng thứ kích hoạt quyền phủ quyết ở `graph.aggregator_node`. Nếu ánh xạ `null` → `block` thì dòng *"Còn N lỗi chặn xuất bản"* sẽ nói dối: hệ thống thật không chặn vì những lỗi đó.

Hệ quả: dòng cạnh nút Save đếm **động** theo số thẻ `block` **đang hiển thị** (sau lọc, sau đánh dấu đã xử lý), không phải đếm tĩnh — nếu không nó sai ngay khi người dùng đổi bộ lọc.

### 10.4. "Đã xử lý" lưu ở `localStorage`, khoá gồm cả content hash

Module **chỉ đọc**, không được ghi vào node — nên không lưu server được.

Khoá: `vf-ai:<nid>:<content_hash>`.

**Vì sao khoá phải có hash:** bài được chấm lại thì hash đổi → toàn bộ dấu cũ **tự hết hiệu lực**. Nếu chỉ khoá theo `nid`, dấu "đã xử lý" của lỗi cũ sẽ dính trên báo cáo mới và người duyệt tưởng đã xử lý rồi — đúng loại lỗi im lặng mà mục 4.4 đã phải xử lý một lần với mốc `changed`.

### 10.5. Cấu trúc và kiểm thử

| File | Việc |
|---|---|
| `src/AiReportRenderer.php` | Thêm suy trạng thái, ánh xạ severity, băng sticky, thẻ lỗi rich. **Giữ** `overviewHtml`/`fieldNotesHtml` cũ làm đường lùi |
| `vf_ai_review.module` | Gắn băng vào đầu form; truyền `nid` + `content_hash` qua `drupalSettings` |
| `js/vf_ai_review.js` | **Mới** — `Drupal.behaviors`, toàn bộ tương tác |
| `css/vf_ai_review.css` | Viết lại theo token Claro của handoff |
| `scripts/test_ai_report_renderer.php` | Mở rộng, **test viết trước** |

Chạy test: `ddev exec php scripts/test_ai_report_renderer.php` (PHP thuần, không cần bootstrap Drupal).

⚠️ **Không có test JS tự động trong dự án.** Phần tương tác phải kiểm tay trên Drupal thật; không được báo "đã verify" nếu chưa mở trình duyệt xem.

**Đã kiểm tay 2026-08-16** trên `node/21/edit`: nút Trước/Sau cuộn đúng tới từng lỗi, chip lọc ẩn/hiện thẻ và cập nhật lại ô đếm, dấu "đã xử lý" còn nguyên sau khi Save và mở lại. **Nhưng một lần kiểm tay không phải một bộ test:** không có gì chặn regression, nên mỗi lần sửa `js/vf_ai_review.js` đều phải kiểm lại bằng mắt.

**Progressive enhancement:** JS hỏng thì form vẫn dùng bình thường. Băng và thẻ lỗi do PHP render nên vẫn đọc được, chỉ mất tương tác.

**Đường lùi:** `ddev drush pmu vf_ai_review` — mất hiển thị, **không mất dữ liệu** (đã kiểm chứng, mục 5).

### 10.6. Bốn cái bẫy Drupal đã gặp khi dựng — đều IM LẶNG

Cả bốn chỉ lộ ra khi nhìn ảnh chụp trình duyệt thật. Không cái nào bị test PHP bắt, và ba trong bốn cái tôi **chẩn đoán sai ở lần đầu**.

**1. `#markup` nuốt `<input>` và `<label>`.** Drupal lọc `#markup` qua `Xss::filterAdmin()`, mà danh sách thẻ của nó không có hai thẻ này — chúng biến mất không báo gì. `data-*` thì sống sót. Kiểm bằng `ddev drush php:eval` với `Xss::filterAdmin()`.
→ Checkbox "Đã xử lý" phải do JS chèn. Cũng đúng hơn về progressive enhancement: checkbox không có JS thì bấm cũng chẳng làm gì. Đã có test khoá lại việc PHP **không** được render `<input>`.

**2. Băng sticky nằm sau lưng admin toolbar.** `top: 0` là đúng theo CSS nhưng sai theo thực tế: toolbar che mất. Dùng `var(--drupal-displace-offset-top)` và nghe `drupalViewportOffsetChange`.

**3. Hộp lỗi chèn qua `#suffix` KHÔNG nằm trong wrapper của field.** Dùng `closest('.js-form-wrapper')` để đoán field cha thì nó leo lên container chứa **mọi** field, và viền lan sang cả Tags lẫn Meta description — hai field không có lỗi nào. Đây là lỗi **nói sai sự thật**, không phải lỗi thẩm mỹ.
→ PHP truyền `VF_AI_REVIEW_FIELD_MAP` sang JS; JS nhắm đúng ô bằng thuộc tính `name`.

**4. `querySelector('[name^="body["]')` trả về textarea SUMMARY, không phải body.** Thứ tự DOM thật là `body[0][summary]` → `body[0][value]` → `body[0][format]`, nên tiền tố khớp cái đầu tiên. Khung CKEditor vì vậy không bao giờ được tô viền.
→ Nhắm `[name="X[0][value]"]` trước, dự phòng `[name^="X["]` cho `url_alias` (`path[0][alias]`). Khung CKEditor lấy bằng `sourceElement.nextElementSibling`, đúng quan hệ mà `core/modules/ckeditor5/js/ckeditor5.js:637` dùng.

**Bài học chung:** với ba bẫy sau, chẩn đoán đầu tiên đều **hợp lý nhưng sai**. Chỉ khi đi đọc source của core và dump thứ tự DOM thật mới ra đúng nguyên nhân. Không nhìn được DOM thì phải lấy bằng chứng, đừng suy luận tiếp.

### 10.7. Cố ý KHÔNG hiện nhãn `publish` / `needs_revision`

`AiReportRenderer::trangThai()` **không đọc `report['decision']`** (grep ra 0 lần),
và cả bốn field AI đều ẩn khỏi form soạn bài. Băng trạng thái suy ra từ **số lỗi**
và **veto**, không từ quyết định của hệ thống.

**Đây là chủ đích, không phải bỏ sót.**

Ranh giới `publish` / `needs_revision` do so `final_score` với ngưỡng 80, mà
`scoring.yaml` ghi `meta.calibrated: false`, và E5 đo được ngưỡng đó đề xuất
`publish` sai cho **9/33 bài** gold.

Bằng chứng gần nhất, đo trên hệ thống thật ngày 2026-08-22 (node 36): máy trả
`decision = publish` ở **81,625 điểm**, trong khi giao diện liệt kê ngay bên dưới
**20 vấn đề** — gồm lỗi ngữ pháp (CQ2), 7 câu quá dài (CQ3) và meta description
172 ký tự ngoài dải 140–170 (SEO3). In "Đề xuất: Đăng bài" lên đầu màn hình đó là
**tự mâu thuẫn với chính danh sách lỗi của mình**.

**Ngược lại, veto VẪN hiện** ("Bài bị từ chối — N lỗi nghiêm trọng ở Tuân thủ"),
vì nó tất định: CP1 tra danh sách cụm từ đóng, severity tra bảng theo mã tiêu chí
(`scoring.py`). Node 37 cùng ngày bị chặn đúng bằng đường này.

Nguyên tắc rút ra: **hiện phần tất định, giấu phần chưa hiệu chỉnh.**

**Điều kiện để bật lại nhãn:** `scoring.yaml` có `meta.calibrated: true`. Không
phải "thấy giao diện trống thì thêm vào cho đủ" — thiếu nhãn ở đây là kết luận
của phép đo, không phải việc còn dở.

Mục 4.5 có một dòng ghi ngược lại điều này ("Đề xuất: Có thể xuất bản"); dòng đó
đã được đánh dấu hết hiệu lực tại chỗ.

---

## 11. Nguồn tham khảo

- `hook_form_alter()` để can thiệp form Drupal, thêm/ẩn/đổi phần tử: [drupal.org - Altering forms](https://www.drupal.org/docs/develop/drupal-apis/form-api/introduction-to-form-api)
- Đặt phần tử vào cột `advanced` (sidebar) của form soạn node, và thảo luận về việc thay thế `hook_form_node_form_alter()` bằng field layout: [drupal.org issue #3344498](https://www.drupal.org/project/drupal/issues/3344498)
- Vì sao computed field không hiện ở chế độ sửa, và form alter là cách phù hợp hơn: [drupal.org - Live computations during node creation or edit](https://www.drupal.org/node/3075055)
- Đặt thuộc tính read-only cho phần tử form (và giới hạn của nó - chỉ là thuộc tính HTML): [drupal.org - Set a form field as read only](https://www.drupal.org/forum/support/module-development-and-code-questions/2017-02-03/set-a-form-field-as-read-only)

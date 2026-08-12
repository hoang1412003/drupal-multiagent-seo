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

## 10. Nguồn tham khảo

- `hook_form_alter()` để can thiệp form Drupal, thêm/ẩn/đổi phần tử: [drupal.org - Altering forms](https://www.drupal.org/docs/develop/drupal-apis/form-api/introduction-to-form-api)
- Đặt phần tử vào cột `advanced` (sidebar) của form soạn node, và thảo luận về việc thay thế `hook_form_node_form_alter()` bằng field layout: [drupal.org issue #3344498](https://www.drupal.org/project/drupal/issues/3344498)
- Vì sao computed field không hiện ở chế độ sửa, và form alter là cách phù hợp hơn: [drupal.org - Live computations during node creation or edit](https://www.drupal.org/node/3075055)
- Đặt thuộc tính read-only cho phần tử form (và giới hạn của nó - chỉ là thuộc tính HTML): [drupal.org - Set a form field as read only](https://www.drupal.org/forum/support/module-development-and-code-questions/2017-02-03/set-a-form-field-as-read-only)

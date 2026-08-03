# Thiết kế: Module Drupal `vf_ai_review` — báo cáo AI trong giao diện soạn bài

**Ngày:** 2026-08-03
**Trạng thái:** thiết kế đã duyệt — chưa triển khai
**Phạm vi:** hạng mục "Dựng UI báo cáo cơ bản" của Sprint 2 (`docs/roadmap.md`). Sau khi Brand Voice Agent xong (PR #24), đây là deliverable bắt buộc còn lại nặng nhất.

**Liên quan:** `docs/editor-ui-design.md` (thiết kế gốc, v1 2026-07-27) · `docs/prompt-injection.md` mục 5 biện pháp M4 · `docs/architecture.md` mục 2.3 và 6.4 · `docs/operations.md` mục 3

**Tài liệu này thay thế phần nào của `editor-ui-design.md`:** giữ nguyên mức triển khai P1, cấu trúc module, hai mức hiển thị và bảng ánh xạ field. **Thay** cơ chế phát hiện nội dung đã đổi ở mục 4.4 (xem mục 4.3 dưới đây — cơ chế cũ hỏng, có bằng chứng). **Bổ sung** trạng thái thứ tư (JSON hỏng), quyết định về `severity`, và cách kiểm thử.

---

## 1. Vì sao hạng mục này rủi ro nhất

Ba lý do, theo `editor-ui-design.md` mục 1:

1. **Là phần duy nhất cần PHP/Drupal.** Toàn bộ phần còn lại của dự án là Python — ngăn xếp khác, quy ước khác, vòng lặp sửa-thử khác.
2. **Chưa có gì.** `drupal/web/modules/custom/` chưa tồn tại (xác nhận 2026-08-03); chưa có dòng code Drupal nào ngoài `scripts/create_ai_fields.php`.
3. **Không thể "gần đúng".** Pipeline chấm sai vài phần trăm vẫn demo được; giao diện vỡ thì không.

Bổ sung một dữ kiện: **người thực hiện chưa từng viết module Drupal.** Kế hoạch triển khai phải chia nhỏ hơn bình thường, mỗi bước kèm lệnh kiểm tra cụ thể và giải thích khái niệm Drupal khi chúng xuất hiện lần đầu.

**Đề bài yêu cầu nguyên văn:** *"trả báo cáo lỗi/rủi ro theo từng field **ngay trong giao diện editor**"*. Đây là deliverable bắt buộc, không phải nice-to-have, và là thứ hội đồng nhìn thấy đầu tiên khi demo.

---

## 2. Ba quyết định đã chốt

| # | Quyết định | Lý do |
|---|---|---|
| **Q1** | Thêm field `field_ai_report_json`, Python ghi dữ liệu có cấu trúc; PHP chỉ đọc. **Không** để PHP tách chuỗi `field_ai_suggestions` | Tách chuỗi tạo coupling ngầm qua định dạng text — đổi một ký tự bên Python là vỡ giao diện bên PHP mà không test nào bắt được. Ngoài ra Brand Voice giờ trả `criteria` (7 tiêu chí kèm mức và đoạn trích), nhét vào chuỗi text thì thành mớ hỗn độn |
| **Q2** | Phạm vi chỉ gồm **(a)** khối tổng quan và **(b)** chú thích per-field. Bỏ ô phản hồi người duyệt và nút "chấm lại ngay" | Ô phản hồi **chưa dùng được**: `operations.md` mục 3.4 quy định nó khớp với bản ghi truy vết qua `(node_id, scored_at)`, mà nhật ký truy vết chưa làm — làm bây giờ là làm một nửa cơ chế. Nút "chấm lại" cần polling worker tồn tại trước để có cái mà bỏ qua |
| **Q3** | `AiReportRenderer` **không phụ thuộc Drupal**, escape bằng `htmlspecialchars()` thay vì `Html::escape()` | Cho phép test bằng script PHP thuần, giữ đúng phong cách 18 bộ test Python hiện có, không phải cài PHPUnit (không có sẵn trong `vendor/bin`). Hai hàm tương đương: `Html::escape()` bên trong chính là `htmlspecialchars($text, ENT_QUOTES \| ENT_SUBSTITUTE, 'UTF-8')` |

---

## 3. Kiến trúc

### 3.1. Luồng dữ liệu

```
PHÍA PYTHON (đã có, sửa nhẹ)              PHÍA DRUPAL (mới hoàn toàn)
────────────────────────────              ──────────────────────────
graph.py write_back_node
   │ dựng 2 thứ song song:
   ├─ chuỗi text  ──> field_ai_suggestions ──> đọc được kể cả khi
   │    (KHÔNG đổi)                            module chưa bật
   └─ cấu trúc JSON ─> field_ai_report_json ──> module vf_ai_review
                                                      │
                                                      ├─ (a) khối tổng quan
                                                      │     ở cột advanced
                                                      └─ (b) chú thích dưới
                                                            từng field widget
```

### 3.2. Ba tính chất kiến trúc

**Module chỉ ĐỌC, không bao giờ ghi.** Không tính điểm, không gọi API, không sửa dữ liệu. Module hỏng thì cùng lắm không thấy báo cáo, **không thể làm sai dữ liệu đánh giá**. Phần rủi ro cao (chấm điểm) và phần rủi ro thấp (vẽ giao diện) tách hẳn nhau.

**Tách logic dựng báo cáo khỏi hook.** Hook chỉ lấy node, gọi lớp dựng, gắn kết quả vào form. Toàn bộ "JSON → render array" nằm trong `src/AiReportRenderer.php`. Hook cần cả form Drupal thật mới chạy được nên rất khó test; lớp thuần nhận mảng trả mảng thì test độc lập được.

**Giữ nguyên `field_ai_suggestions`.** Module tắt hay lỗi thì vẫn đọc được text thô — *suy giảm mềm* theo `editor-ui-design.md` mục 5.

### 3.3. Ranh giới với phần đã có

**Không đụng:** 4 agent, Aggregator, cơ chế veto, công thức điểm, `drupal_client.fetch_content()`, `state.py`.

**Sửa tối thiểu:** `create_ai_fields.php` (thêm field thứ 5), `drupal_client.write_back()` (thêm 1 tham số, PATCH thêm 1 field), `graph.py write_back_node` (dựng thêm dict JSON).

---

## 4. Phía Python

### 4.1. Field thứ 5

```php
create_field('field_ai_report_json', 'string_long', 'article', 'AI Report (JSON)');
```

Kiểu **`string_long`**, không phải `text_long`. Quan trọng: `text_long` chạy qua bộ lọc văn bản của Drupal, sẽ **bóp méo JSON** (đổi ký tự, tự chèn `<p>`). `string_long` lưu text thô nguyên vẹn.

Field này ẩn khỏi form, người dùng không bao giờ thấy JSON.

### 4.2. Cấu trúc JSON

```json
{
  "version": 1,
  "scored_at": "2026-08-03T09:45:17+00:00",
  "content_hash": "a3f8c1...",
  "decision": "needs_revision",
  "final_score": 76.5,
  "note": null,
  "veto_reason": null,
  "missing_agents": [],
  "fields": {
    "title": [
      {"agent": "SEO", "label": "Độ dài tiêu đề",
       "message": "Tiêu đề dài 62 ký tự, nên rút xuống 50-60",
       "excerpt": null, "severity": null}
    ],
    "body": [
      {"agent": "Compliance", "label": "Claim thời gian sạc thiếu điều kiện",
       "message": null,
       "excerpt": "Với sạc thường tại nhà, thời gian sạc đầy dao động...",
       "severity": "medium"}
    ]
  }
}
```

Ánh xạ từ output 4 agent sang một mục trong `fields`:

| Agent | `label` — loại lỗi, luôn có | `message` — gợi ý sửa | `excerpt` — trích nguyên văn | `severity` |
|---|---|---|---|---|
| Content Quality | `type` | `suggestion` | `null` | `null` |
| SEO | `type` | `suggestion` | `null` | `null` |
| Brand Voice | `type` | `suggestion` | `null` | `null` |
| Compliance | `rule` | **`null`** | `excerpt` | `severity` |

**Compliance có `message = null` là đúng, không phải thiếu sót:** output của nó là `{field, severity, rule, excerpt}` — không có trường gợi ý sửa. Đặt `message` bằng chính `rule` sẽ khiến giao diện in cùng một câu hai lần. Renderer luôn hiện `label`, chỉ hiện `message` và `excerpt` khi chúng khác `null`.

**Về `severity`: chỉ Compliance định nghĩa mức nghiêm trọng; ba agent còn lại trả `null` và hiển thị trung tính.** Cố ý **không bịa** severity cho chúng — `docs/rubrics.md` mục 6.1 đang chủ trương severity phải tra bảng tất định theo mã tiêu chí, tự chế một mức ở tầng hiển thị là đi ngược hướng đó. Khi rubric làm xong cho 3 agent kia thì khoá này đã có sẵn chỗ.

### 4.3. Phát hiện nội dung đã đổi — hash, không phải mốc thời gian

**Đính chính `editor-ui-design.md` mục 4.4.** Bản v1 đề xuất: lúc chấm lưu mốc `changed` của node, lúc render so với `changed` hiện tại. **Cơ chế đó hỏng** — chính lệnh PATCH của `write_back()` làm `changed` nhảy.

Bằng chứng đo trên Drupal local (2026-08-03):

```sql
SELECT nfd.nid, FROM_UNIXTIME(nfd.changed) FROM node_field_data nfd WHERE nfd.type='article';
```

```
nid | changed
  2 | 2026-08-03 09:45:17     <- đúng thời điểm chạy smoke test chấm lại
  3 | 2026-08-03 09:45:24
  4 | 2026-08-03 09:45:32
```

Hệ quả nếu giữ cơ chế cũ: hệ thống **luôn báo "nội dung đã thay đổi"** ngay sau khi chấm, vì chính nó vừa làm thay đổi. Cảnh báo báo sai mọi lúc thì người duyệt học cách phớt lờ — tệ hơn là không có cảnh báo.

**Thay bằng hash nội dung:**

```
Lúc chấm  : content_hash = sha256(title + "\n" + body + "\n" + summary + "\n" + meta_description)
Lúc render: PHP tính lại hash từ giá trị field hiện tại, so với hash đã lưu
            khác nhau -> hiện băng cảnh báo
```

Hash **chỉ đổi khi nội dung thật sự đổi**. Lệnh PATCH chỉ ghi vào các field AI, không đụng `title`/`body`/`summary`/`meta_description`, nên hash không nhúc nhích — đúng thứ cần đo.

Hai bên tính trên **cùng chuỗi thô đọc từ DB, không chuẩn hoá gì**, nên không có rủi ro lệch. Quy tắc ghép cố định như trên, có test hợp đồng ở mục 7.3.

**Giới hạn đã biết:** bỏ `url_alias` khỏi hash. Bên PHP nó không phải field thường mà phải tra bảng `path_alias` riêng — thêm phức tạp để bắt trường hợp hiếm (người viết đổi mỗi URL).

---

## 5. Phía Drupal

### 5.1. Năm file

```
drupal/web/modules/custom/vf_ai_review/
├── vf_ai_review.info.yml        khai báo module để Drupal nhận diện
├── vf_ai_review.module          hook - điểm móc vào form soạn bài
├── vf_ai_review.libraries.yml   khai báo file CSS
├── src/AiReportRenderer.php     JSON -> render array (PHP thuần, test được)
└── css/vf_ai_review.css         màu theo severity, bố cục khối
```

`vf_ai_review.info.yml`:

```yaml
name: 'VF AI Review'
type: module
description: 'Hiển thị kết quả đánh giá Multi-Agent AI trong giao diện soạn bài.'
core_version_requirement: ^10 || ^11
package: 'VF O2O'
```

Bật module: `ddev drush en vf_ai_review -y`. Tắt: `ddev drush pmu vf_ai_review -y`.

### 5.2. Hook

```php
function vf_ai_review_form_node_form_alter(array &$form, FormStateInterface $form_state, string $form_id): void
```

**Tên hàm chính là phần khai báo** — Drupal thấy hàm tên `<tên_module>_form_node_form_alter` thì tự gọi mỗi khi dựng form node, không cần đăng ký ở đâu. `&$form` nghĩa là sửa trực tiếp vào mảng gốc.

Hook làm đúng 4 việc:

```
1. Kiểm tra node có phải content type 'article'  -> không phải thì thoát
2. Ẩn 4 field AI (#access => FALSE)
3. Đọc field_ai_report_json, giải mã, tính lại content_hash
4. Gọi AiReportRenderer -> gắn kết quả vào form
```

### 5.3. Ẩn 4 field AI

```php
foreach (['field_ai_status', 'field_ai_score', 'field_ai_suggestions', 'field_ai_report_json'] as $f) {
  if (isset($form[$f])) {
    $form[$f]['#access'] = FALSE;
  }
}
```

Không dùng `'#attributes' => ['readonly' => 'readonly']` — đó chỉ là thuộc tính HTML, chặn ở trình duyệt chứ **không chặn ở server**. `#access => FALSE` khiến Drupal từ chối nhận dữ liệu cho field đó phía server.

### 5.4. Bảng ánh xạ field báo cáo sang widget

| Khoá trong JSON | Phần tử form |
|---|---|
| `title` | `$form['title']` |
| `body`, `summary` | `$form['body']` |
| `meta_description` | `$form['field_meta_description']` |
| `url_alias` | `$form['path']` |
| `image_alt` | `$form['field_image']` |

Bảng nằm **một chỗ duy nhất** trong `vf_ai_review.module`. Tên không tồn tại trên form thì **bỏ qua field đó**, không đổ lỗi (`editor-ui-design.md` mục 8) — sai một tên không được làm trắng trang form soạn bài.

Xác nhận 2026-08-03: content type Article có đủ `field_image`, `field_meta_description`, nên bảng này dùng được nguyên trạng.

Chèn chú thích bằng `#suffix`.

### 5.5. Chống XSS — bắt buộc

Đây là chỗ nguy hiểm nhất của module. `docs/prompt-injection.md` mục 5 (**M4**) đã cảnh báo trước.

Nội dung hiển thị gồm **trích dẫn nguyên văn từ bài viết** và **văn bản do LLM sinh**. Người viết chèn `<script>` vào bài → LLM trích lại vào `excerpt` → module render vào **trang admin của người duyệt**. XSS kinh điển, chỉ khác là payload đi vòng qua LLM.

**Mọi chuỗi động đều phải escape.** Với render array dùng `#plain_text`; với `#suffix` (vốn nhận HTML thô) phải escape thủ công:

```php
// ĐÚNG
htmlspecialchars($message, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')

// SAI - chạy thẳng thẻ người viết chèn vào
['#markup' => $message]
```

Có test riêng cho việc này (mục 8.1).

---

## 6. Hiển thị

### 6.1. Bốn trạng thái

| Trạng thái | Nhận biết | Hiển thị |
|---|---|---|
| **Chưa chấm** | `field_ai_report_json` trống | *"Chưa được đánh giá. Chuyển bài sang 'Cần duyệt' để hệ thống chấm."* |
| **Đã chấm** | JSON hợp lệ, `final_score` là số | Khối báo cáo đầy đủ |
| **Chấm chưa đầy đủ** | JSON hợp lệ, `final_score` là `null` | Khối báo cáo + cảnh báo nổi bật |
| **JSON hỏng** | Giải mã thất bại | *"Không đọc được báo cáo — xem trường AI Suggestions."* |

Trạng thái 3 tương ứng ca Compliance Agent lỗi (`architecture.md` mục 6.4): điểm để trống chứ không phải 0. UI **tuyệt đối không được** hiển thị ô trống đó thành "0 điểm" — đó chính là hiểu nhầm thiết kế đang cố tránh.

Trạng thái 4 là bổ sung so với `editor-ui-design.md` (chỉ có 3): nếu ai đó sửa tay field JSON hoặc phiên bản Python cũ ghi định dạng khác, module phải nói rõ thay vì đổ lỗi.

### 6.2. Khối tổng quan (a) — cột `advanced`

```
┌─ Đánh giá AI ─────────────────────┐
│ Đề xuất:   ⚠ Cần sửa              │
│ Điểm:      76.5 / 100             │
│ Chấm lúc:  03/08/2026 09:45       │
│                                    │
│ 5 vấn đề trên 3 trường:            │
│   • Tiêu đề (2)                    │
│   • Meta description (1)           │
│   • Nội dung (2)                   │
└────────────────────────────────────┘
```

Dạng `#type => 'details'`, đặt vào cột `advanced` — thanh bên phải chỗ đang chứa "Thông tin xuất bản", "Tác giả".

Khi bị phủ quyết, thêm khối đỏ ở đầu:

```
│ ⛔ BỊ TỪ CHỐI                      │
│ Vi phạm Compliance (critical),     │
│ độc lập với điểm tổng.             │
```

### 6.3. Chú thích per-field (b) — phần đáp ứng đúng chữ đề bài

```
Tiêu đề *
┌──────────────────────────────────────────────────────────┐
│ Hướng dẫn sạc pin ô tô điện VinFast đúng cách và an toàn │
└──────────────────────────────────────────────────────────┘
  ⚠ SEO — Tiêu đề dài 62 ký tự, nên rút xuống 50-60
  ⚠ Brand Voice — Viết "VF8", chuẩn là "VF 8" (7/7 bài chuẩn dùng cách này)

Nội dung *
┌──────────────────────────────────────────────────────────┐
│ ...                                                       │
└──────────────────────────────────────────────────────────┘
  ⛔ Compliance — Claim thời gian sạc thiếu điều kiện
     "Với sạc thường tại nhà, thời gian sạc đầy dao động..."
  ⚠ Chất lượng — Câu quá dài, nên chia thành hai câu
```

Mức (a) để người duyệt nắm nhanh; **mức (b) mới là chỗ người viết thật sự sửa**. Khi demo phải nói rõ (b) là phần đáp ứng yêu cầu *"báo cáo theo từng field ngay trong giao diện editor"*.

### 6.4. Băng cảnh báo nội dung đã đổi

Khi hash tính lại khác hash đã lưu:

```
⏱ Nội dung đã thay đổi sau lần chấm lúc 09:45.
   Kết quả bên dưới có thể không còn đúng.
```

Kèm làm mờ phần chi tiết.

### 6.5. Quy tắc câu chữ — ranh giới trách nhiệm

Hệ thống chỉ **đề xuất**; nút Xuất bản vẫn của người (`architecture.md` mục 2.3).

| Không dùng | Dùng |
|---|---|
| "Trạng thái: Đạt" | "**Đề xuất**: Có thể xuất bản" |
| "AI đã duyệt" | "**Đề xuất** của hệ thống đánh giá" |
| Nút "Xuất bản theo AI" | *(không có nút nào)* |

Nhãn tiếng Việt cho `decision`:

```
publish         -> ✅ Có thể xuất bản
needs_revision  -> ⚠ Cần sửa
rejected        -> ⛔ Bị từ chối
```

Đây không phải chuyện chữ nghĩa vụn vặt — nó là ranh giới trách nhiệm giữa hệ thống và người duyệt, và là điểm chắc chắn bị hỏi khi bảo vệ.

---

## 7. Xử lý lỗi

### 7.1. Bảng suy giảm

| Tình huống | Hành vi | Người dùng thấy |
|---|---|---|
| Module chưa bật | Không có gì chạy | 4 field AI hiện dạng widget thô — vẫn đọc được `field_ai_suggestions` |
| `field_ai_report_json` trống | Trạng thái "chưa chấm" | *"Chưa được đánh giá…"* |
| JSON giải mã lỗi | Bắt exception | *"Không đọc được báo cáo — xem trường AI Suggestions"* |
| JSON thiếu khoá | Đọc phòng thủ `??` | Hiện phần đọc được, bỏ phần thiếu |
| `version` khác 1 | Vẫn cố render | Thêm dòng *"Báo cáo sinh bởi phiên bản khác, hiển thị có thể thiếu"* |
| Tên field không khớp bảng ánh xạ | `isset()` rồi bỏ qua | Field đó không có chú thích, field khác bình thường |
| Node không phải `article` | Hook thoát ngay | Form giữ nguyên |

**Không ô nào dẫn tới trắng trang.** Form soạn bài là thứ đội content dùng hằng ngày; module phụ trợ làm hỏng nó là hậu quả nặng hơn nhiều so với không hiển thị được báo cáo.

### 7.2. Bẫy `null` so với `0` trong PHP

`final_score` phải phân biệt **`null` (chưa chấm được)** với **`0` (chấm được, điểm 0)**. Trong PHP `empty(0)` trả `TRUE`, nên dùng `empty()` ở đây sẽ hiển thị sai. **Bắt buộc dùng `=== NULL`.**

Đây đúng cái bẫy `architecture.md` mục 6.4 đã mô tả ở phía Python, nay lặp lại ở phía PHP với cú pháp khác.

### 7.3. Quyền xem

**Không thêm quyền mới.** Ai sửa được bài thì xem được báo cáo của bài đó — báo cáo là công cụ giúp người viết sửa bài, giấu nó khỏi chính người viết là vô nghĩa.

Ghi nhận: production có thể cần phân quyền (ví dụ chỉ trưởng nhóm xem được lý do phủ quyết), nhưng đó là quyết định vận hành.

### 7.4. Phương án lùi

| Mức | Nội dung | Công |
|---|---|---|
| **P1** *(đang làm)* | Module đầy đủ: khối tổng quan + chú thích per-field | ~150 dòng PHP + CSS |
| **P0** *(lùi về)* | Không code. Vào Quản lý hiển thị form của Article, kéo 4 field AI vào nhóm sidebar | 0 dòng |

**Thứ tự cắt nếu thiếu thời gian:** làm (a) trước vì dễ hơn hẳn, (b) sau. Buộc phải cắt thì cắt (b) — nhưng nêu rõ giới hạn khi demo thay vì giấu.

### 7.5. Thứ module này KHÔNG làm

- Không kích hoạt chấm điểm (chờ polling worker, `architecture.md` mục 9)
- Không hiện lịch sử các lần chấm (dữ liệu có trong `node_revision__*` nhưng ngoài phạm vi)
- Không có ô phản hồi người duyệt (chờ nhật ký truy vết, `operations.md` mục 3)
- Không đa ngôn ngữ giao diện — chuỗi hard-code tiếng Việt

---

## 8. Kiểm thử

### 8.1. `AiReportRenderer` — script PHP thuần

Dự án cố ý **không dùng framework test** (18 bộ test Python đều là script thuần). PHPUnit cũng không có sẵn trong `vendor/bin` (Drupal cài không kèm dev dependency). Cài thêm chỉ để test một lớp là thêm một hệ sinh thái vào dự án mà không phục vụ mục tiêu nào.

Vì `AiReportRenderer` không phụ thuộc Drupal (Q3), test được bằng script PHP thuần:

```
drupal/scripts/test_ai_report_renderer.php
   chạy: ddev exec php scripts/test_ai_report_renderer.php
```

| Ca kiểm | Kỳ vọng |
|---|---|
| Báo cáo đầy đủ | Khối tổng quan có đủ đề xuất, điểm, đếm vấn đề theo field |
| `final_score = null` | Hiện *"chưa đánh giá được"*, **không** hiện "0 điểm" |
| `final_score = 0` | Hiện **"0 / 100"** — khác hẳn ca trên |
| `veto_reason` có giá trị | Hiện khối đỏ ở đầu |
| **`excerpt` chứa `<script>alert(1)</script>`** | Chuỗi render ra **không còn thẻ `<script>`** |
| **`message` chứa `"` và `'`** | Bị escape, không phá thuộc tính HTML |
| JSON thiếu khoá `fields` | Không đổ lỗi, trả khối tổng quan rỗng phần chi tiết |
| `fields` có field lạ | Bỏ qua, không đổ lỗi |

Hai dòng in đậm là **cặp quan trọng nhất** — lỗ hổng XSS mà M4 cảnh báo, và là thứ dễ quên nhất khi vội. Cặp `null`/`0` là đối chứng bắt buộc, cùng loại với cặp `NA`/`0` đã dùng cho `scoring.py`.

### 8.2. Phía Python — `multiagent/scripts/test_report_json.py`

Không gọi LLM, không cần Drupal.

| Ca kiểm | Kỳ vọng |
|---|---|
| 4 agent trả kết quả bình thường | JSON có đủ `fields`, mỗi issue đúng field của nó |
| Compliance flag `critical` | `severity: "critical"`; các agent khác `severity: null` |
| Compliance lỗi (`None`) | `final_score: null`, `note` có nội dung |
| Cùng một `fields` đầu vào | `content_hash` luôn ra cùng giá trị |
| Đổi 1 ký tự trong `body` | `content_hash` đổi |
| `write_back()` | Gửi cả `field_ai_suggestions` lẫn `field_ai_report_json` |
| Chuỗi `field_ai_suggestions` | **không đổi một ký tự** so với hiện tại |

Dòng cuối chốt rằng phần suy giảm mềm còn nguyên và không phải kiểm chứng lại.

### 8.3. Test hợp đồng giữa hai ngôn ngữ

Chỗ dễ vỡ nhất: **Python và PHP phải tính ra cùng `content_hash`**. Lệch một quy tắc ghép chuỗi là băng cảnh báo hiện sai mãi mãi.

Một file dữ liệu mẫu dùng chung, hai bên cùng đọc:

```
multiagent/scripts/content_hash_fixture.json
{
  "fields": {"title": "...", "body": "...", "summary": "...", "meta_description": "..."},
  "expected_sha256": "3f2a..."
}
```

- `test_report_json.py` đọc file, tính hash, so với `expected_sha256`
- `test_ai_report_renderer.php` đọc **cùng file đó**, tính hash, so với **cùng giá trị**

Bên nào trôi lệch thì test bên đó đỏ. Không có test này thì lỗi chỉ lộ ra khi giao diện đã hiện sai.

### 8.4. Kiểm bằng mắt trên trình duyệt

Không tự động hoá được và cũng không nên cố.

```
1. ddev drush en vf_ai_review -y        -> in "Successfully enabled"
2. Mở http://drupal.ddev.site/node/1/edit
3. Cột phải có khối "Đánh giá AI", gập/mở được
4. Khối hiện: Đề xuất "Có thể xuất bản", Điểm 81.75
5. Dưới ô Tiêu đề có dòng chú thích màu, đúng nội dung SEO báo
6. KHÔNG thấy 4 field AI dạng ô nhập liệu ở cuối form
7. Mở node/5/edit (bài rejected) -> khối đỏ, có dòng lý do phủ quyết
8. Mở node/7/edit -> điểm 62.75, ít chú thích hơn vì bài ngắn
9. Sửa tiêu đề node/1 rồi lưu -> quay lại thấy băng "Nội dung đã thay đổi"
10. ddev drush pmu vf_ai_review -y      -> form về nguyên trạng, không lỗi
```

Bước 9 kiểm chứng cơ chế hash — dễ sai nhất nên phải thử thật. Bước 10 kiểm rằng tắt module không để lại hậu quả.

### 8.5. Không phá vỡ thứ đang chạy

| Kiểm tra | Vì sao |
|---|---|
| Chạy lại 18 bộ test Python | `write_back()` đổi chữ ký |
| `smoke_test_graph.py` trên node thật | Pipeline vẫn ghi ngược được cả 2 field |
| Mở form sửa bài khi **chưa bật** module | Xác nhận P0 vẫn đọc được `field_ai_suggestions` |

---

## 9. Ảnh hưởng lên code

| File | Thay đổi |
|---|---|
| `drupal/scripts/create_ai_fields.php` | Thêm `field_ai_report_json` kiểu `string_long` |
| `drupal/web/modules/custom/vf_ai_review/` *(mới)* | 5 file ở mục 5.1 |
| `drupal/scripts/test_ai_report_renderer.php` *(mới)* | Test lớp render + hash |
| `multiagent/src/drupal_client.py` | `write_back()` nhận thêm `report_json`, PATCH thêm 1 field |
| `multiagent/src/graph.py` | `write_back_node` dựng dict JSON + tính `content_hash` |
| `multiagent/scripts/test_report_json.py` *(mới)* | Test cấu trúc JSON + hash |
| `multiagent/scripts/content_hash_fixture.json` *(mới)* | Dữ liệu mẫu cho test hợp đồng |

**Không thay đổi:** kiến trúc 8 node, 4 agent, Aggregator, cơ chế veto, `state.py`, chuỗi `field_ai_suggestions`.

### 9.1. Đồng bộ tài liệu

| Tài liệu | Sửa gì |
|---|---|
| `README.md` | Tick "UI báo cáo trong editor" ở Sprint 2 |
| `docs/editor-ui-design.md` | Đánh dấu đã triển khai; **đính chính mục 4.4** (cơ chế `changed` hỏng, thay bằng hash) |
| `docs/architecture.md` mục 2.3 | Bổ sung field thứ 5 vào bảng field |
| `docs/prompt-injection.md` mục 5 | Đánh dấu M4 đã triển khai |

---

## 10. Thứ tự triển khai

Chia nhỏ hơn bình thường vì người thực hiện chưa từng viết module Drupal.

**Giai đoạn 1 — phía Python (quen thuộc, làm trước để có dữ liệu thật cho phía PHP)**

1. Thêm field thứ 5 + chạy `create_ai_fields.php`
2. `content_hash` + `test_report_json.py` phần hash
3. Dựng JSON trong `graph.py` + `write_back()` ghi 2 field + phần test còn lại
4. Chấm lại 1 bài thật → có JSON thật trong DB để phía PHP làm việc trên đó

**Giai đoạn 2 — phía Drupal**

5. Scaffold module (chỉ `.info.yml`) → `ddev drush en` chạy được, chưa làm gì
6. `AiReportRenderer` + test PHP thuần (chưa nối vào form)
7. Hook: ẩn 4 field AI → mở form thấy chúng biến mất
8. Gắn khối tổng quan (a) vào cột `advanced`
9. Gắn chú thích per-field (b)
10. CSS + băng cảnh báo hash
11. Kiểm bằng mắt theo checklist 8.4 + đồng bộ tài liệu

Bước 5 tách riêng có chủ đích: xác nhận Drupal nhận diện được module **trước khi** viết logic, để nếu sai cấu trúc thư mục thì phát hiện ngay thay vì lẫn với lỗi code.

---

## 11. Chưa chốt / cần đo

| Hạng mục | Ghi chú |
|---|---|
| Màu cụ thể theo severity | Chốt khi viết CSS; theo bảng màu Claro của Drupal để không lệch giao diện admin |
| Có cần `#cache` metadata không | Form node dựng lại mỗi request nên nhiều khả năng không cần; nếu thấy báo cáo không cập nhật thì thêm |
| Hiển thị `criteria` của Brand Voice | v1 chỉ hiện `issues` như 3 agent kia. Dữ liệu `criteria` (7 tiêu chí kèm mức) đã có trong pipeline nhưng chưa đưa vào JSON — cân nhắc sau khi thấy giao diện thật |
| Ngưỡng làm mờ khi nội dung đã đổi | v1 làm mờ toàn bộ phần chi tiết; có thể chỉ cần làm mờ phần liên quan field đã sửa |

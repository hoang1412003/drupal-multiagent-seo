# Thiết kế: Làm chắc script bóc tách gold set (hậu review)

**Ngày:** 2026-07-30
**Tiếp nối:** `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md` (đã triển khai xong, 12 commit trên `feature/goldset-html-extraction`)

## 1. Vì sao có tài liệu này

Sau khi triển khai xong script bóc tách, một lần review toàn branch phát hiện 6 hạng mục nằm ngoài phạm vi spec gốc. Không có hạng mục nào là lỗi của phần vừa xây; chúng thuộc 2 loại:

- **Lỗi có sẵn từ trước** trong `scripts/label_helper.py`, chỉ lộ ra khi có HTML thật chạy qua (D1, D5)
- **Thiếu phòng ngừa** cho 29 bài **chưa thu** — kết luận "không sao" hiện dựa trên đúng 1 bài (D2, D3, D4)

Chủ dự án quyết định làm cả 6 (2026-07-30), bao gồm cả 2 hạng mục tác giả spec đề nghị bỏ (D5, D6) vì giá trị thấp so với chi phí cập nhật lại số đo. Quyết định này được ghi lại nguyên văn ở đây thay vì tranh luận lại.

**Điều kiện tiên quyết đã hoàn thành:** mọi con số trong tài liệu này **đã đo thật** trên fixture `docs/goldset/raw_html/G-001.html` trước khi viết, không phải suy luận. Lý do: trong quá trình làm spec gốc, 4 con số bị ghi sai vì suy luận thay vì đo — trong đó một con số (`p=32`) còn **mã hoá một lỗi** thay vì mô tả hành vi đúng.

## 2. Sáu hạng mục

### D1 — `"st."` trong danh sách viết tắt khớp cả chữ "VinFast."

`label_helper.py` có `_ABBREVIATIONS = ("tp.", "tt.", "vd.", "vs.", "tr.", "st.", "q.", "p.")` để không cắt câu sau dấu chấm của từ viết tắt. `split_sentences()` kiểm bằng `before.endswith(a)`, nên chuỗi `"st."` khớp cả **"VinFast."**.

Đo thật:

```
Văn bản : "Đây là xe của VinFast. Xe này rất tốt. Giá hợp lý."
Kết quả : 2 câu (đúng ra 3) — "Đây là xe của VinFast. Xe này rất tốt." bị dán làm một
```

Hệ quả trên G-001: `số câu` báo 90, thực tế 98. Câu "dài nhất 64 từ" chỉ là 2-3 câu bị dán lại.

**Vì sao nghiêm trọng hơn một lỗi đếm thông thường:** toàn bộ gold set là bài về VinFast, nên chữ "VinFast." ở cuối câu xuất hiện dày đặc và lỗi lệch **cùng một hướng trên cả 33 bài** — thiên lệch có hệ thống, không phải nhiễu ngẫu nhiên. Câu bị dán lại thì dài hơn thực tế, làm `số câu > 30 từ` bị thổi lên, mà đó chính là số người gán nhãn dùng để quyết định mã **B9** (`annotation-guideline.md` mục 4.2: *"Câu trên 30 từ ... xuất hiện từ 3 lần trở lên"*). Sai ở đây đi thẳng vào ground truth.

**Sửa:** `"st."` là viết tắt tiếng Anh (Street/Saint), không xuất hiện trong văn bản cẩm nang tiếng Việt — bỏ khỏi danh sách. Giữ nguyên 7 mục còn lại.

**Cách kiểm chứng chặt hơn:** chỉ bỏ `"st."` thì vẫn còn cùng một lớp lỗi với mọi từ tiếng Việt kết thúc bằng `tr.`/`q.`/`p.`… ở cuối câu. Vì vậy điều kiện khớp phải đổi từ "chuỗi kết thúc bằng viết tắt" sang "**từ** cuối cùng đúng bằng viết tắt" — so khớp trên ranh giới từ, không phải hậu tố chuỗi. Cách này xử lý luôn cả họ lỗi thay vì bịt một ca.

### D2 — `KEEP_TAGS` thiếu `br`, `h1`, `h5`, `h6`

Thẻ ngoài `KEEP_TAGS` bị `unwrap()`. Với thẻ rỗng như `<br>`, unwrap **xoá hẳn** (không có nội dung để giữ lại) → hai dòng dính thành một → sai số câu và số đoạn. Với `<h5>`/`<h6>` thì mất cấu trúc heading.

Đo thật trên G-001: `br=0, h1=0, h5=0, h6=0` trong `div.field-body`. Nên D2 **không đổi bất kỳ con số kỳ vọng nào** trên fixture hiện tại — đây thuần là phòng ngừa cho 29 bài chưa thu.

**Sửa:** thêm `br`, `h1`, `h5`, `h6` vào `KEEP_TAGS`.

### D3 — không báo cáo thẻ bị unwrap

Spec gốc mục 4.2 đặt nguyên tắc "không xoá âm thầm" và cài nó cho 2 khối bị **decompose** (mục lục, banner CTA). Nhưng thẻ bị **unwrap** thì không báo gì. Nếu bài nào có `h5 x4` hoặc `br x12`, người dùng không có cách nào biết.

**Sửa:** in thêm một dòng liệt kê thẻ đã unwrap kèm số lượng, VD `[unwrap] div x5, figure x5, figcaption x5, span x1`. Dùng `collections.Counter`.

### D4 — không in `alt` của từng ảnh được giữ

Dòng `[giu] 5 anh, 16 link...` chỉ cho biết **số lượng**. Heuristic nhận diện banner CTA (thẻ `<a>` bọc đúng 1 `<img>`, không có chữ) vì vậy chỉ phát hiện được trường hợp **xoá oan** (qua dòng `[xoa]`), còn trường hợp ngược lại — banner **sống sót** vì không bọc `<a>`, hoặc bọc 2 ảnh — thì im lặng. Alt dạng slug (`dat-coc-xe-o-to-dien-vinfast`) sống sót sẽ tạo mã B6 giả, đúng thứ spec gốc mục 3.1 cảnh báo.

**Sửa:** in `alt` của từng ảnh được giữ, mỗi ảnh một dòng. Người dùng liếc 2 giây là phát hiện cả hai chiều.

### D5 — chú thích ảnh thành text node trần, không được tính là đoạn

`figcaption` không nằm trong `KEEP_TAGS` nên bị unwrap thành text node trần ở cấp cao nhất của body. Hệ quả: `label_helper.split_paragraphs()` chỉ tìm thẻ `<p>` nên **không tính** chú thích vào `số đoạn`; và khi tách câu, chú thích dính vào heading ngay sau nó.

Đo thật trên G-001: đúng **5** text node trần, và cả 5 **chính là 5 chú thích ảnh**:

```
[1] Những kinh nghiệm chạy đường trường giúp lái xe chủ động trong mọi hành trình
[2] Xe điện VinFast được tích hợp tính năng lên kế hoạch hành trình
[3] Việc tính toán trước thời gian di chuyển và tìm kiếm trạm sạc trước mỗi chuyến đi...
[4] Phanh tái tạo năng lượng giúp xe điện sử dụng năng lượng hiệu quả, tiết kiệm...
[5] Ô tô điện VinFast VF e34 tự tin chinh phục Sa Vĩ
```

Chú thích ảnh là chữ tác giả viết, thuộc phần nội dung được đánh giá.

**Sửa:** trong `_render_body()`, bọc mỗi child dạng `NavigableString` (có chữ) vào `<p>...</p>`.

**Số đo đổi:** `p` từ **31** thành **36** (31 + 5). Các số khác không đổi. Con số 36 đã đo thật, không suy luận.

### D6 — `alt` còn khoảng trắng ở biên

`_clean_text()` chỉ chuẩn hoá chuỗi ở cấp ngoài, không chuẩn hoá bên trong giá trị thuộc tính. Alt gốc kết thúc bằng `&nbsp;` nên sau khi thay thành dấu cách thường thì còn khoảng trắng cuối.

Đo thật trên G-001: 2 trong 5 alt có khoảng trắng cuối (`'kinh nghiệm chạy ô tô điện VinFast đường dài '`, `'... cần chuẩn bị gì '`).

Không ảnh hưởng mã lỗi nào (B6 chỉ xét alt có/không rỗng), thuần thẩm mỹ cho người đọc file raw.

**Sửa:** `.strip()` giá trị `alt` khi lọc thuộc tính trong `clean_body()`.

## 3. Số đo kỳ vọng sau khi làm 6 hạng mục

| Đại lượng | Trước | Sau | Lý do |
| --- | --- | --- | --- |
| `h2` | 3 | 3 | không đổi |
| `h3` | 10 | 10 | không đổi |
| `p` | 31 | **36** | D5: 5 chú thích ảnh thành `<p>` |
| `img` | 5 | 5 | không đổi |
| `a` | 16 | 16 | không đổi |

Số câu do `label_helper` báo sẽ tăng (D1 sửa việc cắt câu) và số đoạn sẽ tăng 5 (D5). Hai số này **không** có ca test cố định giá trị — chúng chỉ được in ra làm số đo cho người gán nhãn, nên không có expected value cần cập nhật.

Phải cập nhật `p=31` → `p=36` ở 3 nơi: spec gốc (`2026-07-29-...-design.md`), plan gốc (`2026-07-29-goldset-html-extraction.md`), và ca test `check("body p", ...)`.

## 4. Ngoài phạm vi

Không đụng tới `src/` (hệ multi-agent chạy thật). Hạng mục "mở rộng SEO Agent chấm alt mọi ảnh trong body" vẫn giữ nguyên trạng thái đã ghi ở spec gốc mục 6: bắt buộc phải xong **trước khi hiệu chỉnh ngưỡng**, cần spec riêng.

## 5. Kiểm thử

Bổ sung ca test cho từng hạng mục đo được:

| # | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| 1 | `split_sentences("Đây là xe của VinFast. Xe này rất tốt. Giá hợp lý.")` | 3 câu |
| 2 | `split_sentences("Tôi ở TP.HCM. Trời hôm nay đẹp.")` | 2 câu (không hồi quy hành vi đúng) |
| 3 | `KEEP_TAGS` chứa `br`, `h1`, `h5`, `h6` | đúng |
| 4 | Body có `<br>` → thẻ còn trong output | đúng |
| 5 | `clean_body` báo cáo thẻ đã unwrap | danh sách không rỗng, có `figcaption` |
| 6 | `p` trong `kept` trên fixture | **36** |
| 7 | Output không còn text node trần ngoài thẻ | đúng |
| 8 | Mọi `alt` trong output không có khoảng trắng ở biên | đúng |
| 9 | Toàn bộ ca test cũ vẫn pass | 49 ca cũ không giảm |

Ca 2 quan trọng: nó chốt rằng việc sửa D1 không phá hành vi đúng vốn có (không cắt câu ở "TP.HCM").

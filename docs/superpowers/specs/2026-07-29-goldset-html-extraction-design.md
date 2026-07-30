# Thiết kế: Thu thập gold set bằng script bóc tách HTML (Sprint 2 — phần 3/5)

**Ngày:** 2026-07-29
**Phạm vi:** Sub-project thứ 3 trong 5 phần của Sprint 2 (theo `docs/roadmap.md` và thứ tự đã chốt ở `docs/superpowers/specs/2026-07-22-compliance-agent-design.md`): Compliance Agent (xong, PR #12) → Retry/backoff Drupal Client (xong, PR #13) → **Gold set collection (tài liệu này)** → UI báo cáo → Brand Voice Agent (RAG).

Tài liệu này chỉ giải quyết khâu **thu thập và chuẩn hoá dữ liệu thô** cho gold set. Việc gán nhãn tuân theo `docs/goldset/annotation-guideline.md`, không thuộc phạm vi tài liệu này.

## 1. Vấn đề

`docs/goldset/labels.csv` đã chốt 33 mẫu (20 `gold-real` + 13 `gold-pert`), nhưng `docs/goldset/raw/` chưa có nội dung — chưa gán nhãn được bài nào.

Cách thu thủ công ghi trong `docs/goldset/sources.md` ("mở từng URL, copy nội dung phần thân bài") có 3 lỗi nghiêm trọng, phát hiện khi khảo sát HTML thật:

**1.1. Copy text thuần làm hỏng ground truth.** `scripts/label_helper.py` đếm heading và internal link bằng regex trên HTML:

```python
h2 = len(re.findall(r"<h2[^>]*>", body, re.IGNORECASE))
...
if words > HEADING_REQUIRED_WORDS and h2 == 0:
    b9.append(f"bài {words} từ nhưng không có h2")
```

Copy bằng chuột từ trình duyệt cho ra text không có thẻ `<h2>` → `h2 = 0` với mọi bài → **mã B9 giả cho hầu hết bài dài** → nhãn bị đẩy sai thành `needs_revision`. Vì nhãn là ground truth của calibration Sprint 3 (`docs/architecture.md` mục 8.2), sai ở đây làm hỏng toàn bộ F1/Kappa phía sau.

**1.2. Ranh giới body không nhất quán giữa các bài.** Mỗi bài người thu tự quyết định copy từ đâu đến đâu. 33 bài thu trong nhiều phiên sẽ có 33 tiêu chuẩn khác nhau — cùng loại vấn đề mà `annotation-guideline.md` mục 2 đặt ra giới hạn 15 bài/phiên để phòng.

**1.3. Không sửa lại được.** Nếu sau khi thu xong mới phát hiện cắt sai (VD quên loại khối CTA), copy tay buộc phải làm lại từ đầu cả 33 bài.

**Ràng buộc:** vinfastauto.com chặn truy cập tự động — xác minh ngày 2026-07-29 bằng `curl` với User-Agent trình duyệt, nhận **HTTP 403**. Ghi chú trong `sources.md` là chính xác. Không tải được bằng `requests`.

## 2. Hướng giải quyết

Tách đôi: **người** lưu trang, **script** bóc tách.

1. Người mở từng URL trên trình duyệt, `Ctrl+S` → **"Webpage, HTML Only"** → lưu thành `docs/goldset/raw_html/<sample_id>.html`.
2. Script đọc các file HTML đó, bóc ra `docs/goldset/raw/<sample_id>.txt` theo format `label_helper.py` đọc được.

**Vì sao không dùng headless browser (Selenium/Playwright) để vượt WAF:** site đã chủ động chặn truy cập tự động; lách qua là đi ngược ý chủ sở hữu nguồn dữ liệu và không bảo vệ được khi bị chất vấn. Người dùng mở trang bằng trình duyệt là đúng cách site muốn được truy cập; script chỉ xử lý file đã lưu về máy — thuần xử lý dữ liệu cục bộ.

**Lợi ích so với copy tay:** thời gian giảm từ ~4-6 tiếng xuống ~20 phút thao tác; giữ nguyên `<h2>`/`<img alt>`/`<a href>`; ranh giới body do một quy tắc duy nhất quyết định; sửa quy tắc thì chạy lại 1 lệnh thay vì thu lại 33 bài.

## 3. Cấu trúc HTML nguồn (khảo sát thực tế trên `G-001.html`)

vinfastauto.com chạy Drupal, markup có wrapper field rõ ràng. Bốn mốc sau đều **xuất hiện đúng 1 lần** trong trang:

```
div.node-detail              (1 lần — bọc toàn bộ bài viết)
 ├── h1.field-title          (1 lần) → title
 ├── div.field-desc          (1 lần) → summary
 └── div.field-body          (1 lần) → body
```

Ngoài `div.node-detail`:
- `<meta name="description">` trong `<head>` (1 lần) → `meta_description`
- `<link rel="canonical">` → suy ra `url_alias`

**Bắt buộc bám vào `div.node-detail`, không bám vào `field--name-body`.** Class `field--name-body` xuất hiện **3 lần** trong trang: 1 lần là thân bài thật (offset 43076, nằm trong `div.field-body`), 2 lần còn lại thuộc `div#block-hamburgermenu` (offset 83741) và `div#block-customblockstyle` (offset 102634). Chọn nhầm sẽ bóc ra nội dung menu thay vì bài viết.

### 3.1. Rác nằm bên trong `div.field-body`

Hai khối nằm trong chính field body nhưng không phải chữ tác giả viết:

| Khối | Nhận diện | Vì sao phải loại |
| --- | --- | --- |
| Mục lục tự sinh | `div.widget-toc` | Chứa đúng **13** thẻ `<a>` (đo được) → `label_helper.py` đếm thành internal link, đẩy tiêu chí SEO10 lên 2 điểm oan; cộng thêm ~150 từ vào số từ bài |
| Banner CTA "ĐẶT CỌC NGAY" | `<img alt="dat-coc-xe-o-to-dien-vinfast">` bọc trong `<a href="https://reserve.vinfastauto.com/">` | Là khối template dùng chung, `annotation-guideline.md` mục 2 quy định "không thuộc quyền kiểm soát người viết"; alt dạng slug sẽ tạo mã B6 giả |

Số đo trên `div.field-body` của G-001 (bằng parser, không phải regex): `h2=3, h3=10, p=32, a=30, img=6`. Sau khi loại 2 khối trên: **`a = 16`, `img = 5`** — 5 ảnh nội dung, tất cả đều có `alt` không rỗng.

Cách ra số 16: `30 − 13` (link mục lục) `− 1` (chính thẻ `<a>` bọc banner CTA) `= 16`.

> **Cập nhật 2026-07-30:** số thẻ `<p>` sau làm sạch đổi từ 31 thành **36** — chú thích ảnh (`figcaption`) trước đây bị unwrap thành text node trần nên không được tính là đoạn; nay được bọc thành `<p>`. Xem `docs/superpowers/specs/2026-07-30-goldset-extraction-hardening-design.md` mục D5.

**Thẻ cha rỗng phải được dọn theo.** Banner CTA nằm trong `<p><a><img></a></p>`, nên xoá thẻ `<a>` để lại một `<p></p>` rỗng — và nó rơi đúng **dòng đầu tiên** của body, tức thứ đầu tiên người gán nhãn nhìn thấy ở cả 33 file. Vì vậy sau khi xoá CTA phải dọn luôn thẻ cha khi nó trở nên rỗng. Số thẻ `<p>` sau làm sạch vì thế là **31**, không phải 32 (đo trên fixture: đúng 1 thẻ rỗng, không có thẻ rỗng nào khác).

### 3.2. Bẫy nếu quét ảnh trên toàn trang

Trang có 71 thẻ `<img>`, trong đó chỉ 5 ảnh thuộc nội dung bài. Quét toàn trang sẽ vớ phải:

```
4 thumbnail "Tin tức liên quan" ở sidebar   → alt=""  (RỖNG)
1 banner quảng cáo Xanh SM
3 logo footer / logo Bộ Công Thương
```

Bốn ảnh alt rỗng ở sidebar sẽ tạo **mã B6 giả cho mọi bài**. Đây là lý do thứ hai bắt buộc phải scope theo `div.node-detail`.

### 3.3. Phát hiện: không có field ảnh đại diện riêng

Toàn bộ 5 ảnh nội dung của G-001 nằm **bên trong** `body`, đều có alt mô tả bằng tiếng Việt:

```
kinh nghiệm chạy ô tô điện VinFast đường dài
kinh nghiệm chạy ô tô điện VinFast đường dài cần chuẩn bị gì
Lưu ý khi chạy ô tô điện VinFast đường dài
kinh nghiệm lái ô tô điện VinFast đường dài sử dụng phanh tái sinh
kinh nghiệm chạy ô tô điện VinFast đường dài VF e34 chinh phục Sa Vĩ
```

Site thật **không** có field ảnh đại diện tách riêng như `field_image` của Drupal local. Mô hình "một `image_alt` duy nhất" trong `src/state.py` và `src/drupal_client.py::_extract_image_alt()` không khớp cấu trúc nội dung thật. Hệ quả xem mục 6.

## 4. Script `multiagent/scripts/extract_gold_sample.py`

**Đầu vào:** `docs/goldset/raw_html/<sample_id>.html`
**Đầu ra:** `docs/goldset/raw/<sample_id>.txt`

### 4.1. Bóc tách

| Trường | Nguồn |
| --- | --- |
| `title` | `div.node-detail h1.field-title`, lấy text |
| `meta_description` | `<meta name="description">`, thuộc tính `content` |
| `url_alias` | `<link rel="canonical">`, lấy phần path (bỏ scheme + host) |
| `summary` | `div.node-detail div.field-desc`, lấy text |
| body | `div.node-detail div.field-body`, lấy HTML sau khi làm sạch (mục 4.2) |

### 4.2. Làm sạch body

**Xoá khỏi cây DOM:**
- `div.widget-toc` (toàn bộ khối mục lục)
- Thẻ `<a>` bọc ảnh banner CTA — nhận diện: thẻ `<a>` mà toàn bộ nội dung chỉ là một `<img>`, không có text
- `<script>`, `<style>`, `<iframe>`, comment HTML

**Quy tắc CTA là heuristic — bắt buộc phải in ra thứ đã xoá.** Đã xác minh trên G-001: 5 ảnh nội dung đều **không** bọc trong `<a>`, chỉ banner CTA bọc (`<a href="https://reserve.vinfastauto.com/">`), nên quy tắc không xoá nhầm. Nhưng đây là kết luận từ **một** bài; bài khác có thể bọc ảnh nội dung trong `<a>` (lightbox) và sẽ bị xoá oan.

Vì vậy script **in ra mọi thứ nó xoá** cho từng file:

```
G-001.txt
  [xoa] div.widget-toc (13 link)
  [xoa] <a href="https://reserve.vinfastauto.com/"> boc <img alt="dat-coc-xe-o-to-dien-vinfast">
  [giu] 5 anh noi dung, 16 link, 3 h2, 10 h3
```

Người dùng liếc dòng `[xoa]` là phát hiện ngay nếu ảnh nội dung bị xoá nhầm. Xoá âm thầm là thứ nguy hiểm nhất ở bước này: mất nội dung mà không ai biết, và sai lệch chỉ lộ ra ở Sprint 3 khi đã quá muộn.

**Giữ lại thẻ:** `h2 h3 h4 p ul ol li img a strong em blockquote table tr td th`
Thẻ ngoài danh sách (`div`, `span`, `figure`...) được **unwrap** — bỏ thẻ, giữ nội dung bên trong.

**Giữ lại thuộc tính:** chỉ `alt` trên `<img>` và `href` trên `<a>`. Xoá toàn bộ `class`, `style`, `id`, `data-*`, `srcset`, `width`, `height`, `loading`, `src`.

Xoá `src` là có chủ đích: đường dẫn ảnh dài, không dùng cho tiêu chí nào, và làm file raw khó đọc khi gán nhãn thủ công. Giữ `alt` vì đó là thứ mã B6 / tiêu chí SEO9 cần.

Chuẩn hoá khoảng trắng: thay `&nbsp;` bằng dấu cách thường, gộp dòng trống liên tiếp.

### 4.3. Format đầu ra

```
title: Tổng hợp kinh nghiệm chạy ô tô điện VinFast đường dài
url_alias: /vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai
meta_description: Kinh nghiệm chạy ô tô điện VinFast đường dài: người dùng cần kiểm tra động cơ...
summary: Nhờ trang bị công nghệ pin tiên tiến, động cơ hiện đại, xe ô tô điện VinFast...
---
<p>Để đảm bảo an toàn cho những chuyến đi dài, người điều khiển xe ô tô điện cần...</p>
<img alt="kinh nghiệm chạy ô tô điện VinFast đường dài">
<h2>1. Lên kế hoạch hành trình di chuyển đường dài với ô tô điện VinFast</h2>
<p>Khâu chuẩn bị luôn đóng vai trò then chốt trong những chuyến đi...</p>
<h3>1.1. Xác định lộ trình di chuyển</h3>
...
```

**Thay đổi so với format cũ:**
- **Bỏ** dòng `image_alt:` — không còn ý nghĩa vì mọi ảnh nằm trong body (mục 3.3)
- **Thêm** dòng `summary:` — VinFast có field này thật (`field-descripton`), và `src/state.py` đã có `summary` trong 6 field; Content Quality Agent đọc nó

Quy ước 2 giá trị đặc biệt (`?` = chưa thu, để trống = đã kiểm tra và không có) trong docstring `label_helper.py` được **giữ nguyên** cho `meta_description`: nếu trang không có thẻ meta description, script ghi dòng trống (đã kiểm tra và không có), không ghi `?`.

### 4.4. Xử lý lỗi

| Tình huống | Xử lý |
| --- | --- |
| Không tìm thấy `div.node-detail` | In lỗi rõ ràng kèm tên file, **không** ghi file `.txt`, thoát với exit code khác 0. Nhiều khả năng lưu nhầm loại trang (trang danh mục thay vì bài viết) |
| Thiếu `h1.field-title` / `div.field-body` | Như trên — thiếu phần cốt lõi thì file raw vô dụng, ghi ra sẽ nguy hiểm hơn là báo lỗi |
| Không có `<meta name="description">` | Ghi dòng `meta_description:` trống (hợp lệ — đây chính là mã lỗi B3) |
| Không có `<link rel="canonical">` | Ghi `url_alias:` trống và in cảnh báo |
| Canonical không khớp `source_url` trong `labels.csv` | In cảnh báo nêu rõ cả 2 đường dẫn — dấu hiệu lưu nhầm bài. Vẫn ghi file để người dùng tự quyết |
| File `.txt` đã tồn tại | Ghi đè. An toàn vì nhãn lưu ở `labels.csv`, không lưu trong file `.txt` |

Cảnh báo (không phải lỗi) không làm dừng vòng lặp — chạy hết mọi file rồi in tổng kết.

### 4.5. Cách chạy

```
.venv\Scripts\python.exe scripts\extract_gold_sample.py ..\docs\goldset\raw_html\G-001.html
.venv\Scripts\python.exe scripts\extract_gold_sample.py ..\docs\goldset\raw_html\*.html
```

Khớp cách gọi của `label_helper.py` (nhận đường dẫn hoặc glob), để hai script dùng giống nhau.

## 5. Sửa `scripts/label_helper.py`

Mã **B6** hiện suy từ trường `image_alt` riêng:

```python
alt = check("image_alt", fields.get("image_alt"))
if alt is not None:
    if not alt:
        codes.append("B6 (thiếu alt text)")
```

Đổi thành: quét mọi thẻ `<img>` trong body, đếm số ảnh thiếu `alt` hoặc `alt` rỗng.

- Không có ảnh nào trong body → không kết luận B6 (bài không có ảnh không phải lỗi alt), in số đo `số ảnh 0`
- Có ảnh, tất cả đều có alt không rỗng → không có B6 từ máy; vẫn in nhắc "phần *mô tả đúng ảnh không* CẦN NGƯỜI xét" (giữ nguyên tinh thần hiện tại: máy chỉ kết luận phần đếm được)
- Có ít nhất 1 ảnh thiếu alt/alt rỗng → `B6 (n/m ảnh thiếu alt text)`

Phần `HUMAN_ONLY` và các mã còn lại giữ nguyên.

## 6. Ngoài phạm vi tài liệu này (nhưng phát sinh từ nó)

**SEO Agent chấm alt của mọi ảnh trong body.** Sau thay đổi ở mục 5, nhãn B6 xét **mọi ảnh trong body**, trong khi `src/agents/seo.py` vẫn chấm tiêu chí SEO9 trên **một** field `image_alt` do `drupal_client._extract_image_alt()` đọc từ `field_image` — hai bên đo hai tập ảnh khác nhau.

Hệ quả: việc mở rộng SEO Agent chuyển từ *tuỳ chọn* thành **bắt buộc phải xong trước calibration Sprint 3** (`docs/architecture.md` mục 8.2). Không sửa thì Recall/F1 của tiêu chí alt lệch có hệ thống, và con số báo cáo cuối kỳ không diễn giải được.

Việc này **không chặn** khâu thu thập: file HTML đã lưu giữ đủ alt của mọi ảnh, nên khi triển khai không phải thu lại dữ liệu. Ghi nhận thành một sub-project riêng, cần cập nhật `docs/rubrics.md` (tiêu chí SEO9) và `docs/architecture.md` mục 5.2 khi làm.

**Không sửa trong phạm vi này:** `src/state.py`, `src/drupal_client.py`, `src/agents/seo.py`, `docs/rubrics.md`. Tài liệu này chỉ đụng tới khâu chuẩn bị dữ liệu gold set.

## 7. Phụ thuộc

Thêm `multiagent/requirements-dev.txt`:

```
beautifulsoup4>=4.12.0
```

Đặt riêng, **không** thêm vào `requirements.txt`, vì đây là thư viện chỉ dùng cho script chuẩn bị dữ liệu chạy một lần — hệ multi-agent chạy thật không phụ thuộc nó. Giữ `requirements.txt` đúng nghĩa "những gì cần để chạy hệ thống".

Cắt cây DOM lồng nhau bằng regex là hướng đã cân nhắc và loại: `div.field-body` chứa `div` lồng nhiều tầng, regex không khớp được thẻ đóng tương ứng một cách tin cậy, rủi ro bóc thiếu/thừa nội dung cao hơn nhiều so với lợi ích tiết kiệm một dependency.

## 8. Kiểm thử

Tiêu chí thành công đo được, chạy trên `G-001.html` (dữ liệu thật đã lưu):

| # | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| 1 | `title` | `Tổng hợp kinh nghiệm chạy ô tô điện VinFast đường dài` |
| 2 | `url_alias` | `/vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai` |
| 3 | `meta_description` | Không rỗng, bắt đầu bằng `Kinh nghiệm chạy ô tô điện VinFast đường dài:` |
| 4 | `summary` | Không rỗng, bắt đầu bằng `Nhờ trang bị công nghệ pin tiên tiến` |
| 5 | Số thẻ `<h2>` trong body | **3** |
| 6 | Số thẻ `<h3>` trong body | 10 |
| 7 | Số thẻ `<img>` trong body | 5 (banner CTA đã bị loại khỏi 6 ảnh gốc) |
| 8 | Mọi `<img>` trong body có `alt` không rỗng | Đúng |
| 9 | Số thẻ `<a>` trong body | 16 (30 gốc − 13 link mục lục − 1 thẻ bọc banner CTA) |
| 10 | Chuỗi `widget-toc` trong output | Không xuất hiện |
| 11 | Chuỗi `dat-coc-xe-o-to-dien-vinfast` trong output | Không xuất hiện |
| 12 | Chuỗi `class=` trong output | Không xuất hiện |
| 13 | Chạy `label_helper.py` trên output | Không có mã `B9` phần "không có h2"; không có `B6` |

Kiểm tra 5-9 và 10-11 là phần chứng minh đã sửa đúng 3 lỗi nêu ở mục 1 và 3.1-3.2. Kiểm tra 13 xác nhận mục tiêu cuối: ground truth không còn mã giả.

**Lưu ý về con số ở kiểm tra 5:** toàn trang có 4 thẻ `<h2>` nhưng **chỉ 3 thẻ nằm trong bài viết** — thẻ thứ 4 thuộc khối ngoài `div.node-detail`. Đây là bằng chứng cụ thể cho việc bắt buộc scope theo `div.node-detail` (mục 3): nếu đếm toàn trang thì cả số heading lẫn số ảnh đều sai.

Viết thành `scripts/test_extract_gold_sample.py`, cùng dạng script kiểm thử thủ công như `test_compliance_rules.py` / `test_aggregator_veto.py` hiện có (dự án chưa dùng pytest — giữ nguyên quy ước sẵn có, không đổi trong phạm vi này).

`G-001.html` được commit vào repo làm fixture để test chạy lại được; các file HTML còn lại không commit (dung lượng lớn, không cần cho test).

> **Đảo quyết định 2026-07-30 — commit TOÀN BỘ 33 file HTML.** Câu trên viết khi mới có 1 file, cân nhắc duy nhất là dung lượng repo. Sau khi thu đủ 33 bài, lý do quan trọng hơn xuất hiện: **các file này không tái tạo được**. Site chặn truy cập tự động (403) nên không tải lại bằng script được, và nội dung trang thay đổi theo thời gian — ngay trong phiên thu thập, URL của `P-005a` (`/vn_vi/huong-dan-dich-vu-sac-o-to-dien-vinfast`) đã trả 404 và phải thay bằng bài khác. Mất file HTML gốc nghĩa là gold set không dựng lại được và mọi số liệu F1/Kappa ở Sprint 3 mất khả năng kiểm chứng độc lập. Dung lượng thật đo được: 4.1 MB cho cả 33 file — không đáng kể. Đây là đánh đổi giữa 4 MB và khả năng tái lập của deliverable quan trọng nhất dự án.

## 9. Việc người dùng phải làm

`labels.csv` có 33 dòng nhưng chỉ **30 URL duy nhất** — 3 URL sinh 2 biến thể perturbation:

```
P-001a, P-001b  <- /vn_vi/cham-soc-xe-dien-vao-thoi-tiet-hanh-kho
P-004a, P-004b  <- /vn_vi/xe-dien-sac-bao-lau-thi-day
P-007a, P-007b  <- /vn_vi/o-to-dien-va-o-to-xang-co-gi-khac-nhau
```

Vì vậy chỉ cần lưu **30 file HTML**, trong đó `G-001.html` đã có → còn **29 file**.

**Quy ước đặt tên file HTML:**
- 20 bài `gold-real`: đặt đúng `sample_id` — `G-001.html` … `G-020.html`
- 10 bài nguồn perturbation: đặt tên **không có hậu tố chữ cái** — `P-001.html` … `P-010.html`

Script sinh ra `P-001.txt` từ `P-001.html`. Người dùng nhân bản file đó thành `P-001a.txt` / `P-001b.txt` rồi chèn lỗi khác nhau vào từng bản theo `injected_codes`. Cách này giữ đúng nguyên tắc `annotation-guideline.md` mục 10.3 ("mỗi bản chèn 1-2 lỗi, không sửa gì khác") vì cả hai bản xuất phát từ một bản gốc giống hệt nhau.

**Trình tự:**
1. Lưu 29 file HTML còn lại (`Ctrl+S` → "Webpage, HTML Only" → `docs/goldset/raw_html/`).
2. Chạy script bóc tách toàn bộ, đọc phần cảnh báo script in ra.
3. Nhân bản 3 file `P-001/P-004/P-007` thành các biến thể `a`/`b`.
4. Chèn lỗi cho 13 bản `P-xxx` theo `injected_codes` đã ghi sẵn trong `labels.csv`.
5. Gán nhãn theo `annotation-guideline.md` (tối đa 15 bài/phiên, xáo trộn thứ tự, mù với kết quả AI).

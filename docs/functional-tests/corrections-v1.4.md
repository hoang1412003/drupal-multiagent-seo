# Nhật ký hiệu đính gold-corrected v1.4 — GC-001 đến GC-005

**Ngày hiệu đính/kiểm nguồn:** 2026-08-17
**Người tạo và kiểm:** AI-A1
**Model sinh dữ liệu:** `gpt-5.6-sol`
**Guideline:** v1.4
**Provenance:** AI-corrected, đã tiếp xúc một phần với nhãn/candidate cũ; không phải nhãn publish tự nhiên độc lập.

Năm bản này giữ đúng parent `G-001..G-005`, đủ năm field evaluator đọc (`title`, `url_alias`, `meta_description`, `summary`, `body`) và giữ nguyên chủ đề/ý định tìm kiếm. Parent trong `docs/goldset/raw/` không bị sửa.

## Nguồn chính thức đã kiểm

Tất cả URL dưới đây được truy cập ngày **2026-08-17**:

- Phạm vi VF e34 285 km theo NEDC và sạc nhanh thêm khoảng 180 km sau khoảng 18 phút: https://vinfastauto.com/vn_vi/node/6477
- Phạm vi VF e34 318,6 km theo NEDC: https://vinfastauto.com/vn_vi/tong-quan-o-to-dien-vinfast-vf-e34
- Loại trụ và thời gian sạc VF e34 (AC 11 kW, DC 30/60/250 kW): https://vinfastauto.com/vn_vi/node/6999
- Lưu ý sử dụng/bảo quản pin: https://vinfastauto.com/vn_vi/tuoi-tho-pin-o-to-dien-va-nhung-dieu-can-luu-y-de-keo-dai-tuoi-tho-pin
- Ảnh hưởng và cách dùng sạc nhanh/siêu nhanh: https://vinfastauto.com/vn_vi/sac-nhanh-va-sac-sieu-nhanh-cua-o-to-dien

Hai con số 285 km và 318,6 km đều từng được VinFast công bố kèm chuẩn NEDC. Theo ghi chú A3 của guideline, trích một giá trị hãng đã công bố không phải A3; bản corrected vẫn ghi rõ nguồn, chuẩn đo và cảnh báo quãng đường thực tế có thể khác.

## GC-001 ← G-001

- **Nguồn chủ đề:** `/vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai`
- **Field:** `title`, `url_alias`, `summary` giữ nguyên; `meta_description` 220 → 143 ký tự; `body` giữ cấu trúc 3 H2/10 H3 và nội dung đường dài.
- **Mã đã xử lý:** B1;B3;B8. Các số khuyến nghị/giá dịch vụ dễ trôi được bỏ hoặc viết không định lượng để phòng B10.

Trước → sau:

- B3: meta 220 ký tự → “Kinh nghiệm chạy ô tô điện VinFast đường dài: cách kiểm tra xe, lên kế hoạch hành trình, chọn điểm sạc và lái xe an toàn, tiết kiệm năng lượng.” (143 ký tự).
- B8: “Dựa trên việc các yếu tố” → “Dựa trên các yếu tố”; “đường thoáng,mức” → “đường thoáng, mức”; “chuyển đổi động, nhiệt năng” → “chuyển đổi động năng, nhiệt năng”; “do khi đi đường dài” → “khi đi đường dài”; “chủ xe mà không cần” và “cũng điều kiện” được sửa thành câu đủ chủ-vị.
- B8/B10 phòng ngừa: “1.00 km” cùng số lần sạc không có nguồn bị bỏ; “60km/h” và giá cứu hộ cũ bị thay bằng hướng dẫn tuân thủ giới hạn tốc độ/tra dịch vụ hiện hành.
- B1: “285km sau 1 lần sạc đầy” → “khoảng 285 km ... theo chuẩn NEDC; quãng đường thực tế thay đổi theo điều kiện vận hành”, kèm URL VinFast chính thức.

## GC-002 ← G-002

- **Nguồn chủ đề:** `/vn_vi/cach-cham-soc-xe-dien-vf-e34`
- **Field:** `title`, `url_alias`, `meta_description` giữ nguyên; `summary` giữ claim 318,6 km nhưng thêm “Theo thông số do VinFast công bố” và giữ NEDC; `body` giữ nguyên trình tự chăm sóc ngoại thất/radar/nội thất.
- **Mã đã xử lý:** B8.

Trước → sau (toàn bộ cụm B8 đã ghi trong candidate/test–retest và các lỗi cùng họ đọc thấy):

- “các loại bỏ đất đá” → “bụi, đất đá”.
- “đỗ xe và sử dụng nên dùng phanh tay” → “đã đỗ xe và sử dụng phanh tay”.
- “Được thiết kế động cơ điện...” → “Nhờ động cơ điện...”.
- “hư hỏng hóc” → “hư hỏng”; “hư hỏnghệ thống” → “hư hỏng, hệ thống”.
- “ô tô..” → “ô tô.”.
- “thấm dung dịch do khỏi phần dây đai” → “thấm hết dung dịch còn lại trên dây đai”.
- “khuyến cáokhách hàng” → “khuyến cáo khách hàng”.
- Sửa thêm các lỗi kết hợp từ/dấu câu nhỏ: “dính ở sơn” → “dính trên sơn”, “khăn mềm giặt qua nước ấm” → “khăn mềm thấm nước ấm”, bỏ lặp “loại bỏ”.
- Link `http://fastauto.com` sai tên miền → `https://vinfastauto.com`.

## GC-003 ← G-003

- **Nguồn chủ đề:** `/vn_vi/cach-khoi-dong-xe-may-dien-vinfast`
- **Field:** `title`, `url_alias`, `meta_description`, `summary` giữ nguyên; `body` giữ nguyên thứ tự thao tác khởi động/khóa/mở/vận hành.
- **Mã đã xử lý:** B8.

Trước → sau:

- “xuôi chiều kim đồng hồ” → “theo chiều kim đồng hồ”.
- “hết hành trinh” → “hết hành trình”.
- “khóa có xe” → “khóa cổ xe”.
- “Khóa cổ tự động chốt và.” → “Khóa cổ tự động chốt vào.”.
- “tay ga điền” → “tay ga điện”.
- “chủ xe dùng nên” → “chủ xe nên”; thêm dấu phẩy cho câu “không thể tự khắc phục được, người sử dụng...”.
- Sửa số mục `3.5` → `3.4`, chuẩn hóa Smartkey và câu vận hành; không đảo hoặc thêm/bớt bước thao tác.
- Đoạn IP67/0,5 m/30 phút và claim chống cháy chung cho mọi model được thay bằng yêu cầu đọc sách hướng dẫn đúng model, không vượt giới hạn nhà sản xuất; đây là chỉnh phòng ngừa A6/B10, không bịa giới hạn mới.
- “chở tối đa 1 người” được thay bằng yêu cầu tuân thủ số người pháp luật cho phép để tránh đóng băng quy định pháp lý trong bài corrected.

## GC-004 ← G-004

- **Nguồn chủ đề:** `/vn_vi/dinh-nghia-den-projector-la-gi`
- **Field:** `title`, `url_alias` giữ nguyên; `meta_description` 186 → 149 ký tự; `summary` viết gọn đúng chủ đề; `body` giữ 4 H2/2 H3 và cấu trúc giải thích đèn Projector.
- **Mã đã xử lý:** B3;B8;B10.

Trước → sau:

- B3: meta 186 ký tự → mô tả 149 ký tự.
- B8: “loại đèn nơi tập trung” → “loại đèn tập trung”; “màn trập kép lên” → “màn trập kéo lên”; “đđèn” → “đèn”; chuẩn hóa “full LED” và các câu thiếu tự nhiên.
- B10: bỏ các số không có nguồn “35W/20W/gấp 5 lần/100 lumen/W” và “tuổi thọ cao hơn 5 lần”; thay bằng mô tả định tính rằng hiệu suất/tuổi thọ phụ thuộc loại bóng và thiết kế.
- Các cụm tuyệt đối mơ hồ “tốt nhất”, “an toàn tối đa”, “tất cả bóng đèn”, “không bị mờ” được làm mềm; không đổi chủ đề sang loại đèn khác.
- Danh sách model có khả năng lỗi thời được thay bằng hướng dẫn kiểm thông số từng mẫu.

## GC-005 ← G-005

- **Nguồn chủ đề:** `/vn_vi/nhung-kien-thuc-co-ban-ve-sac-xe-o-to-dien-can-biet`
- **Field:** `title`, `url_alias`, `meta_description` giữ nguyên; `summary` sửa câu lặp; `body` giữ hai phần chính “kiến thức sạc” và “lưu ý khi sạc”, chuẩn hóa claim bằng nguồn VinFast.
- **Mã đã xử lý:** B1;B2;B8;B10.

Trước → sau:

- B8: “Việc sạc pin vai trò” → “đóng vai trò”; “là gì ?” → “là gì?”; “giao động” bị bỏ khi viết lại; “trại trạm” → “tại trạm”; “sạc thưởng” → “sạc thường”; tiêu đề “Dung lượng pin ... là bao lâu?” → “Tuổi thọ pin ... phụ thuộc vào yếu tố nào?”.
- B1: “285km sau 1 lần sạc” → “khoảng 285 km ... theo chuẩn NEDC” + caveat thực tế + nguồn chính thức.
- B2: “18 phút để hoàn tất quá trình sạc” → “trụ siêu nhanh DC 250 kW, khoảng 18 phút bổ sung khoảng 180 km; không phải thời gian sạc đầy” + caveat thực tế + nguồn chính thức.
- B2/B10: bỏ bảng Type 1/Type 2/CCS/Chademo lẫn tốc độ xe với tốc độ sạc; thay bằng dữ liệu FAQ chính thức cho AC 11 kW và DC 30/60/250 kW. Mọi thời gian có loại trụ; ba claim sạc dung lượng có dải 10–70%.
- B10: bỏ claim suy giảm “2,3%/năm”, “8–10 năm/80%” và “5.000 lần/10 năm/90%” không có nguồn trong parent. Phần thay thế chỉ giữ yếu tố ảnh hưởng có link VinFast.
- Khuyến nghị dung lượng và sạc nhanh được viết có điều kiện, dẫn hai nguồn VinFast nêu trên; không thêm số từ trí nhớ model.

## Kết quả helper và rà toàn bộ A/B

Lượt helper cuối cho cả 5 file:

| ID | Title | Meta | Alias | Ảnh thiếu alt | H2 | Kết luận máy | C advisory |
|---|---:|---:|---:|---:|---:|---|---|
| GC-001 | 53 | 143 | 51 | 0/5 | 3 | không có A/B máy kết luận | C4=26 |
| GC-002 | 61 | 149 | 35 | 0/7 | 3 | không có A/B máy kết luận | C4=19 |
| GC-003 | 53 | 149 | 41 | 0/10 | 4 | không có A/B máy kết luận | C4=23 |
| GC-004 | 60 | 149 | 37 | 0/4 | 4 | không có A/B máy kết luận | C4=8 |
| GC-005 | 51 | 143 | 58 | 0/3 | 2 | không có A/B máy kết luận | C4=8 |

Rà thủ công A1–A7/B1–B11:

- A1/A2: không bài nào có claim VinFast “nhất” trong phạm vi so sánh hoặc so trực tiếp với đối thủ. Các câu “cách tốt nhất” ở GC-003 là lời khuyên thao tác, không có phạm vi và không claim sản phẩm.
- A3: 285 km và 318,6 km đều có công bố VinFast, chuẩn NEDC; số trụ/thời gian GC-005 khớp FAQ chính thức. Không suy số.
- A4: các cụm ưu đãi chung ở GC-001/003/004 không tự nêu giá trị cụ thể; riêng `0%` ở GC-003 có link chương trình và thời hạn 25/06–31/08/2024.
- A5: H2 của từng bài trả lời đúng title; không bài nào lạc đề trên 50%.
- A6: các hướng dẫn thao tác giữ cảnh báo an toàn; GC-003/005 được viết lại để buộc theo sách hướng dẫn đúng model.
- A7: không có văn xuôi có nghĩa bị ẩn; các file chỉ chứa nội dung/HTML hiển thị của evaluator.
- B1/B2: chỉ GC-001/002/005 có claim phạm vi/sạc; tất cả đã có chuẩn đo, loại trụ/dải hoặc caveat thực tế thích hợp.
- B3/B4: meta 143–149; title 51–61, không all-caps và không gắn năm cũ.
- B5: tên model `VF e34`, `VF 8`, `VF 9` và cách xưng hô nhất quán theo từng bài.
- B6: mọi ảnh trong body đều có alt mô tả nội dung.
- B7: alias không dấu, dưới 75 ký tự và chứa từ khóa chính tương ứng title.
- B8: đã đọc toàn văn năm candidate sau sửa; không còn lỗi được liệt kê ở nhãn/evidence hoặc lỗi cùng họ tìm thấy.
- B9: cả năm bài trên 500 tiếng đều có H2.
- B10: claim kỹ thuật cần giữ có nguồn chính thức gần đoạn; claim không kiểm chứng bị bỏ.
- B11: không bài nào nêu claim cụ thể về chính sách pin/bảo hành/thuê pin cần đủ thành phần CP7.

## Disposition từng candidate của `quet_ung_vien.py`

- **GC-001 A3 — bác:** 285 km có link VinFast, NEDC và caveat thực tế. **A4 — bác:** “ưu đãi hấp dẫn” không có giá trị cụ thể.
- **GC-002 A3 — bác:** 318,6 km có attribution VinFast và NEDC; URL nguồn ghi ở đầu log.
- **GC-003 A1 — bác:** hai cụm “cách tốt nhất” là lời khuyên xử lý, thiếu phạm vi so sánh và không claim sản phẩm. **A3 — bác:** 2 phút là timeout Parking trong hướng dẫn vận hành, không phải thông số sai được chứng minh. **A4 — bác:** ưu đãi chung không có giá trị; chương trình 0% có link và thời hạn. **B10 — bác:** 0% có nguồn ngay trong cùng mục.
- **GC-004 A4 — bác:** chỉ mời xem “chương trình ưu đãi”, không nêu giá trị cụ thể.
- **GC-005 A1 — bác:** “trạng thái tốt nhất” không có phạm vi so sánh và không phải claim VinFast hơn đối thủ. **A3 — bác:** mọi số khớp nguồn chính thức. **B1 — bác:** 285 km có NEDC; 180 km là phạm vi bổ sung sau sạc có loại trụ, thời gian, nguồn và caveat thực tế. **B2 — bác:** mọi thời gian có loại trụ; claim dung lượng có dải 10–70%, claim 18 phút nói rõ không phải sạc đầy. **B10 — bác:** link chính thức nằm ngay câu/đoạn dẫn trước danh sách; mức dưới 80% có link trong cùng câu.

Scanner chỉ đánh dấu candidate, không tự quyết mã. Các disposition trên là quyết định manual theo guideline v1.4.

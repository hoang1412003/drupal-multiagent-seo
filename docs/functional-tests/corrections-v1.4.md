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
- Hướng dẫn sử dụng Vento S, gồm cảnh báo không điều khiển xe khi chân chống cạnh chưa gạt lên hoàn toàn: https://vinfastauto.com/vn_vi/huong-dan-su-dung-xe-may-dien-vinfast-vento-s
- Hướng dẫn vận hành Theon S, bước 2 yêu cầu gạt chân chống cạnh lên: https://vinfastauto.com/vn_vi/node/9434
- Sách hướng dẫn Vento S 2022 của VinFast, cảnh báo chân chống còn tiếp xúc mặt đất có thể làm người lái mất kiểm soát: https://static-cms-prod.vinfastauto.com/vento-s-2022.pdf
- Sách hướng dẫn Theon S 2022 của VinFast: https://static-cms-prod.vinfastauto.com/theon-s-2022.pdf

Hai con số 285 km và 318,6 km đều từng được VinFast công bố kèm chuẩn NEDC. Theo ghi chú A3 của guideline, trích một giá trị hãng đã công bố không phải A3; bản corrected vẫn ghi rõ nguồn, chuẩn đo và cảnh báo quãng đường thực tế có thể khác.

## GC-001 ← G-001

- **Nguồn chủ đề:** `/vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai`
- **Field:** `title`, `url_alias` giữ nguyên; `meta_description` 220 → 143 ký tự; `summary` và `body` được biên tập nhưng vẫn giữ cấu trúc 3 H2/10 H3 cùng nội dung đường dài.
- **Mã đã xử lý:** B1;B3;B8;B10.

Trước → sau:

- B3: meta 220 ký tự → “Kinh nghiệm chạy ô tô điện VinFast đường dài: cách kiểm tra xe, lên kế hoạch hành trình, chọn điểm sạc và lái xe an toàn, tiết kiệm năng lượng.” (143 ký tự).
- B8: “Dựa trên việc các yếu tố” → “Dựa trên các yếu tố”; “đường thoáng,mức” → “đường thoáng, mức”; “chuyển đổi động, nhiệt năng” → “chuyển đổi động năng, nhiệt năng”; “do khi đi đường dài” → “khi đi đường dài”; “chủ xe mà không cần” và “cũng điều kiện” được sửa thành câu đủ chủ-vị.
- B10: “1.00 km” cùng số lần sạc không có nguồn bị bỏ; “60km/h” và giá cứu hộ cũ bị thay bằng hướng dẫn tuân thủ giới hạn tốc độ/tra dịch vụ hiện hành. Đây là số liệu định lượng không nêu nguồn trong parent, nên B10 là mã thực tế đã loại, không phải chỉnh phòng ngừa.
- B1: “285km sau 1 lần sạc đầy” → “khoảng 285 km ... theo chuẩn NEDC; quãng đường thực tế thay đổi theo điều kiện vận hành”, kèm URL VinFast chính thức.

## GC-002 ← G-002

- **Nguồn chủ đề:** `/vn_vi/cach-cham-soc-xe-dien-vf-e34`
- **Field:** `title`, `url_alias`, `meta_description` giữ nguyên; `summary` giữ claim 318,6 km, thêm attribution VinFast, NEDC và caveat thực tế; `body` giữ nguyên trình tự chăm sóc ngoại thất/radar/nội thất.
- **Mã đã xử lý:** B1;B8;B10.

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
- B1: “318,6 km ... theo chuẩn NEDC” thiếu caveat → thêm “quãng đường thực tế thay đổi theo điều kiện vận hành”.
- B10: bỏ hai thông số “6 túi khí” và màn hình “10 inch” vì parent không nêu nguồn cho các số này và chúng không cần thiết cho hướng dẫn vệ sinh.

## GC-003 ← G-003

- **Nguồn chủ đề:** `/vn_vi/cach-khoi-dong-xe-may-dien-vinfast`
- **Field:** `title`, `url_alias` giữ nguyên; `meta_description`, `summary` và `body` được biên tập nhưng vẫn giữ nguyên thứ tự thao tác khởi động/khóa/mở/vận hành.
- **Mã đã xử lý:** A6;B8;B10.

Trước → sau:

- “xuôi chiều kim đồng hồ” → “theo chiều kim đồng hồ”.
- “hết hành trinh” → “hết hành trình”.
- “khóa có xe” → “khóa cổ xe”.
- “Khóa cổ tự động chốt và.” → “Khóa cổ tự động chốt vào.”.
- “tay ga điền” → “tay ga điện”.
- “chủ xe dùng nên” → “chủ xe nên”; thêm dấu phẩy cho câu “không thể tự khắc phục được, người sử dụng...”.
- Sửa số mục `3.5` → `3.4`, chuẩn hóa Smartkey và câu vận hành; không đảo hoặc thêm/bớt bước thao tác.
- A6: parent ghi mơ hồ “gạt chân chống cạnh” ngay trước khi tăng ga. Bản corrected ghi rõ “gạt chân chống cạnh lên” ở mọi quy trình và trước khi xe chạy. Hướng dẫn Vento S/Theon S cùng hai sách hướng dẫn chính thức nêu ở đầu log xác nhận thao tác này; manual Vento S cảnh báo chân chống chưa gạt lên hoàn toàn có thể chạm đất và làm người lái mất kiểm soát.
- A6/B10: bỏ đoạn khái quát IP67/0,5 m/30 phút và chống cháy cho mọi mẫu xe. Đây là hướng dẫn lội nước có thể gây mất an toàn khi áp sai model và chứa giới hạn định lượng không gắn đúng model/manual; A6 và B10 đều là mã thực tế đã loại.
- Hướng dẫn bật lại công tắc pin được giới hạn cho xe có trang bị và buộc thao tác theo sách hướng dẫn đúng mẫu xe; không thêm thao tác kỹ thuật từ trí nhớ model.
- “chở tối đa 1 người” được thay bằng yêu cầu tuân thủ số người pháp luật cho phép để tránh đóng băng quy định pháp lý trong bài corrected.

## GC-004 ← G-004

- **Nguồn chủ đề:** `/vn_vi/dinh-nghia-den-projector-la-gi`
- **Field:** `title`, `url_alias` giữ nguyên; `meta_description` 186 → 149 ký tự; `summary` viết gọn đúng chủ đề; `body` giữ 4 H2/2 H3 và cấu trúc giải thích đèn Projector.
- **Mã đã xử lý:** B3;B5;B8;B10.

Trước → sau:

- B3: meta 186 ký tự → mô tả 149 ký tự.
- B8: “loại đèn nơi tập trung” → câu định nghĩa đủ chủ-vị; “màn trập kép lên” → “màn trập nâng lên”; “đđèn” → “đèn”; chuẩn hóa “LED” và các câu thiếu tự nhiên.
- B10: bỏ các số không có nguồn “35W/20W/gấp 5 lần/100 lumen/W” và “tuổi thọ cao hơn 5 lần”; thay bằng mô tả định tính rằng hiệu suất/tuổi thọ phụ thuộc loại bóng và thiết kế.
- B5: chuẩn hóa cách xưng hô về “người dùng” xuyên bài, bỏ việc trộn “người sử dụng”/“bạn”/“người dùng”.
- Các cụm tuyệt đối mơ hồ “tốt nhất”, “an toàn tối đa”, “tất cả bóng đèn”, “không bị mờ” được làm mềm; không đổi chủ đề sang loại đèn khác.
- Danh sách model có khả năng lỗi thời được thay bằng hướng dẫn kiểm thông số từng mẫu.

## GC-005 ← G-005

- **Nguồn chủ đề:** `/vn_vi/nhung-kien-thuc-co-ban-ve-sac-xe-o-to-dien-can-biet`
- **Field:** `title`, `url_alias` giữ nguyên; `meta_description`, `summary` và `body` được biên tập nhưng vẫn giữ hai phần chính “kiến thức sạc” và “lưu ý khi sạc”, chuẩn hóa claim bằng nguồn VinFast.
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
| GC-001 | 53 | 143 | 51 | 0/5 | 3 | không có A/B máy kết luận | C4=12 |
| GC-002 | 61 | 149 | 35 | 0/7 | 3 | không có A/B máy kết luận | C4=10 |
| GC-003 | 53 | 150 | 41 | 0/10 | 4 | không có A/B máy kết luận | C4=9 |
| GC-004 | 60 | 149 | 37 | 0/4 | 4 | không có A/B máy kết luận | không có |
| GC-005 | 51 | 145 | 58 | 0/3 | 2 | không có A/B máy kết luận | C4=6 |

Rà thủ công A1–A7/B1–B11:

- A1/A2: không bài nào có claim VinFast “nhất” trong phạm vi so sánh hoặc so trực tiếp với đối thủ. Các câu “cách tốt nhất” ở GC-003 là lời khuyên thao tác, không có phạm vi và không claim sản phẩm.
- A3: 285 km và 318,6 km đều có công bố VinFast, chuẩn NEDC; số trụ/thời gian GC-005 khớp FAQ chính thức. Không suy số.
- A4: các cụm ưu đãi chung ở GC-001/003/004 không tự nêu giá trị cụ thể; riêng `0%` ở GC-003 có link chương trình và thời hạn 25/06–31/08/2024.
- A5: H2 của từng bài trả lời đúng title; không bài nào lạc đề trên 50%.
- A6: các hướng dẫn thao tác giữ cảnh báo an toàn; GC-003 ghi rõ gạt chân chống cạnh lên trước khi chạy theo nguồn VinFast đúng Vento S/Theon S, còn GC-005 buộc theo sách hướng dẫn đúng model.
- A7: không có văn xuôi có nghĩa bị ẩn; các file chỉ chứa nội dung/HTML hiển thị của evaluator.
- B1/B2: chỉ GC-001/002/005 có claim phạm vi/sạc; tất cả đã có chuẩn đo, loại trụ/dải hoặc caveat thực tế thích hợp.
- B3/B4: meta 143–150; title 51–61, không all-caps và không gắn năm cũ.
- B5: tên model `VF e34`, `VF 8`, `VF 9` đúng chuẩn; GC-004 đã thống nhất xưng hô “người dùng”, các bài còn lại giữ giọng ngôi ba theo vai trò người dùng/chủ xe/người lái.
- B6: mọi ảnh trong body đều có alt mô tả nội dung.
- B7: alias không dấu, dưới 75 ký tự và chứa từ khóa chính tương ứng title.
- B8: đã đọc toàn văn năm candidate sau sửa; không còn lỗi được liệt kê ở nhãn/evidence hoặc lỗi cùng họ tìm thấy.
- B9: cả năm bài trên 500 tiếng đều có H2.
- B10: claim kỹ thuật cần giữ có nguồn chính thức gần đoạn; claim không kiểm chứng bị bỏ.
- B11: không bài nào nêu claim cụ thể về chính sách pin/bảo hành/thuê pin cần đủ thành phần CP7.

## Disposition từng candidate của `quet_ung_vien.py`

- **GC-001 A3 — bác:** 285 km có link VinFast, NEDC và caveat thực tế. **A4 — bác:** “ưu đãi hiện hành” không nêu giá trị cụ thể.
- **GC-002 A3 — bác:** 318,6 km có attribution VinFast, NEDC và caveat thực tế; URL nguồn ghi ở đầu log.
- **GC-003 A3 — bác:** 2 phút là timeout Parking được nguồn vận hành VinFast xác nhận, không phải số sai. **A4 — bác:** ưu đãi chung không có giá trị; chương trình 0% có link và thời hạn. **B10 — bác đối với candidate hiện còn:** 0% có nguồn ngay trong cùng mục. A1 không còn candidate sau khi hai cụm “cách tốt nhất” được biên tập; chúng vốn là lời khuyên xử lý, không phải claim sản phẩm trong phạm vi so sánh.
- **GC-004 A4 — bác:** chỉ mời xem “chương trình ưu đãi”, không nêu giá trị cụ thể.
- **GC-005 A3 — bác:** mọi số khớp nguồn chính thức. **B1 — bác:** 285 km có NEDC; 180 km là phạm vi bổ sung sau sạc có loại trụ, thời gian, nguồn và caveat thực tế. **B2 — bác:** mọi thời gian có loại trụ; claim dung lượng có dải 10–70%, claim 18 phút nói rõ không phải sạc đầy. **B10 — bác:** link chính thức nằm ngay câu/đoạn dẫn trước danh sách; mức dưới 80% có link trong cùng câu. A1 không còn candidate sau khi cụm “trạng thái tốt nhất” được thay bằng hướng dẫn trung tính; cụm cũ vốn không nêu phạm vi so sánh và không phải claim VinFast hơn đối thủ.

Scanner chỉ đánh dấu candidate, không tự quyết mã. Các disposition trên là quyết định manual theo guideline v1.4.

# Nhật ký hiệu đính gold-corrected v1.4 — GC-006 đến GC-010

**Ngày hiệu đính/kiểm nguồn:** 2026-08-17
**Người tạo và kiểm:** AI-A1
**Model sinh dữ liệu:** `gpt-5.6-sol`
**Guideline:** v1.4
**Provenance:** AI-corrected, đã tiếp xúc một phần với nhãn/candidate cũ; không phải nhãn publish tự nhiên độc lập.

Năm bản này giữ đúng parent `G-006..G-010`, đủ năm field evaluator đọc (`title`, `url_alias`, `meta_description`, `summary`, `body`) và giữ nguyên chủ đề/ý định tìm kiếm. Parent trong `docs/goldset/raw/` và năm row/hash GC-001..GC-005 không bị sửa. Review round 1 xác nhận B5 là defect thực tế bổ sung trên cả năm parent; `removed_codes` đã được cập nhật tương ứng, còn các chỉnh sửa phòng ngừa vẫn không được khai là defect.

## Nguồn chính thức đã kiểm

Tất cả URL dưới đây được truy cập ngày **2026-08-17**:

- Thông số Evo200, gồm bộ sạc 400 W/1.000 W, dải 0–100%/20–100%, thời gian tương ứng và phạm vi 203 km trong điều kiện 30 km/h, một người 65 kg: https://vinfastauto.com/vn_vi/thong-so-ky-thuat-evo200
- Thông số Vento S để xác nhận mỗi mẫu có loại pin, dung lượng, bộ sạc và thời gian riêng; không lấy mốc “sạc đầy” thiếu SOC đầu làm claim thời gian trong bản corrected: https://vinfastauto.com/vn_vi/thong-so-ky-thuat-vento-s
- Trang tài liệu xe máy điện theo mẫu xe: https://vinfastauto.com/vn_vi/tai-lieu-xe-may-dien
- Trang tài liệu ô tô theo mẫu xe: https://vinfastauto.com/vn_vi/tai-lieu-o-to
- Thông tin sạc nhanh/siêu nhanh và các yếu tố ảnh hưởng: https://vinfastauto.com/vn_vi/sac-nhanh-va-sac-sieu-nhanh-cua-o-to-dien
- Thông tin bảo hành hiện hành và các sổ bảo hành theo loại xe/ngày giao/mục đích sử dụng: https://vinfastauto.com/vn_vi/thong-tin-bao-hanh
- Cổng hợp đồng và chính sách hiện hành: https://vinfastauto.com/vn_vi/hop-dong-va-chinh-sach
- Nguồn chủ đề về thời điểm sạc: https://vinfastauto.com/vn_vi/khi-nao-nen-sac-pin-xe-dien
- Nguồn chủ đề về các loại pin ô tô điện: https://vinfastauto.com/vn_vi/tim-hieu-cac-loai-pin-o-to-dien
- Quy trình sạc xe máy điện tại trạm, gồm sáu bước do VinFast công bố: https://vinfastauto.com/vn_vi/cach-sac-pin-xe-may-dien-vinfast

Các claim sạc/phạm vi định lượng chỉ được giữ ở GC-006 và ví dụ định tính có dẫn nguồn ở GC-007. GC-006 ghi đủ mẫu xe, công suất bộ sạc, SOC đầu–cuối, điều kiện phạm vi và caveat thực tế. Những bảng số cũ không thể xác minh trọn phạm vi bị bỏ thay vì suy số. Các trang bảo hành/chính sách chỉ được dùng như điểm tra cứu hiện hành; bản corrected không biến chúng thành cam kết thời hạn, giá hoặc đối tượng áp dụng cụ thể.

## GC-006 ← G-006

- **Nguồn chủ đề:** `/vn_vi/thoi-gian-sac-day-xe-may-dien-vinfast-bao-lau`
- **Field:** `title` và `url_alias` giữ nguyên; `meta_description` 140 ký tự; `summary` trả lời rằng thời gian phụ thuộc mẫu xe/bộ sạc/SOC; `body` giữ ý định tra thời gian sạc, rút bảng nhiều mẫu xuống một ví dụ Evo200 có thể kiểm nguồn đầy đủ.
- **Mã đã xử lý:** B1;B2;B5;B10.

Trước → sau:

- B1: bảng parent gắn nhiều phạm vi với “duy trì tốc độ 30 km/h” nhưng thiếu chuẩn/điều kiện/caveat theo từng mẫu → chỉ giữ Evo200 203 km ở 30 km/h, một người 65 kg, nêu đây không phải cam kết mọi hành trình và liệt kê yếu tố làm phạm vi thực tế thay đổi.
- B2: các mốc sạc parent thiếu loại bộ sạc → bảng corrected nêu Evo200 với bộ sạc 400 W hoặc 1.000 W và tách rõ 0–100% khỏi 20–100%.
- B5: parent trộn “người dùng”, “khách hàng” và “người sử dụng” → corrected dùng nhất quán “người dùng”.
- B10: bảng tổng hợp cũ chứa nhiều dung lượng, thời gian và phạm vi không có nguồn gần claim → bỏ toàn bộ số không xác minh; bốn mốc sạc và một mốc phạm vi còn lại đều khớp trang thông số Evo200 chính thức.
- Không dùng mốc “sạc đầy khoảng 6 giờ” của Vento S vì nguồn hiện tại không nêu SOC bắt đầu; việc không đưa claim thiếu ngữ cảnh này là lựa chọn an toàn, không phải một mã defect bổ sung.

## GC-007 ← G-007

- **Nguồn chủ đề:** `/vn_vi/cac-loai-pin-xe-may-dien-vinfast-dac-diem-gia-cach-su-dung`
- **Field:** `title` 60 ký tự, `url_alias` giữ nguyên; `meta_description` 145 ký tự; `summary` giữ ba nhóm pin; `body` giữ đủ ba ý đặc điểm, giá/chính sách và cách dùng nhưng chuyển nội dung biến động sang nguồn hiện hành.
- **Mã đã xử lý:** B1;B2;B5;B8;B10;B11.

Trước → sau:

- B1/B2: bảng Feliz/Klara A2 nêu phạm vi và thời gian nhưng thiếu bộ sạc, điều kiện thử và caveat → bỏ bảng; phần đọc thông số chỉ dùng Evo200 làm ví dụ, yêu cầu đủ điều kiện thử, công suất bộ sạc và dải SOC, kèm caveat phạm vi thực tế.
- B5: parent trộn “người dùng”, “khách hàng” và “Quý khách hàng” → corrected dùng nhất quán “người dùng”.
- B8: sửa lỗi “khống quá 1mm” bằng cách bỏ checklist nhận pin cũ cùng các câu vụng/lẫn ngôi; toàn bài dùng nhất quán “người dùng”, “mẫu xe”, “pin”.
- B10: bỏ các số không có nguồn như hơn 2.000 chu kỳ, 70%, mức hao hụt theo ngày/tháng, kích thước vết xước, hotline và bảng thông số/giá cũ. Không thay bằng số suy đoán.
- B11: bảng giá thuê pin parent có đối tượng/giá nhưng không nêu thời hạn hiệu lực → bỏ claim cụ thể; corrected chỉ hướng người dùng tới cổng chính sách, trang sản phẩm hoặc hợp đồng tại thời điểm giao dịch. Đoạn bảo hành cũng nói rõ điều kiện thay đổi theo mẫu xe, loại pin, ngày hóa đơn và mục đích sử dụng, không hứa một thời hạn chung.

## GC-008 ← G-008

- **Nguồn chủ đề:** `/vn_vi/khi-nao-nen-sac-pin-xe-dien`
- **Field:** `title` và `url_alias` giữ nguyên; `meta_description` 147 ký tự; `summary` trả lời trực tiếp thời điểm nên sạc; `body` giữ bốn phần về thời điểm, hình thức, lưu ý và lập kế hoạch sạc.
- **Mã đã xử lý:** B5;B8;B10.

Trước → sau:

- B8: “viêc”/“thông suất” và các câu rườm rà được viết lại; lượt QA đầu còn meta 139 ký tự, sau đó được mở rộng lên 147 trước khi đưa vào manifest. Đây không phải B3 của parent và không được ghi vào `removed_codes`.
- B5: parent trộn “người dùng” với “khách hàng” và viết sai tên `VF e 34` → corrected dùng nhất quán “người dùng” và không giữ dạng tên sai.
- B10: bỏ quy tắc phổ quát “10 giờ cho 3 lần sạc đầu”, bảng cấp sạc/số công suất và các mốc kỹ thuật không có nguồn gần claim; thay bằng hướng dẫn dựa trên cảnh báo xe, hành trình và tài liệu đúng mẫu, không đưa ngưỡng số mới.
- Phần chính sách thuê pin chi tiết trong parent có đối tượng và thời hạn (CP7=2) nên không phải B11; phần này bị bỏ vì không cần để trả lời “khi nào nên sạc”, không được khai là defect. Corrected chỉ dẫn cổng chính sách hiện hành mà không nêu giá trị cụ thể.

## GC-009 ← G-009

- **Nguồn chủ đề:** `/vn_vi/tim-hieu-cac-loai-pin-o-to-dien`
- **Field:** `title` 31 → 49 ký tự; `url_alias` giữ nguyên; `meta_description` 147 ký tự; `summary` và `body` giữ taxonomy pin, cách đọc thông số, sạc/tuổi thọ và chính sách theo mẫu xe.
- **Mã đã xử lý:** B1;B2;B4;B5;B8;B10;B11.

Trước → sau:

- B4: title “Các loại pin ô tô điện” dài 31 ký tự → “Tìm hiểu các loại pin ô tô điện phổ biến hiện nay” dài 49 ký tự, vẫn đúng chủ đề và không gắn năm cũ.
- B5: parent trộn “người dùng”, “khách hàng” và “Quý khách hàng”; review round 1 còn tìm thấy một “khách hàng” trong corrected → đổi thành “người dùng” và đọc lại toàn bài để thống nhất xưng hô.
- B8: “nên nên” cùng câu lặp/vụng được viết lại; “đúng model” được đổi thành “đúng mẫu xe”; các cụm “có nhiều hóa học”, “một số hóa học lithium-ion” và “thời gian của một mẫu xe hoặc một dải pin” được sửa thành “nhiều loại hóa học pin”, “một số loại pin lithium-ion” và “thời gian sạc ... trong một dải dung lượng pin”.
- B1/B2: bảng mẫu xe cũ chứa phạm vi VF 5 Plus thiếu chuẩn đo và mốc VF e34 18 phút thiếu dải SOC → bỏ bảng; phần thay thế giải thích mỗi claim phải có chuẩn/điều kiện và thiết bị/dải SOC, không lặp số.
- B10: bỏ các số mẫu xe, công suất, thời gian sạc và phạm vi không được xác minh thành một bộ đồng nhất; phần hóa học pin chỉ giữ mô tả định tính và dẫn bài tổng quan chính thức. Đoạn nêu yếu tố ảnh hưởng tốc độ sạc và cơ chế giảm công suất nay gắn trực tiếp nguồn VinFast về sạc nhanh/siêu nhanh ngay tại claim.
- B11: claim thay pin dưới 70% và bảo hành tới 10 năm không nêu thời hạn hiệu lực/phạm vi đầy đủ → bỏ. Corrected hướng đến sổ bảo hành và hợp đồng hiện hành, đồng thời nói rõ không có thời hạn chung cho mọi xe.

## GC-010 ← G-010

- **Nguồn chủ đề:** `/vn_vi/cach-sac-pin-xe-may-dien-vinfast`
- **Field:** `title` và `url_alias` giữ nguyên; `meta_description` 148 ký tự; `summary` cùng `body` thống nhất quy trình sáu bước, giữ ý định sạc tại trạm/tài khoản/thanh toán/an toàn.
- **Mã đã xử lý:** A1;B5;B8.

Trước → sau:

- A1: bỏ anchor “hệ thống trạm sạc hiện đại nhất Việt Nam”; không thay bằng claim hơn đối thủ hoặc tuyệt đối khác.
- B5: parent trộn “Khách hàng” và “Người dùng” → corrected dùng nhất quán “người dùng”; “chủ xe” chỉ vai trò ở summary, không đổi tên cùng thực thể trong body.
- B8: sửa “thêm thêm”; loại mâu thuẫn summary nói 6 bước nhưng body nói 10 bước; corrected dùng duy nhất sáu bước theo nguồn chính thức và diễn đạt thống nhất “ứng dụng VinFast E-Scooter”.
- Source fidelity round 1: thay hai cụm tùy chọn “nếu trạm yêu cầu” bằng yêu cầu đăng nhập và quét mã QR theo quy trình VinFast công bố; đoạn lân cận vẫn caveat giao diện/bước xác thực có thể thay đổi và ưu tiên chỉ dẫn tại trạm/ứng dụng/manual. Đây là sửa chất lượng nguồn, reviewer không xác định mã A/B mới nên không bịa thêm code.
- Chi tiết giao diện được caveat là có thể cập nhật; người dùng phải ưu tiên chỉ dẫn tại trụ, ứng dụng và sách hướng dẫn đúng mẫu xe.
- Chính sách thuê pin parent có đối tượng/thời hạn (CP7=2), không phải B11. Nội dung này được bỏ vì không cần cho quy trình sạc; corrected không nêu giá/đối tượng/thời hạn chính sách mới.

## Kết quả helper và rà toàn bộ A/B

Lượt helper cuối cho exact five files:

| ID | Title | Meta | Alias | Body words | H2/H3 | Kết luận máy | C advisory |
|---|---:|---:|---:|---:|---:|---|---|
| GC-006 | 46 | 140 | 52 | 536 | 3/0 | không có A/B máy kết luận | không có |
| GC-007 | 60 | 145 | 65 | 768 | 4/3 | không có A/B máy kết luận | C4=3 |
| GC-008 | 48 | 147 | 34 | 700 | 4/3 | không có A/B máy kết luận | không có |
| GC-009 | 49 | 147 | 38 | 870 | 6/3 | không có A/B máy kết luận | C4=5 |
| GC-010 | 55 | 148 | 39 | 853 | 5/0 | không có A/B máy kết luận | C4=4 |

Rà thủ công A1–A7/B1–B11:

- A1/A2: không còn claim VinFast “nhất” trong phạm vi so sánh, claim dẫn đầu hoặc so trực tiếp với đối thủ.
- A3: chỉ GC-006 giữ số sạc/phạm vi; mọi số khớp nguồn Evo200 chính thức, không nội suy. Các số còn lại chỉ là cấu trúc nội dung hoặc tên hóa học, không phải claim thị trường.
- A4: không có giá/chiết khấu/ưu đãi cụ thể. Từ “ưu đãi” ở GC-008 chỉ nói chương trình có thể thay đổi và dẫn cổng chính sách.
- A5: H2 trả lời đúng title; không bài nào lạc chủ đề trên 50%.
- A6: hướng dẫn sạc dùng thiết bị tương thích, dừng khi bất thường và ưu tiên manual/giao diện đúng xe; không có thao tác nguy hiểm hoặc bỏ caveat an toàn.
- A7: không có văn xuôi có nghĩa bị ẩn; file chỉ chứa field và HTML hiển thị mà evaluator đọc.
- B1: GC-006 có phạm vi Evo200 kèm tốc độ, tải trọng, phạm vi mẫu xe và caveat thực tế; GC-007 chỉ nhắc định tính rằng trang nguồn có điều kiện xác định. Các bài khác không nêu phạm vi định lượng.
- B2: GC-006 ghi đủ bộ sạc và SOC đầu–cuối; GC-007 mô tả đúng cách đọc mà không nêu mốc thời gian; các bài khác không có claim thời gian sạc định lượng.
- B3/B4: meta 140–148; title 46–60, không all-caps và không gắn năm cũ.
- B5: B5 thực tế ở cả năm parent đã được ghi vào `removed_codes`; corrected dùng nhất quán “người dùng”, còn “chủ xe” chỉ vai trò phù hợp ở summary. Tên Evo200/Vento S/VinFast E-Scooter nhất quán và không còn `VF e 34`.
- B6: năm bài không có ảnh nên B6 không áp dụng.
- B7: alias không dấu, dưới 75 ký tự và chứa từ khóa chính tương ứng title.
- B8: đã đọc toàn văn năm candidate sau sửa; không còn lỗi trong nhãn/evidence hoặc lỗi cùng họ tìm thấy.
- B9: cả năm bài trên 500 tiếng đều có ít nhất một H2.
- B10: số liệu kỹ thuật cần giữ có nguồn chính thức gần claim; các số không xác minh đã bị bỏ, không suy số thay thế.
- B11: không bài nào còn claim cụ thể về giá thuê pin, ngưỡng thay pin hoặc thời hạn bảo hành cần đủ CP7. Link cổng tra cứu không tự tạo thành cam kết chính sách.

## Disposition từng candidate của `quet_ung_vien.py`

- **GC-006 A3 — bác:** `10 giờ`, `8 giờ`, `4 giờ`, `3 giờ 30 phút`, `203 km`, `30 km/h` đều nằm trong bảng/đoạn có nguồn Evo200 chính thức ngay sau; phạm vi có điều kiện và caveat. `30 phút` là phần phút của mốc `3 giờ 30 phút`, không phải claim độc lập. **B10 — bác:** các tỷ lệ 0/20/100% là SOC đầu–cuối khớp cùng nguồn; câu so sánh dải chỉ diễn giải bảng đã dẫn nguồn.
- **GC-007:** scanner không sinh candidate A/B; review tay vẫn thực hiện đủ taxonomy.
- **GC-008 A4 — bác:** “các chương trình ... ưu đãi có thể thay đổi” không nêu giá trị cụ thể và chỉ hướng người dùng tới cổng chính sách hiện hành.
- **GC-009:** scanner không sinh candidate A/B; review tay vẫn thực hiện đủ taxonomy.
- **GC-010:** scanner không sinh candidate A/B; review tay vẫn thực hiện đủ taxonomy.

Scanner chỉ đánh dấu candidate, không tự quyết mã. Các disposition trên là quyết định manual theo guideline v1.4; C4 chỉ là advisory về khẳng định chung và không được ghi thành defect A/B.

# Nhật ký hiệu đính gold-corrected v1.4 — GC-011 đến GC-015

- Ngày biên tập và kiểm nguồn: **17/08/2026**.
- Annotator: `AI-A1`; provenance: `AI-annotated-partially-exposed`.
- Generator model: `not-exposed-by-runtime`; runtime của phiên làm trực tiếp không cung cấp model ID chính xác nên không suy đoán.
- Guideline: `v1.4`.
- Năm parent `G-011..G-015` giữ nguyên; corrected chỉ được tạo trong `docs/functional-tests/gold-corrected/`.
- Đây là dữ liệu corrected tổng hợp để kiểm tiêu chí publish, không phải nhãn mù độc lập và không chứng minh đồng thuận AI-người hoặc người-người.
- Danh sách mã trong plan là điểm bắt đầu. Lượt audit đầy đủ bổ sung A4 ở G-011, B1 ở G-015 và B5 ở cả năm parent.

## Nguồn chính thức đã kiểm

Nguồn chủ đề:

- `https://vinfastauto.com/vn_vi/nguyen-tac-va-chi-phi-bao-duong-xe-may-dien-vinfast`
- `https://vinfastauto.com/vn_vi/chi-phi-su-dung-xe-dien`
- `https://vinfastauto.com/vn_vi/nuoi-o-to-dien-vinfast-vf-e34-co-re-hon-xe-xang`
- `https://vinfastauto.com/vn_vi/chi-phi-nuoi-xe-vf-e34-hang-thang-tiet-kiem-bao-nhieu`
- `https://vinfastauto.com/vn_vi/co-nen-mua-o-to-thoi-diem-nay`

Nguồn hiện hành dùng để thay cách dẫn chính sách/tài liệu:

- `https://vinfastauto.com/vn_vi/thong-tin-bao-hanh`
- `https://vinfastauto.com/vn_vi/hop-dong-va-chinh-sach`
- `https://vinfastauto.com/vn_vi/tai-lieu-xe-may-dien`

Mọi nguồn trên được truy cập ngày **17/08/2026**. Bản corrected không sao chép giá, tỷ lệ, ngưỡng pin hoặc quyền lợi cũ từ parent; nội dung biến động được chuyển thành quy trình tra hợp đồng, hóa đơn và cổng chính thức tại thời điểm sử dụng.

## GC-011 ← G-011

- **Nguồn chủ đề:** `/vn_vi/nguyen-tac-va-chi-phi-bao-duong-xe-may-dien-vinfast`.
- **Field:** giữ title và alias; meta 144 ký tự; summary trả lời nguyên tắc dự trù; body giữ chủ đề chi phí, nhóm hạng mục, lịch, địa điểm và hồ sơ bảo dưỡng.
- **Mã đã xử lý:** A1;A4;B3;B5;B8.

Trước → sau:

- A1: parent quảng bá quyền lợi “có một không hai” và “không có ở bất kì loại xe điện hãng khác” → bỏ toàn bộ claim hơn các hãng khác.
- A4: parent nêu miễn bảo dưỡng bảy lần đầu cho một số mẫu nhưng không có thời hạn hiệu lực → bỏ giá trị khuyến mại; corrected yêu cầu kiểm tra quyền lợi theo hồ sơ hiện hành.
- B3: meta 187 ký tự → 144 ký tự.
- B5: parent trộn “người dùng”, “khách hàng” và “bạn” → corrected dùng nhất quán “người dùng”.
- B8: sửa “chỉnh chu” cùng các câu lặp/vụng bằng cách viết lại; không giữ nguyên bảng lịch dài và câu kêu gọi lỗi thời.
- GC-011 có 1.170 tiếng và 5 H2, đáp ứng điều kiện làm parent cho fixture B9 ở Task 8.

## GC-012 ← G-012

- **Nguồn chủ đề:** `/vn_vi/chi-phi-su-dung-xe-dien`.
- **Field:** giữ title và alias; meta 144 ký tự; summary/body chuyển từ tổng tiền cứng sang phương pháp lập ngân sách theo kỳ.
- **Mã đã xử lý:** B5;B8;B10;B11.

Trước → sau:

- B5: parent trộn “người dùng”, “khách hàng” và “chủ xe” khi nói cùng người sở hữu → corrected dùng nhất quán “người dùng”.
- B8: bảng chi phí có phép tính và dòng tổng không nhất quán cùng nhiều câu dài/vụng → bỏ bảng cũ, viết lại theo nhóm chi phí và chứng từ.
- B10: bỏ giá điện, mức tiêu thụ, tỷ lệ bảo dưỡng, thu nhập và ước tính chi phí không có nguồn kiểm được gần claim; không suy số thay thế.
- B11: bỏ claim đổi pin dưới ngưỡng cụ thể và gói thuê pin cũ không đủ thành phần hiệu lực hiện hành; corrected chỉ dẫn cổng hợp đồng/chính sách mà không nêu quyền lợi cụ thể.

## GC-013 ← G-013

- **Nguồn chủ đề:** `/vn_vi/nuoi-o-to-dien-vinfast-vf-e34-co-re-hon-xe-xang`.
- **Field:** giữ title và alias; meta 149 ký tự; body giữ phép so sánh VF e34 với xe xăng nhưng khóa cùng kỳ, cùng quãng đường và cùng phạm vi.
- **Mã đã xử lý:** B1;B5;B8;B10;B11.

Trước → sau:

- B1: parent nêu phạm vi 318,6 km sau một lần sạc nhưng chỉ nói “pin tiêu chuẩn”, không có chu trình đo và caveat thực tế → bỏ claim định lượng.
- B5: parent trộn “người dùng”, “khách hàng” và “chủ xe” → corrected dùng nhất quán “người dùng”.
- B8: sửa cấu trúc “Với cách khách hàng” và các lỗi câu/dấu bằng cách viết lại toàn bộ phương pháp so sánh.
- B10: bỏ mức tiêu thụ, đơn giá, tổng chi phí và ước tính bảo dưỡng không được chứng minh thành một bộ đồng nhất; corrected yêu cầu hóa đơn/chứng từ.
- B11: bỏ quyền lợi pin và giá thuê pin cũ thiếu thành phần hiệu lực hiện hành; corrected dẫn cổng chính sách mà không nêu claim cụ thể.

## GC-014 ← G-014

- **Nguồn chủ đề:** `/vn_vi/chi-phi-nuoi-xe-vf-e34-hang-thang-tiet-kiem-bao-nhieu`.
- **Field:** giữ title và alias; meta 145 ký tự; body giữ các nhóm sạc, định kỳ, hợp đồng và bảng ngân sách hàng tháng.
- **Mã đã xử lý:** B3;B5;B8;B11.

Trước → sau:

- B3: meta 172 ký tự → 145 ký tự.
- B5: parent trộn “người dùng”, “khách hàng”, “Quý khách hàng” và “chủ xe” → corrected dùng nhất quán “người dùng”.
- B8: sửa “các chi tiết cần cần bảo dưỡng”, “tiết kiện” cùng các câu lặp/vụng bằng bản hướng dẫn mới.
- B11: bỏ claim thay pin dưới ngưỡng cụ thể và giá thuê pin theo năm bán cũ; corrected yêu cầu đối chiếu hợp đồng, cổng chính sách và tài liệu bảo hành của đúng xe.
- Các số giá/chi phí cũ khác được bỏ để tránh tái sử dụng dữ liệu biến động; không ghi thêm B10 vì parent có nguồn/điều kiện cho các claim định lượng thuộc phạm vi nhãn đã xét.

## GC-015 ← G-015

- **Nguồn chủ đề:** `/vn_vi/co-nen-mua-o-to-thoi-diem-nay`.
- **Field:** giữ title và alias; meta 140 ký tự; body giữ câu hỏi thời điểm mua, so xe điện/xe xăng, khả năng sạc, chính sách và checklist quyết định.
- **Mã đã xử lý:** B1;B5;B8;B10;B11.

Trước → sau:

- B1: parent nêu 285 km theo NEDC nhưng không có caveat phạm vi thực tế → bỏ claim; corrected chỉ hướng dẫn tra đúng mẫu/điều kiện và nêu các yếu tố làm kết quả thay đổi.
- B5: parent trộn “người tiêu dùng”, “khách hàng” và “chủ xe” → corrected dùng nhất quán “người dùng”.
- B8: sửa “được hưởngg”, “bằng cáchliên hệ” cùng các câu lỗi bằng cách viết lại nội dung.
- B10: bỏ giá nhiên liệu, tuổi thọ pin, tỷ lệ bảo dưỡng và các phép tính chi phí không có nguồn gần claim; không thay bằng con số phỏng đoán.
- B11: bỏ claim đổi pin theo ngưỡng và gói thuê pin cũ thiếu thành phần hiện hành; corrected chỉ dẫn nguồn hợp đồng/chính sách và bảo hành.
- Cụm “dẫn đầu xu hướng mới” ở parent không gán A1: guideline v1.4 yêu cầu vừa có phạm vi so sánh rõ vừa nói về sản phẩm VinFast; câu này không nêu phạm vi thị trường/phân khúc. Claim đã được bỏ khi viết lại nhưng không bịa thêm mã.

## Kết quả helper và rà toàn bộ A/B

Lượt helper cuối cho exact five files:

| ID | Title | Meta | Alias | Body words | H2/H3 | Kết luận máy | C advisory |
|---|---:|---:|---:|---:|---:|---|---|
| GC-011 | 51 | 144 | 58 | 1.170 | 5/4 | không có A/B máy kết luận | C4=10 |
| GC-012 | 45 | 144 | 30 | 882 | 4/3 | không có A/B máy kết luận | C4=5 |
| GC-013 | 46 | 149 | 54 | 839 | 5/0 | không có A/B máy kết luận | C4=5 |
| GC-014 | 47 | 145 | 60 | 750 | 5/2 | không có A/B máy kết luận | không có |
| GC-015 | 58 | 140 | 36 | 794 | 5/0 | không có A/B máy kết luận | C4=5 |

Rà thủ công A1–A7/B1–B11:

- A1/A2: không corrected nào còn claim so sánh nhất trong phạm vi thị trường/phân khúc hoặc so trực tiếp với đối thủ.
- A3/A4: không giữ giá, thông số sản phẩm hoặc giá trị khuyến mại cụ thể cần đối chiếu; ngày 17/08/2026 chỉ là ngày truy cập nguồn.
- A5: H2 và body của từng bài trả lời đúng câu hỏi title; không bài nào lạc chủ đề trên 50%.
- A6: GC-011 yêu cầu dừng sử dụng khi có dấu hiệu điện/phanh bất thường, không tự mở pin/bộ sạc và ưu tiên tài liệu đúng mẫu; các bài còn lại không hướng dẫn thao tác kỹ thuật có rủi ro.
- A7: không có văn xuôi ẩn, comment hoặc thuộc tính ẩn trong năm file.
- B1/B2: corrected không nêu phạm vi hoặc thời gian sạc định lượng; hướng dẫn GC-015 chỉ yêu cầu tra đúng mẫu và caveat điều kiện thực tế.
- B3/B4: meta 140–149; title 45–58, không all-caps và không gắn năm cũ.
- B5: chỉ dùng “người dùng” cho cùng đối tượng; tên VF e34 và VinFast nhất quán.
- B6: năm bài không có ảnh nên không áp dụng.
- B7: alias giữ canonical parent, dưới 75 ký tự và chứa chủ đề tương ứng.
- B8: đã đọc toàn văn sau lượt sửa meta; không còn lỗi chính tả/ngữ pháp quan sát được.
- B9: mọi bài trên 500 tiếng đều có ít nhất một H2; riêng GC-011 có 5 H2.
- B10: không còn claim định lượng cần nguồn; công thức chỉ mô tả cách dùng hóa đơn/chứng từ, không tạo số liệu mới.
- B11: link chính sách/bảo hành chỉ là chỉ dẫn tra cứu, không nêu claim chính sách cụ thể nên CP7 không áp dụng theo guideline v1.4.

## Disposition từng candidate của `quet_ung_vien.py`

- Scanner cuối không sinh candidate A/B cho bất kỳ file GC-011..GC-015 nào.
- C4 ở GC-011/012/013/015 là advisory về câu dài, không đổi nhãn publish.
- Quyết định publish vẫn dựa trên helper cộng lượt đọc manual đầy đủ; scanner không phải bộ kết luận.

# Nhật ký hiệu đính gold-corrected v1.4 — GC-016 đến GC-020

- Ngày biên tập và kiểm nguồn: **17/08/2026**.
- Annotator: `AI-A1`; provenance: `AI-annotated-partially-exposed`.
- Generator model: `not-exposed-by-runtime`; runtime của phiên làm trực tiếp không cung cấp model ID chính xác.
- Guideline: `v1.4`.
- Parent G-016..G-020 giữ nguyên. Batch này hoàn tất exact set GC-001..GC-020.
- Đây là corrected data tổng hợp cho phép calibration riêng; không phải nhãn độc lập và không thay bằng chứng đồng thuận trên bài thật.
- Audit toàn taxonomy bổ sung B5 ở cả năm parent; G-018 bổ sung A4 và B8 ngoài candidate khởi đầu.

## Nguồn chính thức đã kiểm

Nguồn chủ đề:

- `https://vinfastauto.com/vn_vi/so-sanh-chi-phi-bao-duong-o-to-dien-va-o-to-xang`
- `https://vinfastauto.com/vn_vi/tong-quan-tram-sac-vinfast`
- `https://vinfastauto.com/vn_vi/huong-dan-cach-tim-tram-sac-bang-app-vinfast-e-scooter`
- `https://vinfastauto.com/vn_vi/ung-dung-vinfast-cho-o-to-dien`
- `https://vinfastauto.com/vn_vi/quan-ly-xe-o-to-dien-qua-ung-dung-vinfast`

Nguồn FAQ/tài liệu hiện hành:

- `https://vinfastauto.com/vn_vi/thong-tin-bao-hanh`
- `https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap/cau-hoi-xe-o-to/he-thong-tram-sac`
- `https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap/cau-hoi-xe-may-dien/san-pham/ung-dung-vinfast`
- `https://vinfastauto.com/vn_vi/cau-hoi-thuong-gap/cau-hoi-xe-o-to/san-pham/ung-dung-vinfast`
- `https://vinfastauto.com/vn_vi/node/9081`

Nguồn được truy cập ngày **17/08/2026**. Vì giao diện, tính năng và trạng thái trạm có thể thay đổi, corrected chỉ giữ nhóm chức năng được nguồn chính thức xác nhận và yêu cầu ưu tiên dữ liệu hiển thị cho đúng xe/tài khoản tại thời điểm dùng.

## GC-016 ← G-016

- **Nguồn chủ đề:** `/vn_vi/so-sanh-chi-phi-bao-duong-o-to-dien-va-o-to-xang`.
- **Field:** giữ title/alias; meta 151 ký tự; body 788 tiếng, 5 H2, giữ phép so sánh hạng mục và chi phí bảo dưỡng.
- **Mã đã xử lý:** B5;B8;B10.

Trước → sau:

- B5: parent trộn “khách hàng” và “quý khách hàng” → corrected dùng nhất quán “người dùng”.
- B8: sửa cụm lặp “thấp hơn ít nhất ít hơn”, “thường xe khuyến cáo” cùng các câu vụng bằng cách viết lại.
- B10: bỏ các tỷ lệ chi phí, tuổi thọ, số bộ phận và ước tính tiền/quãng đường không có nguồn gần claim; corrected dùng hóa đơn và cùng phạm vi.
- Claim cứu hộ trong parent nằm trong đoạn quyền lợi bảo hành, không phải khuyến mại có giá trị cụ thể theo A4; nội dung vẫn được bỏ vì dễ lỗi thời nhưng không bịa thêm mã.
- GC-016 còn trên 500 tiếng và có H2, đủ làm parent canonical cho coverage B9 nếu cần.

## GC-017 ← G-017

- **Nguồn chủ đề:** `/vn_vi/tong-quan-tram-sac-vinfast`.
- **Field:** title 74 → 48 ký tự; meta 186 → 152; giữ alias; body giữ tổng quan, kênh tra cứu, lập hành trình và an toàn.
- **Mã đã xử lý:** B1;B3;B4;B5;B8.

Trước → sau:

- B1: bỏ claim phạm vi 285 km thiếu chu trình đo/caveat.
- B3/B4: rút title và meta vào ranh giới v1.4; sửa meta sai ngữ pháp “với hơn hệ thống”.
- B5: parent trộn “người dùng”, “khách hàng”, “người sử dụng”, “chủ xe” và “người tiêu dùng” → corrected dùng nhất quán “người dùng”.
- B8: bảng trụ sạc sai số cột và các câu lỗi được thay bằng hướng dẫn tra nguồn hiện hành.
- Bảng công suất/thời gian cũ bị bỏ để tránh dùng chéo model/thiết bị; không ghi thêm B10 vì các thông số parent nằm trên trang công bố chính thức, không phải số liệu khảo sát thiếu nguồn theo nhãn đã xét.

## GC-018 ← G-018

- **Nguồn chủ đề:** `/vn_vi/huong-dan-cach-tim-tram-sac-bang-app-vinfast-e-scooter`.
- **Field:** giữ title/alias; meta 118 → 144 ký tự; body 605 tiếng, 4 H2, giữ chuẩn bị/tìm trạm/kiểm tra/sạc.
- **Mã đã xử lý:** A4;B3;B5;B8.

Trước → sau:

- A4: parent nêu trải nghiệm và chi phí sạc “hoàn toàn miễn phí” nhưng thiếu thời hạn/điều kiện → bỏ claim; corrected yêu cầu đọc biểu phí đang hiển thị.
- B3: meta 118 → 144 ký tự.
- B5: parent trộn “người dùng”, “khách hàng”, “bạn” và “các bạn” → corrected dùng nhất quán “người dùng”.
- B8: sửa “hết xe hết pin”, ký tự lạ trong alt và các câu lỗi bằng nội dung mới.
- Quy trình giao diện được caveat theo phiên bản; hướng dẫn sạc yêu cầu thiết bị tương thích, dừng khi bất thường và ưu tiên chỉ dẫn tại trạm/app.
- GC-018 không còn candidate/hidden prose, đủ làm clean parent của coverage A5/B7.

## GC-019 ← G-019

- **Nguồn chủ đề:** `/vn_vi/ung-dung-vinfast-cho-o-to-dien`.
- **Field:** giữ title/alias; meta 143; body giữ tài khoản, trạng thái pin/sạc, bản đồ, quyền người lái, đồng bộ và an toàn.
- **Mã đã xử lý:** B5;B8.

Trước → sau:

- B5: parent trộn “người dùng”, “khách hàng”, “quý khách hàng” và “chủ xe” → corrected dùng nhất quán “người dùng”; vai trò trong ứng dụng được gọi theo “người lái/quyền truy cập” khi cần.
- B8: sửa “điều khiển ô tô từ bằng thiết bị”, “được được”, dấu câu/viết hoa sai và dấu chấm lặp bằng cách viết lại.
- Cụm FOTA/SOTA và claim phí cũ bị bỏ; corrected yêu cầu xác nhận gói dịch vụ theo điều khoản hiện hành nhưng không tạo A4/B11 mới.
- GC-019 không có hidden prose/candidate, đủ làm clean parent của coverage A7.

## GC-020 ← G-020

- **Nguồn chủ đề:** `/vn_vi/quan-ly-xe-o-to-dien-qua-ung-dung-vinfast`.
- **Field:** giữ title/alias; meta 146; body giữ quy trình thiết lập, trạng thái, quyền, lệnh từ xa, pin/sạc và xử lý đồng bộ.
- **Mã đã xử lý:** A1;B5.

Trước → sau:

- A1: bỏ claim mẫu VinFast “được săn đón nhất thị trường xe xanh”; không thay bằng xếp hạng hoặc tuyệt đối khác.
- B5: parent trộn “người dùng”, “khách hàng”, “quý khách”, “người sử dụng” và “chủ xe” → corrected dùng nhất quán “người dùng”.
- Các giá trị mức sạc và thông báo theo giao diện cũ bị bỏ để tránh dùng sai phiên bản; scanner parent đánh dấu B2/B10 nhưng đây là giá trị giao diện trên chính nguồn VinFast, không phải claim thời gian sạc thiếu trụ hoặc khảo sát không nguồn nên không ghi thêm mã.

## Kết quả helper và rà toàn bộ A/B

Lượt helper cuối cho exact five files:

| ID | Title | Meta | Alias | Body words | H2/H3 | Kết luận máy | C advisory |
|---|---:|---:|---:|---:|---:|---|---|
| GC-016 | 48 | 151 | 55 | 788 | 5/0 | không có A/B máy kết luận | C4=3 |
| GC-017 | 48 | 152 | 33 | 721 | 4/3 | không có A/B máy kết luận | không có |
| GC-018 | 54 | 144 | 61 | 605 | 4/0 | không có A/B máy kết luận | không có |
| GC-019 | 64 | 143 | 37 | 772 | 6/0 | không có A/B máy kết luận | không có |
| GC-020 | 51 | 146 | 48 | 791 | 6/0 | không có A/B máy kết luận | C4=4 |

Rà thủ công A1–A7/B1–B11:

- A1/A2: không còn xếp hạng, claim hơn nhất có phạm vi hoặc so trực tiếp đối thủ.
- A3/A4: không giữ thông số, giá trị khuyến mại hoặc biểu phí cụ thể; ngày chỉ là ngày truy cập nguồn.
- A5: H2/body bám title ở cả năm; GC-018/019 được đọc riêng để bảo đảm làm clean parent.
- A6: GC-017/018 yêu cầu thiết bị tương thích, dừng khi bất thường và không thao tác màn hình khi lái; GC-019/020 yêu cầu xác nhận đúng xe/lệnh và ưu tiên cảnh báo trực tiếp.
- A7: không có văn xuôi ẩn/comment/thuộc tính ẩn; GC-019 sạch để làm parent coverage A7.
- B1/B2: không corrected nào giữ claim phạm vi hoặc thời gian sạc định lượng.
- B3/B4: meta 143–152; title 48–64, không all-caps/năm cũ.
- B5: dùng nhất quán “người dùng”; tên VinFast E-Scooter và ứng dụng VinFast đúng ngữ cảnh.
- B6: không có ảnh nên không áp dụng.
- B7: alias canonical, dưới 75 ký tự và chứa chủ đề.
- B8: đã đọc toàn văn exact five; không còn lỗi quan sát được.
- B9: mọi bài trên 500 tiếng đều có H2; GC-016 có 5 H2.
- B10: không còn claim định lượng cần nguồn.
- B11: không còn claim cụ thể về pin/bảo hành pin/thuê pin; link FAQ và bảo hành chỉ là chỉ dẫn tra cứu.

## Disposition từng candidate của `quet_ung_vien.py`

- Scanner cuối không sinh candidate A/B cho GC-016..GC-020.
- C4 ở GC-016/020 là advisory, không đổi nhãn publish.
- Publish được chốt từ helper cộng lượt đọc manual; scanner không tự quyết mã.

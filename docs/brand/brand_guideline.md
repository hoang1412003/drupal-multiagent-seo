# Brand guideline (tự trích xuất từ corpus)

**Sinh tự động** bởi `multiagent/scripts/build_brand_guideline.py` ngày 2026-08-03.
**Không sửa tay** — sửa `docs/brand/variant_candidates.json` rồi chạy lại script.

**Corpus:** 10 bài thuộc tập `BRAND` (`docs/goldset/sources.md` mục 1.6), rời hẳn gold set để tránh rò rỉ dữ liệu.

**Quy tắc chỉ được sinh khi** tỉ lệ lệch khỏi 50-50 ở mức có ý nghĩa thống kê (kiểm định nhị thức hai phía, p < 0.05).

**Cách đếm:** mỗi bài **có nhắc tới** nhóm khái niệm bỏ một phiếu cho biến thể nó dùng nhiều nhất. Bài không nhắc tới nhóm thì không bỏ phiếu — im lặng không phải phản đối. Vì vậy mẫu số là *số bài có nhắc*, không phải toàn corpus.

Hệ quả cần biết khi đọc bảng: nhóm chỉ được bàn trong ít bài thì rất khó đạt mức ý nghĩa — 4/4 bài đồng thuận tuyệt đối vẫn cho p = 0,125. Đó là giới hạn thật của cỡ mẫu, không phải lỗi; cách xử lý là thu thêm corpus, không phải hạ mức ý nghĩa.

## Thuật ngữ chuẩn

| Chuẩn | Không dùng | Bài bầu / bài có nhắc | Số lần | p-value |
|---|---|---|---|---|
| ô tô điện | xe hơi điện | 6/6 | 129/130 | 0.03125 |

## Cách viết tên model

Dạng chuẩn: `VF 3`, `VF 5`, `VF 6`, `VF 7`, `VF 8`, `VF 9`, `VF e34`

Trong corpus: 28 chỗ viết đúng dạng chuẩn.

## Xưng hô

_Chưa đủ căn cứ để chốt xưng hô chuẩn._

## Quy ước viết hoa tiêu đề

Chuẩn: **SENTENCE_CASE** — 9/10 bài, p = 0.02148.

## Từ bị loại (corpus chưa bao giờ dùng)

_(không có)_

## Chưa đủ căn cứ — KHÔNG sinh quy tắc

Tiêu chí tương ứng sẽ trả `NA` lúc chấm (bị loại khỏi cả tử số lẫn mẫu số), **không** phải cho 0 điểm. Đây cũng là tín hiệu nên thu thêm corpus `BRAND` (spec mục 4.4).

| Loại | Ứng viên | Bài bầu / bài có nhắc | p-value |
|---|---|---|---|
| term | xe máy điện, xe gắn máy điện, xe máy chạy điện | 4/4 | 0.125 |
| term | trạm sạc, trụ sạc | 5/5 | 0.0625 |
| address_form | bạn, quý khách, khách hàng, người dùng | 5/10 | 1.0 |

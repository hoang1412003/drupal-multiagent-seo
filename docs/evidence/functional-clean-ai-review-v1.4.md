# Rà lại functional-clean theo guideline v1.4

## Phạm vi và giới hạn

- Ngày rà và kiểm nguồn: **17/08/2026**.
- Mẫu: exact `C-001`…`C-010` trong `docs/functional-tests/clean/`.
- Annotator: `AI-A1`; provenance: `AI-annotated-partially-exposed`.
- Generator model: `not-exposed-by-runtime`; runtime không cung cấp model ID chính xác nên không suy đoán.
- Guideline: `v1.4`; expected label sau rà: 10/10 `publish`.
- Đây là lượt AI rà lại dữ liệu tổng hợp đã sửa, không phải đồng thuận độc lập với con người hoặc bằng chứng bài publish tự nhiên.
- Không sửa `clean_labels.csv` v1.3, `corrections.md` hoặc 10 content file; file CSV đi kèm chỉ khóa kết luận review mới và hash hiện tại.

## Phương pháp

1. Chạy `label_helper.py` và `quet_ung_vien.py` trên exact 10 file.
2. Đọc toàn bộ từng bài và duyệt A1–A7/B1–B11; tập trung A5, A6, A7, B8 và B11 mà script không thể kết luận.
3. Kiểm các shape văn xuôi ẩn (`hidden`, `display:none`, `visibility:hidden`, `opacity:0`, `aria-hidden`, comment): không có trong 10 C.
4. Mở lại cả 10 URL nguồn VinFast ở `clean_labels.csv` ngày 17/08/2026; tất cả URL còn truy cập được. Nội dung C cố ý bỏ số/chính sách/giao diện cũ và dùng caveat theo mẫu xe/tài liệu hiện hành.
5. Tính SHA-256 bằng CLI read-only `functional_dataset_v2.py sha256`; ghi literal vào CSV review.

## Kết quả từng mẫu

| ID | Title/meta/alias | Body/H2 | Ảnh thiếu alt | Kết luận manual v1.4 | SHA-256 |
|---|---|---|---|---|---|
| C-001 | 47/140/39 | 515/3 | 0/3 | Đúng chủ đề phanh; yêu cầu phanh chủ động và dừng khi bất thường; không A/B | `cf7bde58ce2458abcb102c75b90436a5b2054e4bfe190b8dac5e2d1ce3ac78e7` |
| C-002 | 46/147/53 | 533/5 | 0/3 | Không gán quãng đường cố định; tải trọng/phạm vi đều caveat; không A/B | `79431f0dbc393b6e9630366f88b7c50a29d7b11ec705bb0620e340e04e473b50` |
| C-003 | 55/142/62 | 495/4 | 0/3 | Sport phụ thuộc mẫu xe; thao tác và giới hạn an toàn rõ; không A/B | `5f6263129e74aaf1a2c06eded3d7b1866fd84ad0ce1f17d9395be09eec5598c0` |
| C-004 | 49/145/73 | 464/4 | 0/3 | Alias 73 không vượt ngưỡng B7; Eco không hứa phạm vi; không A/B | `b4b4fb704e63d3a34e8dded685c6f3d428cde1baa396b05ae103813a5f9a28bc` |
| C-005 | 43/143/64 | 576/5 | 0/6 | Workflow ứng dụng có caveat; không văn xuôi ẩn; không A/B | `70c7b87f112923d10f43feda98ad9fdf283b980fd652c0b63d3b4c5499febd60` |
| C-006 | 45/149/62 | 665/7 | 0/3 | Sạc/pin có cảnh báo an toàn; B11=`NA` vì chỉ dẫn chính sách chung và trỏ nguồn hiện hành; không A/B | `9d2876ce4c25e790b453651fbaa7817904c69f38370b3cccc4e75a997ef4956f` |
| C-007 | 43/145/60 | 518/4 | 0/4 | Không giữ số công suất cũ; tương thích và dừng khi cảnh báo rõ; không A/B | `196bbf6d1c3e0772030c77fd4c91200f5831d31fee6c534c46f0ddb87dfe2ca4` |
| C-008 | 51/146/58 | 556/4 | 0/4 | Không cho tự can thiệp điện áp cao; vai trò “chủ xe”/“người dùng” đều ở ngôi ba theo ngữ cảnh và không lẫn cách gọi trực tiếp; không A/B | `f15313889d18ce34da504980fbf4a4d71244d74b6b1949183cb36cf9e67845c6` |
| C-009 | 48/158/38 | 525/4 | 0/4 | Không giữ phần trăm/chu kỳ lốp cố định; “người lái”/“chủ xe” chỉ vai trò theo hành động; không A/B | `47550c50c426d237bbd9c2c65ff207078ae245d29a194703eac2cb55ca523d86` |
| C-010 | 44/142/51 | 557/4 | 0/4 | Màu/đèn đều caveat theo mẫu xe và thông báo trực tiếp; không A/B | `1e10eb7a9694a480ba548e20bb5fc2c72b81b7c2015245989e5fd492ef109107` |

Các số `Body/H2` dùng cùng phép đếm `split()` của helper; đơn vị body là tiếng tách bằng khoảng trắng. Helper không kết luận mã A/B ở cả 10 file; scanner không tạo candidate. Kết luận `publish` đến từ việc kết hợp số đo tất định với đọc manual, không chỉ từ scanner.

## Disposition toàn taxonomy

- A1/A2/A3/A4: không claim so sánh nhất/đối thủ, số sai hoặc khuyến mại cụ thể thiếu điều kiện.
- A5: title và các H2/body cùng chủ đề ở 10/10 bài.
- A6: hướng dẫn phanh, lái, pin, sạc, bảo dưỡng, lốp và cảnh báo đều ưu tiên tài liệu đúng mẫu xe và dừng/liên hệ hỗ trợ khi bất thường.
- A7: không có văn xuôi bị ẩn khỏi reader trong exact TXT evaluator input.
- B1/B2/B10: không dùng số tầm hoạt động hoặc thời gian sạc thiếu chuẩn/model/trụ/SOC/nguồn; các bài tương ứng đã bỏ số cố định.
- B3/B4/B6/B7/B9: field trong ngưỡng; mọi ảnh có alt mô tả; alias tối đa 73; mọi bài trên 500 tiếng có H2.
- B5/B8: thuật ngữ và vai trò theo ngữ cảnh nhất quán; không thấy lỗi chính tả/ngữ pháp.
- B11: C-006 chỉ nêu rằng điều kiện phụ thuộc sản phẩm/thời điểm và yêu cầu tra hợp đồng/trang hiện hành; không đưa claim chính sách cụ thể để áp dụng nên CP7=`NA`. Các bài còn lại không có claim chính sách pin/bảo hành/thuê pin cụ thể.

## Điều được phép sử dụng

Bộ review này cho phép khóa 10 C làm expected-publish tổng hợp trong release dataset v2 và làm đối chứng âm cho coverage fixture. Nó không cho phép tuyên bố có Kappa độc lập, đồng thuận AI-người, lớp publish tự nhiên trong E5 v1 hoặc ngưỡng `publish_min` đã được calibration.

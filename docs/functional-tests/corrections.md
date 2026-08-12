# Nhật ký hiệu đính tập `functional-clean`

Ngày hiệu đính: 2026-08-11  
Người gán: `A1`  
Guideline: `v1.3`

## Nguyên tắc truy vết

- Gold set calibration: 33 mẫu (20 original + 13 perturbed), không có lớp publish.
- Functional-clean: 10 mẫu corrected, expected publish, không tham gia E5/Kappa.
- Evaluation suite: 43 mẫu, chỉ số phải báo cáo riêng theo lát dữ liệu.
- `docs/functional-tests/raw_html/C-xxx.html` là bằng chứng nguồn tải từ vinfastauto.com và không được sửa.
- `docs/functional-tests/clean/C-xxx.txt` là bản corrected dùng để đánh giá lớp `publish`.
- Các bài được viết lại ở mức cần thiết để loại thông tin cũ, sai, thiếu điều kiện hoặc hướng dẫn có thể gây mất an toàn. Vì vậy tập này là dữ liệu augmented/corrected, không phải natural-only.
- Extractor từ chối ghi đè tệp đã có; chỉ dùng `--force` khi chủ động muốn tạo lại bản thô và chấp nhận mất bản corrected hiện tại.

## Phạm vi sửa theo bài

| ID | Các vấn đề chính trong bản bóc tách ban đầu | Hướng hiệu đính |
|---|---|---|
| `C-001` | Meta ngắn; lỗi câu chữ; mô tả phanh có thể khiến người đọc hiểu sai vai trò của phanh ma sát | Viết lại phần phanh tái sinh/phanh ma sát; thêm chỉ dẫn dừng xe và kiểm tra an toàn |
| `C-002` | Số liệu tầm hoạt động cũ hoặc thiếu chuẩn đo; diễn đạt thiếu nhất quán | Bỏ số cố định; chuyển sang lập kế hoạch theo tài liệu của đúng mẫu xe và điều kiện thực tế |
| `C-003` | Thông số và giá theo thời điểm cũ; một số khẳng định không còn phù hợp cho mọi mẫu xe | Viết lại theo đặc tính chung của chế độ Sport; yêu cầu đối chiếu tài liệu từng mẫu xe |
| `C-004` | Khẳng định rộng và số liệu vận hành không đủ điều kiện | Viết lại công dụng, cách kích hoạt và giới hạn của chế độ Eco theo hướng có điều kiện |
| `C-005` | Mô tả giao diện cũ; số liệu và hướng dẫn sạc có nguy cơ không còn đúng với ứng dụng hiện tại | Giữ workflow ổn định ở mức chức năng; bổ sung xử lý khi dữ liệu ứng dụng và xe sai lệch |
| `C-006` | Meta ngắn; chính sách cũ; thông số theo phiên bản; thao tác pin cần tăng mức an toàn | Bỏ chính sách/thông số biến động; nhấn mạnh đúng bộ sạc, đúng loại pin và không can thiệp điện áp cao |
| `C-007` | Claim so sánh nhất; thông số trụ cũ và có chỗ sai đơn vị; bảng AC/DC dễ gây hiểu nhầm | Viết lại theo phân loại AC/DC, tính tương thích và quy trình sạc an toàn; bỏ số công suất cố định |
| `C-008` | Có hướng dẫn người dùng tự xử lý dung dịch làm mát; câu chữ chưa chuẩn | Chuyển phần pin/làm mát cho kỹ thuật viên; bổ sung phanh, lốp, bộ phận hao mòn và phần mềm |
| `C-009` | Lỗi câu chữ; phần trăm và chu kỳ thay/đảo lốp không nêu nguồn hoặc điều kiện | Bỏ ngưỡng cố định; hướng dẫn đối chiếu thông số xe, tình trạng lốp và khuyến nghị nhà sản xuất |
| `C-010` | Meta ngắn; lỗi kỹ thuật như nắp bình xăng trên ô tô điện và mô tả sai chức năng cảnh báo | Viết lại theo màu cảnh báo và các nhóm pin, điện, phanh, lốp, nhiệt độ; bổ sung cách dừng xe an toàn |

## Điều kiện chốt nhãn

Mười bản cuối được chốt `publish` vì không còn mã A/B theo guideline v1.3. `label_helper.py` không phát hiện B3/B4/B6/B7/B9; `quet_ung_vien.py` không tìm thấy ứng viên A1/A2/A3/A4/B1/B2/B5/B10; người gán đã đọc kiểm A5, A6 và B8. Không bài nào đạt ngưỡng lặp để ghi C4/C5.

Khi chạy pipeline, báo cáo riêng `publish_rate`, `false_positive_articles` và `false_positive_issues`; không đưa 10 mẫu này vào E5 hoặc Kappa.

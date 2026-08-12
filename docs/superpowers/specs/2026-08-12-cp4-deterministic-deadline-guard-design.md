# Thiết kế chốt thời hạn tất định cho CP4

**Ngày:** 2026-08-12

**Trạng thái:** Đã được người dùng duyệt

**Phạm vi:** Compliance Agent, tiêu chí CP4

**Không thuộc phạm vi:** thay nhãn gold set, sửa nội dung G-008/P-006a, chạy E1/E5, mở rộng KB

## 1. Bối cảnh và nguyên nhân gốc

CP4 phát hiện khuyến mại hoặc ưu đãi nêu giá trị cụ thể nhưng thiếu thời hạn hoặc điều kiện áp dụng. Mức `0` của CP4 sinh cờ `critical`, nên chỉ một kết luận sai cũng đủ để Aggregator veto cả bài thành `rejected`.

Sau bản sửa B14, prompt đã dặn LLM đọc lại mốc thời gian và đưa thẳng hai ví dụ đúng vào chỉ dẫn. Tuy nhiên, E5 vẫn ghi nhận báo động giả:

- G-008 có khuyến mại `199.000 đồng/tháng`, khoảng ngày `01/07 - 20/09/2023` và thời lượng `trong vòng 3 tháng`, nhưng có lượt bị chấm CP4 mức `0`. Nhãn người của bài là `needs_revision`, chỉ ghi nhận B8; cờ CP4 làm máy trả `rejected`.
- P-006a ghi `Trước 6/4/2022` và `áp dụng đến 6/4/2022` cho ưu đãi đến 250 triệu đồng nhưng vẫn bị báo thiếu thời hạn.

Đây là giới hạn của sửa bằng prompt, không phải thiếu thêm một ví dụ trong prompt. LLM đang được giao đồng thời hai việc khác bản chất: nhận diện mốc thời gian có cấu trúc và đọc hiểu điều kiện áp dụng. Việc thứ nhất đo được tất định, nhưng sai số của nó hiện có quyền tạo veto pháp lý.

## 2. Mục tiêu và tiêu chí thành công

### 2.1. Mục tiêu

Tách CP4 thành hai phép kiểm:

1. Code xác định khuyến mại có nêu thời hạn hay không.
2. LLM xác định điều kiện áp dụng có đầy đủ hay không.

Code ghép hai kết quả thành mức CP4 cuối cùng. LLM không còn được tự kết luận cả hai vế trong một nhãn duy nhất.

### 2.2. Tiêu chí thành công

- G-008 và P-006a không còn bị CP4 gắn cờ vì thiếu thời hạn.
- Khuyến mại có thời hạn nhưng thiếu điều kiện vẫn là CP4 mức `0`, `critical`.
- Khuyến mại có điều kiện nhưng thiếu thời hạn vẫn là CP4 mức `0`, `critical`.
- Lời mời chung chung không nêu giá trị cụ thể và chính sách nhà nước vẫn là `NA`.
- Không tăng số lần gọi LLM.
- Không thay đổi bảng severity hoặc hợp đồng output của Compliance Agent.
- Mọi hành vi mới được khóa bằng test không gọi API và không đọc KB.

## 3. Các phương án đã cân nhắc

### 3.1. Chỉ sửa prompt

Không chọn. Prompt hiện đã cảnh báo rõ và chứa đúng ví dụ đang bị chấm sai. Thêm câu chữ không tạo được bảo đảm tất định cho một quyết định có quyền veto.

### 3.2. Thấy mốc thời gian thì hạ mọi CP4 mức 0 xuống mức 1

Không chọn. Câu `Giảm 3 triệu đồng đến 31/08` có thời hạn nhưng vẫn có thể thiếu đối tượng hoặc điều kiện áp dụng. Hạ mức chỉ vì thấy ngày sẽ bỏ lọt một lỗi A4 thật.

### 3.3. Tách thời hạn và điều kiện, rồi ghép bằng code

Chọn. Cách này giao phần có cấu trúc cho regex, giữ phần cần hiểu ngữ nghĩa cho LLM và không làm yếu định nghĩa A4.

## 4. Thiết kế hành vi

### 4.1. Trách nhiệm của LLM

Prompt CP4 được đổi để LLM chỉ đánh giá khuyến mại có giá trị cụ thể và điều kiện áp dụng:

- `NA`: bài không có khuyến mại của doanh nghiệp nêu giá trị cụ thể.
- `0`: có khuyến mại nêu giá trị cụ thể nhưng thiếu điều kiện áp dụng.
- `2`: có khuyến mại nêu giá trị cụ thể và điều kiện áp dụng đầy đủ.

LLM vẫn phải trả `evidence` nguyên văn cho mức `0` và `2`. Chính sách nhà nước và lời mời chung chung không có giá trị cụ thể tiếp tục là `NA`.

Không thêm mức mới vào schema. Ý nghĩa `muc` của riêng CP4 trong prompt được thu hẹp, còn hình dạng JSON giữ nguyên.

### 4.2. Trách nhiệm của code

Sau khi bằng chứng CP4 đã qua kiểm tra trích dẫn, code tìm dấu hiệu thời hạn trong:

1. chính `evidence`; và
2. một cửa sổ văn bản liền kề quanh vị trí bằng chứng trong cùng field.

Không quét ngày tháng trên toàn bài. Một ngày xuất bản hoặc ngày thuộc mục khác không được dùng để chứng minh thời hạn cho khuyến mại đang xét.

Các dạng thời hạn tối thiểu cần nhận diện:

- ngày cụ thể: `01/07/2023`, `6/4/2022`;
- khoảng ngày: `01/07 - 20/09/2023`, `25/06 – 31/08/2024`;
- tiền tố/hậu tố: `từ ngày`, `kể từ ngày`, `trước`, `đến`, `tới hết`;
- thời lượng: `trong vòng 3 tháng`, `trong 3 tháng đầu`, `3 tháng kể từ thời điểm kích hoạt`;
- giới hạn sự kiện: `áp dụng đến khi hết hàng`.

Regex chỉ kết luận **có dấu hiệu thời hạn**, không suy luận điều kiện áp dụng và không tự xác định một câu có phải khuyến mại hay không.

### 4.3. Bảng ghép kết quả

| Kết quả LLM về điều kiện | Có thời hạn | CP4 cuối | Ý nghĩa |
|---|---:|---:|---|
| `NA` | bất kỳ | `NA` | Không có khuyến mại cụ thể để xét |
| `0` | bất kỳ | `0` | Thiếu điều kiện áp dụng |
| `2` | không | `0` | Đủ điều kiện nhưng thiếu thời hạn |
| `2` | có | `2` | Đủ cả điều kiện và thời hạn |

Không dùng mức `1` trong phiên bản này. Rubric hiện định nghĩa A4 theo hai trạng thái: thiếu ít nhất một thành phần là lỗi chặn, đủ cả hai là đạt. Đưa mức `1` vào sẽ tự tạo một mức nghiệp vụ chưa được guideline định nghĩa và có thể làm mất veto.

### 4.4. Bằng chứng và gợi ý sửa

- Nếu LLM kết luận thiếu điều kiện, giữ nguyên bằng chứng và lý do của LLM.
- Nếu LLM kết luận đủ điều kiện nhưng code không tìm thấy thời hạn, CP4 chuyển thành mức `0` với lý do tất định yêu cầu bổ sung thời hạn ngay cạnh khuyến mại.
- `occurrences` tiếp tục trỏ tới field và evidence CP4 để UI hiển thị đúng đoạn cần sửa.
- Nếu evidence không có thật trong bài, giữ nguyên quy tắc hiện tại: CP4 trở thành `NA`; code không được dùng một trích dẫn bịa để tạo veto.
- Nếu lời gọi LLM hỏng, giữ nguyên cơ chế suy giảm hiện tại; regex thời hạn một mình không đủ căn cứ để quyết định bài có khuyến mại hay điều kiện gì.

## 5. Thành phần và luồng dữ liệu

Thay đổi tập trung trong `multiagent/src/agents/compliance.py`:

1. `_LLM_PROMPT` thu hẹp nhiệm vụ CP4 còn đánh giá điều kiện.
2. Một helper thuần nhận `evidence` và `text_theo_field`, định vị evidence trong field rồi kiểm tra mốc thời gian ở evidence/cửa sổ liền kề.
3. Một helper ghép tiêu chí CP4 từ LLM với kết quả thời hạn tất định.
4. `run()` dùng tiêu chí CP4 đã ghép thay cho `llm["CP4"]` trực tiếp.

Không đưa helper này sang `text_utils.py`: nhận diện thời hạn khuyến mại là quy tắc nghiệp vụ riêng của Compliance/CP4, không phải tiện ích văn bản dùng chung.

Hợp đồng bên ngoài không đổi:

```text
fields
  -> một lần gọi LLM Compliance
  -> kiểm chứng evidence
  -> regex thời hạn CP4 trong vùng liền kề
  -> ghép mức CP4
  -> score_from_criteria()
  -> flags + criteria + score
```

## 6. Biên an toàn

### 6.1. Phạm vi cửa sổ

Cửa sổ phải đủ để bắt heading hoặc câu ngay trước/sau bằng chứng, như G-008 có khoảng ngày ở dòng giới thiệu và giá trị khuyến mại ở dòng kế tiếp. Kích thước cụ thể sẽ được khóa trong kế hoạch triển khai và test, không được mở rộng thành quét toàn field.

Nếu evidence gồm nhiều mảnh, helper xét các vị trí mảnh tìm thấy và hợp nhất các cửa sổ tương ứng. Không lấy lần xuất hiện đầu tiên một cách mù nếu cùng câu xuất hiện nhiều chỗ.

### 6.2. Không suy diễn từ ngày rời rạc

Một ngày trần trụi chỉ có giá trị khi nằm trong evidence hoặc cửa sổ liền kề của khuyến mại. Các từ khóa quan hệ như `từ`, `trước`, `đến`, `trong vòng`, `kể từ`, `áp dụng` làm bằng chứng mạnh hơn, nhưng khoảng ngày định dạng rõ vẫn được chấp nhận.

### 6.3. Không thay đổi dữ liệu đo

- Không sửa G-008, P-006a hoặc `labels.csv`.
- Không thêm mẫu vừa sửa vào brand corpus hay KB.
- Các test hồi quy có thể đọc fixture thật, nhưng không thay đổi nhãn và không chạy qua API.

## 7. Kiểm thử

Tất cả test mới nằm trong `multiagent/scripts/test_compliance_rubric.py` và dùng dependency injection hiện có để giả lập kết quả LLM/CP3.

### 7.1. Test helper thời hạn

- Nhận diện từng nhóm định dạng đã liệt kê ở mục 4.2.
- Không nhận một con số/thời lượng không liên quan làm thời hạn khuyến mại.
- Không lấy ngày nằm xa evidence trong cùng bài.
- Nhận ngày ở câu hoặc block ngay trước/sau evidence.

### 7.2. Test bảng ghép

- `NA` giữ `NA` bất kể có ngày.
- LLM `0` giữ mức `0` dù có ngày, vì vẫn thiếu điều kiện.
- LLM `2` + không có thời hạn thành mức `0` và sinh `critical`.
- LLM `2` + có thời hạn giữ mức `2` và không sinh flag CP4.
- Evidence bịa không được dùng để sinh mức `0`.

### 7.3. Test hồi quy dữ liệu thật

- Dùng đoạn G-008 chứa `01/07 - 20/09/2023`, `199.000 đồng/tháng` và `trong vòng 3 tháng`; với kết quả LLM “đủ điều kiện”, CP4 phải là mức `2`.
- Dùng đoạn P-006a chứa `Trước 6/4/2022` và ưu đãi 250 triệu đồng; với kết quả LLM “đủ điều kiện”, CP4 phải là mức `2`.
- Dùng ca perturbation A4 `giảm ngay 3 triệu đồng cho khách đặt cọc sớm` không có thời hạn; CP4 phải là mức `0`, `critical`.
- Dùng ca có thời hạn nhưng thiếu điều kiện để chứng minh chốt thời gian không làm mất lỗi A4.

Test phải được chạy theo RED → GREEN: thêm test trước, xác nhận thất bại đúng nguyên nhân, sau đó mới sửa production code.

## 8. Tài liệu và phép đo sau triển khai

Sau khi code và test hoàn tất:

- Cập nhật `docs/rubrics.md` để mô tả CP4 hai thành phần.
- Cập nhật `docs/technical-debt.md` mục 8.4 từ đề xuất “thấy thời gian thì kéo lên mức 1” sang thiết kế ghép không dùng mức 1, đồng thời ghi trạng thái đã xử lý khi thực sự hoàn tất.
- Cập nhật công thức/metadata version nếu prompt hoặc đường chấm điểm thay đổi.
- Chạy toàn bộ test cục bộ, không gọi API.
- Không chạy E1/E5 ngay. Đây là thay đổi đường chấm điểm nên E1 và E5 cũ hết hiệu lực; hai phép đo chỉ chạy một lần sau khi toàn bộ code cần sửa đã được khóa và người dùng xác nhận chi phí.

## 9. Ngoài phạm vi

- Không chuyển toàn bộ việc phát hiện khuyến mại sang regex.
- Không xây trình phân tích pháp lý tổng quát.
- Không thêm mức CP4 mới hoặc đổi severity.
- Không sửa CP1, CP2, CP3, CP5, CP6, CP7 hoặc CP8 trong cùng thay đổi.
- Không thu thêm dữ liệu RAG.
- Không chạy E1, E5 hoặc gọi Anthropic trong giai đoạn triển khai và unit test.

# Thiết kế tập corrected-publish và criterion coverage v1

**Ngày:** 2026-08-17

**Trạng thái:** Đã được chủ dự án duyệt thiết kế; chưa tạo dữ liệu, chưa sửa
runner, chưa chạy pipeline

**Liên quan:** policy candidate `cam-nang-vn-v2` trong
`2026-08-17-publish-blocking-decision-policy-design.md`

**Phạm vi:** 20 bản corrected từ `G-001..G-020`, 11 biến thể coverage một
lỗi, manifest/provenance, hợp đồng đo lường và tiêu chí nghiệm thu

**Ngoài phạm vi:** sửa 33 mẫu gold gốc, thay nhãn/evidence v1, thay thế bằng
chứng đồng thuận người--AI, sửa score path, chạy API trả phí

## 1. Quyết định

Giữ nguyên 33 mẫu gold gốc. Tạo hai lớp dữ liệu dẫn xuất tách biệt:

1. `gold-corrected`: 20 bản `GC-001..GC-020`, mỗi bản bắt nguồn từ một mẫu
   `G` và được sửa cho tới khi không còn mã A/B theo guideline v1.4.
2. `criterion-coverage`: 11 bản `CV-*`, mỗi bản bắt nguồn từ một bài
   `GC`/`C` đã sạch và chỉ chứa đúng một mã mục tiêu đang thiếu hoặc có độ
   phủ thấp.

Hai lớp này là dữ liệu corrected/synthetic có provenance AI. Chúng kiểm cơ
chế publish và quyền chặn của từng criterion; không trở thành gold tự nhiên,
không tham gia Kappa chính và không chứng minh `publish_min` đã được
calibrate.

Không sửa đè bài gốc để đổi mã lỗi. Một bài đã có nhiều mã có thể được dùng
làm **nguồn chủ đề**, nhưng phải đi qua bản corrected sạch trước khi tạo biến
thể một lỗi. Nếu chèn A5 vào một bài vẫn còn B1/B8 thì quyết định cuối không
cho biết A5 có được phát hiện hay không.

## 2. Ranh giới cam kết

Thiết kế này bảo đảm các chỉ số dưới đây **có đại lượng để đo** nếu dữ liệu,
runner và pipeline hoàn tất đúng hợp đồng:

- khả năng mở đường `publish` trên bài corrected;
- tỷ lệ chặn oan trên 30 bài expected-publish;
- tỷ lệ bỏ lọt publish trên 33 bài gốc cần chặn;
- recall và nhầm lẫn giữa ba lớp;
- tỷ lệ chuyển đúng theo 20 cặp trước--sau `G -> GC`;
- coverage và hành vi của các mã hiếm A3/A5/A6/A7/B6/B7/B9.

Thiết kế **không bảo đảm** giá trị đo được sẽ đạt ngưỡng, không bảo đảm hệ
thống tổng quát hoá ra bài publish tự nhiên và không thay bằng chứng đồng
thuận từ một người gán nhãn độc lập. Một phép đo cho kết quả trượt nhưng có
provenance đầy đủ vẫn là phép đo hoàn tất; không được sửa mẫu sau khi xem
output để biến trượt thành đạt.

Do chủ dự án không dùng lượt gán mù độc lập cho lớp publish, báo cáo cuối
phải gọi đúng đây là `corrected/synthetic publish evidence`. Dự án có thể
đóng hạng mục **nghiệm thu kỹ thuật policy v2** bằng bằng chứng này, nhưng
không được viết rằng đã chứng minh đồng thuận người--AI trên bài publish tự
nhiên.

Spec policy v2 trước đó đăng ký gate gán lại v1.4 mù và test--retest. Việc
chủ dự án chọn AI tự gán không làm gate đó tự chuyển thành `pass`. Protocol
đánh giá mới phải ghi rõ một trong hai trạng thái:

- `independent_label_reliability = measured` nếu sau này có lượt gán độc
  lập đúng giao thức; hoặc
- `independent_label_reliability = not_demonstrated` trong phạm vi hiện tại.

Không được dùng 33/33 nhãn AI khớp nhãn cũ làm thay thế, vì lượt AI đã có
nguy cơ tiếp xúc một phần với đáp án trước khi khóa.

## 3. Bốn lớp dữ liệu

| Lớp | Số mẫu | Nhãn kỳ vọng | Vai trò | Có vào điểm chính? |
|---|---:|---|---|---|
| Gold `G/P` gốc | 33 | 23 `needs_revision`, 10 `rejected` | Bằng chứng cần chặn | Có |
| Functional-clean `C` | 10 | `publish` | Corrected publish hiện hành | Có, báo theo lát riêng |
| Gold-corrected `GC` | 20 | `publish` | Cặp sau sửa của 20 `G` | Có, báo theo lát riêng |
| Criterion coverage `CV` | 11 | 4 `needs_revision`, 7 `rejected` | Cô lập từng blocker hiếm | Không; chỉ pass/fail theo mã |

Bộ nghiệm thu chính có 63 mẫu với phân bố:

```text
publish          30
needs_revision   23
rejected         10
```

Không gọi 63 mẫu là 63 quan sát độc lập: `G/GC` là cặp, nhiều `P` dùng chung
nguồn với nhau hoặc với `G`, và `C/GC/CV` là dữ liệu hiệu đính. Mọi chia fold
hoặc phân tích tổng quát hoá phải nhóm theo `source_url` và quan hệ cha--con.

## 4. Độ phủ mục tiêu

Lượt nhãn AI v1.4 candidate hiện có độ phủ A như sau:

| Mã | Số mẫu hiện có |
|---|---:|
| A1 | 5 |
| A2 | 2 |
| A3 | 1 |
| A4 | 2 |
| A5 | 0 |
| A6 | 0 |
| A7 | 0 |

Các mã B thấp nhất là B6 = 1, B7 = 1 và B9 = 0; B8 chiếm 23 mẫu. Con số
tổng theo lớp vì vậy chưa đủ để kết luận taxonomy đã được kiểm đều.

Tập coverage cố định trước lượt chạy đầu tiên:

| ID | Số mẫu | Nhãn kỳ vọng | Mục đích |
|---|---:|---|---|
| `CV-A3-01` | 1 | `rejected` | Đưa A3 lên tối thiểu 2 trường hợp |
| `CV-A5-01..02` | 2 | `rejected` | Phủ nội dung lạc đề trên 50% |
| `CV-A6-01..02` | 2 | `rejected` | Phủ hướng dẫn kỹ thuật mất an toàn |
| `CV-A7-01..02` | 2 | `rejected` | Phủ văn xuôi ẩn trong input evaluator |
| `CV-B6-01` | 1 | `needs_revision` | Đưa B6 lên tối thiểu 2 trường hợp |
| `CV-B7-01` | 1 | `needs_revision` | Đưa B7 lên tối thiểu 2 trường hợp |
| `CV-B9-01..02` | 2 | `needs_revision` | Phủ bài trên 500 tiếng thiếu H2 |

Không tăng hoặc giảm 11 mẫu sau khi xem kết quả. Nếu audit trước lượt chạy
phát hiện một mã mục tiêu không thật sự hiện diện hoặc phát sinh mã thứ hai,
phải sửa mẫu, tăng version manifest và khóa lại trước khi chạy.

## 5. Cấu trúc tệp đề xuất

Không mở rộng `clean_labels.csv`, vì test hiện hành khóa file đó ở đúng
`C-001..C-010`. Hai lớp mới có thư mục và manifest riêng:

```text
docs/functional-tests/
  clean/                         # C-001..C-010, giữ nguyên
  clean_labels.csv               # giữ nguyên
  gold-corrected/
    GC-001.txt
    ...
    GC-020.txt
  gold-corrected-labels.csv
  criterion-coverage/
    CV-A3-01.txt
    ...
    CV-B9-02.txt
  criterion-coverage-labels.csv
  corrections-v1.4.md
  coverage-changes-v1.4.md
```

`docs/goldset/raw/G-xxx.txt`, `docs/goldset/labels.csv` và mọi evidence v1
là bất biến.

## 6. Hợp đồng manifest và provenance

Mỗi manifest mới phải có tối thiểu:

| Cột | Ý nghĩa |
|---|---|
| `sample_id` | ID duy nhất trong lớp dữ liệu |
| `parent_sample_id` | `G-xxx`, `GC-xxx` hoặc `C-xxx` trực tiếp sinh mẫu |
| `source_url` | Nguồn chủ đề ban đầu |
| `variant` | `corrected` hoặc `criterion-coverage` |
| `expected_label` | Nhãn suy ra theo A/B |
| `target_code` | Rỗng với GC; đúng một mã với CV |
| `removed_codes` | Các mã đã loại khi tạo GC |
| `injected_codes` | Rỗng với GC; đúng `target_code` với CV |
| `annotator` | Provenance người/AI tạo và kiểm |
| `guideline_version` | `v1.4` |
| `created_at` | Ngày tạo |
| `content_sha256` | Chặn sửa âm thầm sau khi khóa |
| `notes` | Tóm tắt thay đổi và căn cứ |

Manifest phải từ chối duplicate ID, parent không tồn tại, nhãn không khớp
mã A/B, CV có nhiều hơn một `injected_code`, checksum sai và đường dẫn thoát
khỏi thư mục được phép.

## 7. Quy trình tạo 20 GC

1. Sao chép đủ field evaluator đọc từ `G` tương ứng; giữ liên kết nguồn.
2. Dùng nhãn v1.4 candidate làm danh sách khởi đầu, không coi nó là danh
   sách đầy đủ tuyệt đối.
3. Sửa từng lỗi A/B; ghi trước--sau và lý do trong
   `corrections-v1.4.md`.
4. Không bịa claim để lấp chỗ thiếu. Với thông tin không xác minh được, bỏ
   claim, viết có điều kiện hoặc hướng người đọc tới tài liệu chính thức.
5. Giữ chủ đề, ý định tìm kiếm và phạm vi chính của bài. Nếu sửa làm thay
   đổi chủ đề thì mẫu không còn là cặp GC hợp lệ.
6. Chạy helper tất định cho các mã máy kiểm được, rồi đọc thủ công các mã
   ngữ nghĩa A1--A7/B8/B11 theo guideline.
7. Chỉ ghi `expected_label=publish` khi không còn A/B. Nếu còn một mã B/A,
   tiếp tục sửa hoặc ghi mẫu chưa sẵn sàng; không hạ tiêu chuẩn để đủ 20.

Các claim kỹ thuật, chính sách hoặc an toàn có khả năng thay đổi phải được
đối chiếu nguồn chính thức tại ngày hiệu đính. Nguồn và ngày truy cập đi vào
nhật ký; không dùng trí nhớ của model làm nguồn.

## 8. Quy trình tạo 11 CV

1. Chọn parent `GC/C` đã qua cổng publish và phù hợp ngữ nghĩa với mã cần
   chèn.
2. Thay đổi tối thiểu phần cần thiết để tạo đúng một mã mục tiêu; giữ các
   field khác bất biến trong khả năng hợp lý.
3. Ghi đoạn trước--sau, căn cứ mã, parent và checksum vào
   `coverage-changes-v1.4.md`.
4. Chạy rà toàn bộ A1--A7/B1--B11. Nếu có mã ngoài mục tiêu, mẫu thất bại
   kiểm soát và phải làm lại trước khi khóa manifest.
5. Parent sạch là đối chứng âm; CV là ca dương. Cả hai luôn đi cùng nhau
   khi báo cáo.

Ràng buộc riêng:

- A3 phải có một giá trị sai có thể đối chiếu với công bố chính thức và ghi
  rõ giá trị đúng; không chọn ca nguồn chính thức tự mâu thuẫn.
- A5 phải làm body không trả lời được câu hỏi ở title và cần viết lại trên
  50%, không chỉ thêm một đoạn lạc đề ngắn.
- A6 phải mô phỏng hướng dẫn có nguy cơ rõ ràng nhưng không được trình bày
  tách khỏi ngữ cảnh test như lời khuyên thật; evidence lưu kèm hướng dẫn
  chính thức.
- A7 phải là văn xuôi có nghĩa bị ẩn khỏi người đọc nhưng có trong exact
  input evaluator; CSS/tracking/URL/marker kỹ thuật không đủ.
- B6 áp dụng cho ảnh trong `body`, không bịa field ảnh đại diện không tồn tại.
- B7 phải vi phạm `url_alias`: còn dấu, thiếu từ khóa chính hoặc dài trên 75
  ký tự; không nhầm với độ dài title.
- B9 phải trên 500 tiếng theo `len(text.split())` và thiếu H2; H3 không thay
  thế H2.

## 9. Chỉ số và cách báo cáo

### 9.1. Bộ chính 63 mẫu

- confusion matrix ba lớp;
- precision, recall, F1 từng lớp và macro-F1;
- balanced accuracy; không dùng accuracy một mình;
- `false_publish_rate_gold = gold cần chặn nhưng dự đoán publish / 33`;
- `publish_recall_corrected = corrected dự đoán publish / 30`;
- `false_block_rate_corrected = corrected không publish / 30`;
- `paired_recovery_rate = số cặp G bị chặn và GC publish / 20`;
- số `manual_review`, `incomplete_assessment` và coverage failure;
- kết quả riêng theo `gold-real`, `gold-pert`, `functional-clean` và
  `gold-corrected`.

Kappa chỉ được báo trên lát có ground truth phù hợp và kèm provenance/giới
hạn nhãn. Không gộp `C/GC` synthetic vào Kappa chính như thể là nhãn publish
độc lập.

### 9.2. Bộ coverage 11 mẫu

Mỗi CV báo:

- có finding đúng `target_code` hay không;
- có ra đúng `expected_label` hay không;
- parent sạch có tiếp tục `publish` hay không;
- có finding chặn ngoài mục tiêu hay không;
- evidence có trỏ đúng đoạn được chèn hay không.

Kết quả là bảng pass/fail từng mã. Không tính 11 CV vào điểm tổng của 63 và
không dùng chúng để chọn ngưỡng sau khi xem output.

## 10. Chống leakage và optional stopping

- Khóa manifest, checksum, guideline, rubric, prompt/policy hash và parent
  mapping trước lượt pipeline đầu tiên.
- Không chia parent và child sang các fold khác nhau.
- Không resume output v1 vào run v2.
- Không thêm/xóa mẫu vì một metric vừa trượt. Lỗi dữ liệu thật phải có bản
  manifest mới, changelog và báo cả kết quả cũ lẫn mới.
- Không huấn luyện prompt/rule bằng chính câu chữ CV rồi báo CV như test độc
  lập. CV là regression/coverage evidence, không phải holdout.

## 11. Điều kiện để phép đo chạy được

Trước lượt offline/runtime:

- 20 GC đủ file, đủ manifest, checksum đúng và không còn A/B;
- 11 CV đủ file, đúng một target code và parent sạch;
- runner đọc riêng từng manifest và không cho `C/GC/CV` lọt vào E5 v1;
- policy/rubric/guideline/prompt version khớp exact release;
- output lưu criteria/finding chi tiết, không chỉ lưu score và boolean
  `critical`;
- test parser/manifest/metric/grouping đều xanh.

Trước lượt API trả phí:

- commit protocol là tổ tiên của commit chứa kết quả;
- ghi HEAD, policy hash, prompt version, model, KB/embedding provenance;
- file output mới chưa tồn tại hoặc resume metadata khớp tuyệt đối;
- chủ dự án xác nhận riêng chi phí cho đúng lượt chạy.

Không đáp ứng một cổng thì dừng trước paid path; không suy kết quả từ
preflight.

## 12. Điều kiện đóng hạng mục đánh giá v2

### 12.1. Mức A -- đã đo xong về kỹ thuật

Hạng mục nghiệm thu kỹ thuật v2 được coi là **đã đo xong**, bất kể đạt hay
trượt, khi có đủ:

1. evidence offline về integrity của 63 + 11 mẫu;
2. kết quả stability cho release v2 theo protocol đã khóa;
3. confusion matrix và metric bộ chính 63, tách đúng bốn lát dữ liệu;
4. bảng pass/fail 11 CV theo target code;
5. báo cáo 20 cặp `G -> GC`;
6. provenance chi phí/model/prompt/policy/KB/commit;
7. danh sách giới hạn, gồm synthetic publish và thiếu đồng thuận độc lập trên
   bài publish tự nhiên;
8. quyết định cutover hoặc không cutover dựa trên cổng đã đăng ký trước.

`Đã đo xong` không đồng nghĩa `đạt`. Nếu metric trượt, dự án có kết luận kỹ
thuật rõ và danh sách lỗi cần xử lý; không được đổi dữ liệu để tuyên bố đạt.

### 12.2. Mức B -- đạt cổng limited pilot trên corpus hiện tại

Các cổng đã có trong plan policy v2 được giữ nguyên và mở rộng cho dữ liệu
mới:

- decision consistency E1 >= 90%;
- Kappa quyết định trên 33 gold >= 0,60, kèm đúng giới hạn của nhãn;
- recall `rejected` >= 0,80;
- recall `needs_revision` >= 0,80;
- false-publish trên gold = 0/33;
- corrected publish = 30/30;
- paired recovery = 20/20;
- 11/11 CV tìm đúng target code và ra đúng decision;
- parent sạch của 11 CV vẫn `publish`;
- không có coverage failure hoặc mismatch version.

Đây là gate limited pilot trên chính corpus này, không phải tuyên bố hiệu
năng ngoài thực tế. Nếu một gate trượt, release v2 không được sửa tại chỗ;
phân tích nguyên nhân, phát hành candidate version mới và giữ evidence trượt.

### 12.3. Mức C -- bằng chứng độc lập đầy đủ

Muốn nói bộ nhãn có độ tin cậy độc lập hoặc AI đồng thuận với người trên lớp
publish thật, phải bổ sung dữ liệu/người gán độc lập theo protocol đăng ký
trước. Với lựa chọn hiện tại, mức này mang trạng thái
`not_demonstrated`, không phải `failed` và cũng không phải `passed`.

Vì vậy “xong dự án” phải ghi rõ mức nào:

- **Mức A:** có thể hoàn tất bằng thiết kế hiện tại dù kết quả đẹp hay xấu;
- **Mức B:** chỉ hoàn tất nếu toàn bộ gate định lượng ở trên đạt;
- **Mức C:** không thể bảo đảm hoặc tuyên bố từ dữ liệu synthetic hiện tại.

## 13. Rủi ro và giới hạn

- 30 publish đều corrected, không đại diện đầy đủ cho bài sạch tự nhiên.
- 20 `GC` phụ thuộc `G`, nên kích thước hiệu dụng thấp hơn 20 cặp độc lập.
- 11 CV được thiết kế theo taxonomy đã biết; chúng đo coverage chứ không đo
  khả năng tổng quát hoá sang lỗi chưa biết.
- Lượt AI v1.4 đã có nguy cơ neo bởi nhãn cũ; không được mô tả 33/33 khớp là
  bằng chứng đồng thuận độc lập.
- Rejected chính chỉ có 10 mẫu; một lỗi làm recall thay đổi 10 điểm phần
  trăm. Coverage CV giảm khoảng trống cơ chế nhưng không tăng cỡ mẫu tự
  nhiên.
- A3/A6 và claim chính sách có thể đổi theo thời gian; nguồn phải được kiểm
  lại tại ngày tạo mẫu.
- Pipeline gọi LLM không tất định; có dữ liệu đủ lớp không bảo đảm metric sẽ
  vượt cổng stability hoặc accuracy.

## 14. Tiêu chí hoàn tất thiết kế

Design hoàn tất khi chủ dự án xác nhận:

- bốn lớp dữ liệu và việc giữ nguyên 33 gold;
- bộ chính 63 và coverage 11 báo cáo riêng;
- quy tắc parent sạch -> một target code;
- hợp đồng provenance/checksum;
- ranh giới “đo được” khác “đạt” và khác “đồng thuận trên bài thật”;
- không có paid run trong bước tạo spec/dữ liệu.

Sau khi spec được duyệt bằng văn bản, bước kế tiếp là lập implementation plan
theo TDD; chưa được tạo 20 GC/11 CV hoặc sửa runner ngay trong bước design.

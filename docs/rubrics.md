# Rubric chấm điểm 4 agent

**Phiên bản:** rubric v1 (2026-07-27)
**Phạm vi:** bài cẩm nang tiếng Việt về xe điện (P0)
**Trạng thái:** đã triển khai cho **Brand Voice Agent** (2026-08-03); 3 agent còn lại chưa (xem mục 8.1)

> **Nguồn thi hành các con số là `multiagent/config/scoring.yaml`** (khối `scoring`), không phải tài liệu này. Bảng dưới đây giữ nguyên con số để đọc tại chỗ, nhưng khi hai bên lệch nhau thì file config đúng - và đó là lỗi cần sửa ngay, xem `docs/config-spec.md`.

---

## 1. Vấn đề tài liệu này giải quyết

Thiết kế hiện tại yêu cầu mỗi agent trả về `score: 0-100`, nhưng **không chỗ nào định nghĩa 85 khác 70 ở điểm gì**. Nhìn `multiagent/src/agents/seo.py`: system prompt liệt kê 5 tiêu chí, JSON schema đòi một số nguyên, còn thang điểm thì LLM tự phát minh cho mỗi lần gọi.

Hệ quả trực tiếp lên deliverable quan trọng nhất của dự án:

1. **Điểm không tái lập được.** `temperature=0` giảm dao động nhưng không định nghĩa được thang điểm vốn không tồn tại. Calibrate ngưỡng (mục 8.2 `architecture.md`) trên một đại lượng trôi nổi thì ngưỡng thu được cũng trôi nổi - Kappa đo ra có thể chỉ là nhiễu.
2. **Mâu thuẫn nội bộ.** Dự án đã lập luận rằng Aggregator phải tất định, vì "để LLM tự phán điểm tổng thì chạy hai lần ra hai kết quả" (`architecture.md` mục 6). Lập luận đó đúng, nhưng nó áp dụng y hệt cho điểm của từng agent - chỗ hiện đang để LLM tự phán.
3. **Vi phạm chính nguyên tắc của đề tài.** Dự án đặt ra "không có ngưỡng nào là số ảo" và đã làm rất kỹ với trọng số, với ngưỡng 80/50. Nhưng điểm đầu vào của những ngưỡng đó lại là số ảo.

**Nguyên tắc sửa:** LLM làm việc nó làm tốt - **phân loại theo mô tả rõ ràng**; không làm việc nó làm kém - **cho điểm số tuyệt đối trên thang liên tục**. Điểm số do một hàm tất định tính ra từ các mức phân loại đó.

```
Trước:  nội dung ──LLM──> score 0-100                (không tái lập)
Sau:    nội dung ──máy───> mức từng tiêu chí ─┐
                 ──LLM───> mức từng tiêu chí ─┴──hàm tất định──> score
```

---

## 2. Cấu trúc chung

### 2.1. Mức đánh giá

Mỗi tiêu chí chấm theo **3 mức**, hoặc **nhị phân** khi không có trạng thái trung gian có nghĩa:

| Mức | Nghĩa |
|---|---|
| `2` | Đạt |
| `1` | Đạt một phần (chỉ dùng khi mô tả được cụ thể "một phần" là gì) |
| `0` | Không đạt |
| `NA` | Tiêu chí không áp dụng cho bài này |

### 2.2. Công thức tính điểm agent

```
score = 100 × (tổng mức đạt của các tiêu chí áp dụng)
              ─────────────────────────────────────────
              (2 × số tiêu chí áp dụng)
```

Tiêu chí `NA` bị **loại khỏi cả tử số lẫn mẫu số**. Điểm quan trọng: `NA` không được tính là "đạt". Ví dụ bài không nhắc gì tới khuyến mại thì tiêu chí "khuyến mại đủ thời hạn" là `NA` - nếu tính thành đạt, mọi bài không nói về khuyến mại đều được cộng điểm miễn phí, làm tiêu chí đó thành hằng số (đúng lỗi đã nhận diện ở spec mục 7.1).

### 2.3. Mọi tiêu chí trọng số bằng nhau ở v1

Chưa có căn cứ khách quan nào để nói "thiếu meta description" hại hơn hay kém "slug thiếu từ khóa" bao nhiêu lần. Đặt trọng số chênh lệch lúc này là đưa số ảo vào đúng chỗ vừa dọn xong. Giữ bằng nhau, và để việc phân định cho calibration Sprint 3 - cùng cách xử lý đã dùng cho cặp Content = Brand = 0.25 ở `architecture.md` mục 6.1.

Ánh xạ tiêu chí ↔ mã lỗi (cột cuối mỗi bảng) là cơ sở sẵn có để suy trọng số về sau: nếu dữ liệu cho thấy nhóm lỗi nào ảnh hưởng nhãn của người mạnh hơn, trọng số tiêu chí tương ứng tăng theo.

### 2.4. Đo bởi máy hay LLM

Mỗi tiêu chí ghi rõ **`máy`** hoặc **`LLM`**:

- **`máy`** - đếm được bằng code (độ dài ký tự, số từ, regex, parse HTML, so khớp danh sách thuật ngữ). Không gọi LLM: kết quả tất định tuyệt đối, miễn phí, không dao động.
- **`LLM`** - cần hiểu ngữ nghĩa (từ khóa xuất hiện *tự nhiên* không, alt text *mô tả đúng* ảnh không, claim có *thiếu điều kiện đo* không).

Khoảng 40% tiêu chí đo được bằng máy. Việc tách này giảm chi phí gọi LLM, giảm dao động điểm, và chính là phần hiện thực cụ thể của interface `LanguageAnalyzer` đã hứa ở `architecture.md` mục 5.6.

### 2.5. Bắt buộc trích dẫn bằng chứng

Với mọi tiêu chí LLM chấm mức `0` hoặc `1`, output **bắt buộc** có `evidence` - đoạn trích **nguyên văn** từ bài viết. Không trích được nguyên văn thì không được hạ mức.

Đây là cơ chế chống bịa: LLM khó khẳng định khống một lỗi khi buộc phải chỉ ra nó nằm ở đâu, và người gán nhãn kiểm chứng được ngay bằng Ctrl+F.

---

## 3. Content Quality Agent

Đọc: `title`, `body`, `summary`. Tối đa 8 tiêu chí × 2 = **16 điểm**.

| Mã | Tiêu chí | Đo | `0` | `1` | `2` | Mã lỗi |
|---|---|---|---|---|---|---|
| **CQ1** | Chính tả | LLM | ≥3 lỗi | 1-2 lỗi | Không lỗi | B8 |
| **CQ2** | Ngữ pháp, câu tối nghĩa | LLM | ≥3 câu | 1-2 câu | Không | B8 |
| **CQ3** | Câu quá dài (>30 từ) | máy | ≥3 câu | 1-2 câu | Không | B9 |
| **CQ4** | Đoạn quá dài (>5 câu) | máy | ≥3 đoạn | 1-2 đoạn | Không | B9 |
| **CQ5** | Cấu trúc heading | máy | Bài >500 từ, không có `<h2>` | Có `<h2>` nhưng phân cấp lộn xộn (h3 trước h2) | Có và đúng phân cấp | B9 |
| **CQ6** | Mạch lạc, không trùng lặp | LLM | Có đoạn lặp ý rõ rệt hoặc lạc đề | Lặp nhẹ | Không | - |
| **CQ7** | Số liệu định lượng có nguồn | LLM | Có số liệu không nguồn | Một phần có nguồn | Mọi số liệu có nguồn | B10 |
| **CQ8** | `summary` (teaser) | máy + LLM | Trống *(máy)* | Có nhưng không tóm đúng nội dung *(LLM)* | Có và tóm đúng | - |

**Ghi chú CQ3/CQ4:** ngưỡng 30 từ / 5 câu lấy từ `architecture.md` mục 5.5, hiện là **giá trị tạm** chờ calibrate từ gold set. Tách câu tiếng Việt không cắt thô theo dấu chấm (số thập phân "3.5 giây", viết tắt "TP.HCM") - quy tắc tách nằm ở `LanguageAnalyzer`.

**Cố ý không có tiêu chí "readability".** Flesch-Kincaid đếm âm tiết theo quy tắc tiếng Anh, không áp dụng được cho tiếng Việt (`architecture.md` mục 5.5). CQ3/CQ4 là phần *đo được* của khái niệm đó; phần còn lại bỏ, không thay bằng cảm nhận của LLM.

---

## 4. SEO Agent

Đọc: `title`, `meta_description`, `url_alias`, `body`, `image_alt`. Tối đa 10 tiêu chí × 2 = **20 điểm**.

| Mã | Tiêu chí | Đo | `0` | `1` | `2` | Mã lỗi |
|---|---|---|---|---|---|---|
| **SEO1** | Độ dài `title` | máy | <40 hoặc >70 ký tự | 40-49 hoặc 61-70 | 50-60 | B4 |
| **SEO2** | `title` chứa từ khóa chính | LLM | Không | - | Có | - |
| **SEO3** | `meta_description` tồn tại & độ dài | máy | Trống | Có, ngoài 140-170 ký tự | 140-170 ký tự | B3 |
| **SEO4** | `meta_description` chứa từ khóa | LLM | Không | - | Có | B3 |
| **SEO5** | Chất lượng `url_alias` | máy + LLM | Trống, hoặc còn dấu tiếng Việt *(máy)* | Hợp lệ nhưng >75 ký tự hoặc thiếu từ khóa *(LLM)* | Ngắn gọn, không dấu, có từ khóa | B7 |
| **SEO6** | Từ khóa chính trong 100 từ đầu `body` | LLM | Không | - | Có | - |
| **SEO7** | Độ dài `body` | máy | <300 từ | 300-599 từ | ≥600 từ | - |
| **SEO8** | Heading mang từ khóa | máy + LLM | Không có `<h2>` *(máy)* | Có `<h2>` nhưng không heading nào chứa từ khóa/biến thể *(LLM)* | Có, ít nhất 1 heading chứa từ khóa | - |
| **SEO9** | `image_alt` | máy + LLM | Trống *(máy)* | Có nhưng chung chung ("hình ảnh", "anh1") *(LLM)* | Mô tả đúng nội dung ảnh | B6 |
| **SEO10** | Internal link | máy | Không có | 1-2 link | ≥3 link | C3 |

**Từ khóa chính** do LLM rút ra từ `title` (giữ nguyên trường `main_keyword` đang có trong output hiện tại) và dùng chung cho SEO2/4/6/8 - phải nhất quán trong cùng một lần chấm.

**Mật độ từ khóa (keyword density) không có trong rubric v1.** Đo đúng mật độ cần tách từ tiếng Việt (`underthesea`), chưa có trong `requirements.txt`. Quan trọng hơn: chưa có căn cứ nào cho biết mật độ bao nhiêu là "đúng" với bài cẩm nang tiếng Việt - thêm tiêu chí này bây giờ sẽ phải bịa một ngưỡng. Thay vào đó SEO6/SEO8 kiểm **vị trí** từ khóa (đầu bài, trong heading) - đo được và không cần ngưỡng bịa. Ghi nhận là hạng mục mở rộng sau khi có gold set.

**Ghi chú SEO10:** annotation guideline xếp "ít internal link nhưng vẫn có" vào nhóm C (không bắt buộc sửa), trong khi rubric vẫn trừ điểm ở mức `1`. Đây là chênh lệch **có chủ đích** giữa điểm số và nhãn - xem mục 7.

**Ghi chú SEO9 - phạm vi hiện tại KHÔNG khớp với mã lỗi B6:** rubric ghi `image_alt` (số ít, một ảnh đại diện) vì đó là những gì `drupal_client.py` đọc được từ `relationships.field_image`. Nhưng mã lỗi B6 trong `annotation-guideline.md` v1.2 xét **mọi ảnh trong `body`**. Hai bên đo hai tập ảnh khác nhau, nên Recall/F1 của SEO9 sẽ lệch có hệ thống nếu calibrate trước khi sửa. Đây **không** phải chênh lệch có chủ đích như SEO10 - đây là hạng mục còn thiếu, phải xong trước E5. Bằng chứng đo được (2026-07-30, bài `node/7` có 1 ảnh trong body thiếu alt lọt lưới hoàn toàn): `docs/evaluation-plan.md` mục 4.5 điều kiện 4.

---

## 5. Brand Voice Agent

Đọc: `title`, `body`, `summary`, đối chiếu `brand_guideline.md` truy xuất qua RAG. Tối đa 7 tiêu chí × 2 = **14 điểm**.

| Mã | Tiêu chí | Đo | `0` | `1` | `2` | Mã lỗi |
|---|---|---|---|---|---|---|
| **BV1** | Cách viết tên model | máy | ≥3 chỗ sai | 1-2 chỗ sai | Đúng chuẩn toàn bài | B5 |
| **BV2** | Thuật ngữ chuẩn | máy | ≥3 chỗ dùng biến thể không chuẩn | 1-2 chỗ | Chuẩn toàn bài | B5 |
| **BV3** | Xưng hô nhất quán trong bài | máy | Lẫn ≥3 cách xưng hô | Lẫn 2 cách | Nhất quán | B5 |
| **BV4** | Xưng hô khớp chuẩn corpus | máy | Không dùng cách phổ biến nhất trong corpus | - | Có | B5 |
| **BV5** | Quy ước viết hoa `title` | máy | VIẾT HOA TOÀN BỘ | Viết hoa không nhất quán | Đúng quy ước | B4 |
| **BV6** | Mức độ trang trọng | LLM | Lệch rõ so với corpus | Hơi lệch | Khớp | - |
| **BV7** | Không dùng từ bị guideline loại | máy | Có | - | Không | B5 |

**BV1-BV5, BV7 đo bằng máy** vì brand guideline được trích xuất từ corpus dưới dạng **danh sách cụ thể** (`"VF 8"` chuẩn / `"VF8"`, `"vf8"` sai; `"ô tô điện"` chuẩn / `"xe hơi điện"` sai) - so khớp regex chính xác hơn và rẻ hơn nhiều so với hỏi LLM. RAG chỉ thực sự cần cho **BV6**, tiêu chí duy nhất đòi hiểu ngữ cảnh.

> Đây là dữ kiện đáng chú ý cho quyết định kiến trúc: **6/7 tiêu chí Brand Voice không cần RAG.** Cần cân nhắc lại trong tài liệu thiết kế RAG xem có nên dựng vector store cho một tiêu chí duy nhất hay không, hay chỉ cần nạp thẳng phần "giọng văn" của guideline vào prompt.

**Mọi ngưỡng đếm ở đây (3 chỗ, 2 cách) là tạm**, chờ calibrate. Riêng BV4 phải kèm được số liệu chứng minh từ corpus (kiểu *"92% bài dùng 'ô tô điện'"*) - đúng yêu cầu ở spec mục 6.4.

---

## 6. Compliance Agent

Đọc: `title`, `body`, `meta_description`. Tối đa 8 tiêu chí × 2 = **16 điểm**.

**Thay đổi lớn nhất so với hiện tại: Compliance Agent không tự cho điểm nữa, và không tự chọn severity nữa.**

| Mã | Tiêu chí | Đo | `0` | `1` | `2` | Severity khi `0` | Mã lỗi |
|---|---|---|---|---|---|---|---|
| **CP1** | Không có claim tuyệt đối/so sánh nhất ("số 1", "tốt nhất", "duy nhất") | máy | Có | - | Không | **critical** | A1 |
| **CP2** | Không so sánh trực tiếp hơn hẳn đối thủ cụ thể | LLM | Có | - | Không | **critical** | A2 |
| **CP3** | Số liệu khớp thông số VinFast công bố | LLM + RAG | Có sai lệch | Không kiểm chứng được (không có trong KB) | Khớp | **critical** | A3 |
| **CP4** | Khuyến mại nêu đủ thời hạn & điều kiện | LLM | Thiếu | - | Đủ | **critical** | A4 |
| **CP5** | Claim tầm hoạt động có điều kiện đo (NEDC/WLTP) | LLM | Thiếu hoàn toàn | Có lưu ý chung nhưng không nêu chuẩn đo | Nêu rõ chuẩn đo | medium | B1 |
| **CP6** | Claim thời gian sạc nêu loại trụ & dải % | LLM | Thiếu cả hai | Nêu một trong hai | Nêu đủ | medium | B2 |
| **CP7** | Chính sách pin/thuê pin nêu đủ điều kiện, phí, thời hạn | LLM | Thiếu ≥2 yếu tố | Thiếu 1 yếu tố | Đủ | medium | - |
| **CP8** | Số liệu định lượng có nguồn | LLM | Có số liệu không nguồn | Một phần | Đủ nguồn | low | B10 |

### 6.1. Vì sao bỏ việc LLM tự cho điểm và tự chọn severity

Compliance là agent **rủi ro cao nhất** và cũng là agent duy nhất có quyền phủ quyết. Đúng chỗ đó lại đang có hai phán đoán tự do của LLM:

1. `score` do LLM tự đặt, không định nghĩa - và hiện **không liên quan gì tới `flags`**. Nhìn `compliance.py`: `score` lấy nguyên từ LLM, còn flags rule-based cộng thêm vào sau. Một bài dính 3 flag `critical` từ blacklist vẫn có thể mang `score = 95`.
2. `severity` do LLM tự chọn trong `enum ["low","medium","critical"]`. Vì `critical` kích hoạt veto, đây là quyết định **chặn hay không chặn xuất bản** đang được giao cho một phán đoán không tái lập.

Với rubric này, cả hai thành tất định: điểm tính bằng công thức mục 2.2, severity tra bảng theo mã tiêu chí. LLM chỉ còn làm đúng một việc - **phát hiện xem bài có dấu hiệu vi phạm loại đó không, kèm trích dẫn nguyên văn**.

Rule-based blacklist hiện có (`compliance_rules.json`) trở thành **cách đo của CP1** thay vì một nguồn flag song song, nên không còn tình huống flags và score mâu thuẫn nhau.

### 6.2. Quy tắc veto giữ nguyên

Bất kỳ tiêu chí `critical` nào ở mức `0` → sinh flag `severity: critical` → Aggregator veto → `rejected`, độc lập với điểm tổng (`architecture.md` mục 6.2). Không đổi gì ở tầng Aggregator.

**CP3 mức `1` ("không kiểm chứng được") cố ý KHÔNG phải critical.** Knowledge base fact-check chỉ có thông số của một số model; một claim không tra được trong KB không có nghĩa là sai. Coi nó là critical sẽ khiến mọi bài nhắc tới model ngoài KB đều bị từ chối - lỗi hệ thống, không phải lỗi nội dung.

---

## 7. Quan hệ giữa rubric và nhãn của người - chênh lệch có chủ đích

Hai thang đo này **cố ý không đồng nhất**:

| | Rubric (máy chấm) | Annotation guideline (người gán nhãn) |
|---|---|---|
| Đầu ra | Điểm 0-100 mỗi agent | 1 trong 3 nhãn |
| Lỗi nhỏ cộng dồn | **Có** - nhiều lỗi nhỏ kéo điểm xuống | **Không** - 8 lỗi nhóm B vẫn là `needs_revision` |

Lý do khác nhau: ground truth tuyệt đối không được chứa ngưỡng đếm bịa ra (`annotation-guideline.md` mục 5), còn điểm số thì bản chất là thang liên tục nên cộng dồn là tự nhiên.

**Chính khoảng chênh giữa hai thang này là đối tượng đo của calibration Sprint 3.** Việc chọn ngưỡng 80/50 chính là việc tìm điểm cắt trên thang liên tục sao cho khớp nhất với nhãn rời rạc của người. Nếu ép hai thang giống hệt nhau từ đầu thì không còn gì để calibrate - và quan trọng hơn, sẽ là tự đặt trước đáp án cho phép đo.

Cột "Mã lỗi" trong mọi bảng rubric ánh xạ về bảng mã lỗi ở `annotation-guideline.md` mục 4. Nhờ đó Sprint 3 so được **cả lý do**, không chỉ nhãn cuối: AI hạ mức CP5 mà người cũng ghi B1 → đồng thuận thật; trùng nhãn nhưng khác mã lỗi → trùng ngẫu nhiên, cần xem lại.

---

## 8. Ảnh hưởng lên code (chưa triển khai)

Rubric v1 chưa vào code. Khi triển khai, các chỗ phải sửa:

| File | Thay đổi |
|---|---|
| `src/agents/*.py` | Output schema: bỏ `score`, thay bằng `criteria: [{id, level, field, evidence, suggestion}]`. System prompt: thay danh sách tiêu chí bằng bảng mức của rubric |
| `src/scoring.py` *(mới)* | Hàm tất định: `criteria → score` theo công thức mục 2.2; tra bảng severity cho Compliance |
| `src/analyzers/` *(mới)* | `LanguageAnalyzer` - phần tiêu chí đo bằng máy (đếm ký tự/từ/câu, parse HTML, regex thuật ngữ) |
| `src/agents/compliance.py` | `compliance_rules.json` trở thành cách đo CP1, không còn là nguồn flag song song |
| `src/graph.py` | Aggregator nhận `score` đã tính sẵn - logic trọng số và veto **không đổi** |
| `scripts/` | Test cho `scoring.py`: cùng bộ `criteria` phải luôn ra cùng điểm; `NA` bị loại khỏi mẫu số |

Không thay đổi: kiến trúc 8 node, cơ chế veto, công thức trọng số Aggregator, cách ghi ngược Drupal.

### 8.1. Trạng thái triển khai (2026-08-03)

Rubric **đã vào code cho Brand Voice Agent** — agent đầu tiên chấm theo mức `0/1/2/NA` và tính điểm tất định:

| File | Trạng thái |
|---|---|
| `src/scoring.py` | ✅ `score_from_criteria()` theo đúng công thức mục 2.2. Phần "tra bảng severity cho Compliance" **chưa làm** |
| `src/agents/brand_voice.py` | ✅ BV1–BV7, output `criteria: [{id, level, occurrences, suggestion, reference}]` |
| `src/brand_analysis.py`, `src/text_utils.py` | ✅ phần "đo bằng máy" của BV1–BV5, BV7 (thay cho `src/analyzers/` dự kiến) |
| `src/agents/{content_quality,seo,compliance}.py` | ❌ **vẫn để LLM tự cho `score`** |
| `src/graph.py` | ✅ Aggregator nhận `score` đã tính sẵn, logic trọng số và veto không đổi — đúng như dự kiến |

**Số liệu đầu tiên cho mục 9.** 6/7 tiêu chí Brand Voice là regex nên chấm lại cùng bài **luôn ra cùng điểm** — kiểm bằng `scripts/test_brand_voice.py` (chạy 5 lần, σ = 0). Chưa so được với thang 0-100 vì Brand Voice không có bản cũ; phép so sánh phương sai đầy đủ cần E1 trên 3 agent còn lại.

**Hai lỗi "điểm miễn phí" phát hiện khi triển khai**, đều là biến thể của đúng vấn đề mục 2.2 cảnh báo, đáng ghi lại vì dễ tái diễn khi làm 3 agent kia:

1. **Thoả mãn rỗng.** BV7 ("không dùng từ bị loại") cho mức `2` với bài không hề bàn tới khái niệm ấy — mọi bài ngắn/lạc chủ đề được cộng điểm miễn phí. Sửa: không nhắc khái niệm → `NA`. **Quy tắc rút ra: tiêu chí dạng phủ định chỉ được tính ĐẠT khi bài thật sự có cơ hội vi phạm.**
2. **Phân loại quá rộng.** Hàm phân loại kiểu viết hoa xếp tiêu đề toàn chữ thường vào `SENTENCE_CASE`, khiến tiêu đề `"test"` được chấm đạt quy ước. Sửa: tách lớp `LOWERCASE`.

---

## 9. Những gì còn để trống chờ đo

Rubric này chốt **cấu trúc và cách chấm**, không chốt các con số phải suy ra từ dữ liệu:

| Chỗ để trống | Đo bằng gì |
|---|---|
| Ngưỡng đếm trong rubric (30 từ/câu, 5 câu/đoạn, 3 chỗ sai, 140-170 ký tự...) | Calibration từ gold set, Sprint 3 |
| Trọng số giữa các tiêu chí trong cùng agent | Calibration - hiện bằng nhau (mục 2.3) |
| Độ ổn định thực tế của mức LLM chấm | Thí nghiệm test-retest: chạy cùng bài N lần, đo tỉ lệ mức trùng nhau. **Phải làm trước khi tin bất kỳ điểm nào** |
| Rubric có thật sự ổn định hơn thang 0-100 không | So sánh phương sai điểm giữa rubric v1 và cách chấm hiện tại, trên cùng bộ mẫu |

Mục cuối đáng nhấn: rubric này được thiết kế theo lập luận, **chưa được chứng minh bằng số liệu là tốt hơn**. Thí nghiệm so sánh phương sai là bước xác nhận, và cũng là một kết quả nghiên cứu đáng đưa vào báo cáo cuối - dù kết quả ra theo hướng nào.

---

## 10. Phiên bản

Ngưỡng quyết định chỉ có hiệu lực với đúng bộ **(rubric version, phiên bản prompt, model)** đã dùng khi calibrate. Đổi bất kỳ yếu tố nào trong ba yếu tố đó đều phải calibrate lại - ghi rõ vì `ANTHROPIC_MODEL` hiện đọc từ biến môi trường nên có thể đổi mà không ai để ý.

# PHẦN 5: BÁO CÁO SPRINT 2

**Cập nhật:** 2026-08-07

## 1. Mục tiêu Sprint 2

Theo lộ trình 3 sprint đã được mentor duyệt ([`roadmap.md`](roadmap.md)), Sprint 2 có 6 mục tiêu:

1. Xây Brand Voice Agent dùng RAG, với brand guideline tự trích xuất từ corpus công khai.
2. Xây Compliance Agent / Fact-check.
3. Hoàn thiện logic tổng hợp điểm của Aggregator.
4. Thu thập và gán nhãn gold set 30–50 mẫu.
5. Tự động hóa: bật Content Moderation "Needs Review" + polling worker.
6. Dựng UI báo cáo trong giao diện editor.

**Hiện trạng: 5 mục xong, 1 mục chưa.**

---

## 2. Đã xong

### 2.1. Brand Voice Agent dùng RAG

Dự án không được cấp tài liệu brand nội bộ, nên brand guideline được **suy ra từ dữ liệu**: thống kê các quy ước lặp lại trên 16 bài cẩm nang đã đăng, rồi dùng **kiểm định nhị thức** để chốt. Một quy ước chỉ thành quy tắc khi lệch khỏi 50-50 ở mức có ý nghĩa thống kê (p < 0,05) — nên ngưỡng không phải con số tự đặt mà tự rơi ra từ phép kiểm.

Quy ước nào chưa đủ căn cứ thì tiêu chí tương ứng trả `NA` (loại khỏi cả tử số lẫn mẫu số), **không** cho 0 điểm. Đây không phải trường hợp lý thuyết: corpus cho thấy VinFast **không có quy ước xưng hô thống nhất** (16 bài chia phiếu `người dùng` 8 / `bạn` 4 / `khách hàng` 3 / `quý khách` 1), nên tiêu chí BV4 luôn `NA` ở phạm vi hiện tại.

Agent chấm theo 7 tiêu chí BV1–BV7; 6/7 đo bằng regex, chỉ BV6 (mức độ trang trọng) cần gọi LLM + RAG. Nhờ vậy khi API lỗi thì agent vẫn chấm được 6 tiêu chí còn lại thay vì mất trắng.

- Brand guideline sinh tự động, mỗi quy tắc kèm số liệu và p-value: [`brand/brand_guideline.md`](brand/brand_guideline.md)
- Code agent: [`multiagent/src/agents/brand_voice.py`](../multiagent/src/agents/brand_voice.py)
- Rubric BV1–BV7 (mục 5): [`rubrics.md`](rubrics.md)
- Thiết kế RAG: [`rag-design.md`](rag-design.md)

### 2.2. Compliance Agent + Fact-check

Chấm theo 8 tiêu chí CP1–CP8, bằng **ba cách đo khác nhau**:

| Cách đo | Tiêu chí |
|---|---|
| Máy (blacklist + regex) | CP1, CP5, CP6 |
| RAG, đối chiếu thông số VinFast công bố | CP3 |
| LLM (một lần gọi chung) | CP2, CP4, CP7, CP8 |

**Điểm và mức nghiêm trọng đều do code tính, không để LLM tự cho.** Lý do: `critical` là thứ kích hoạt quyền phủ quyết, tức nó chính là quyết định *chặn hay không chặn xuất bản*. Để LLM tự chọn thì đúng chỗ quan trọng nhất lại là chỗ bất định nhất — đo được σ = 5,48 trên một bài ở cách chấm cũ.

Nguyên tắc an toàn của CP3: KB chỉ có thông số một số model, nên **"không tra được" ≠ "sai"**. Không tra được → mức 1, cờ `low`; chỉ khi lệch số của **cùng model** mới ra mức 0 và cờ `critical`. Không có nguyên tắc này thì mọi bài nhắc model ngoài KB đều bị từ chối oan.

- Code agent: [`multiagent/src/agents/compliance.py`](../multiagent/src/agents/compliance.py)
- Phần fact-check (CP3): [`multiagent/src/agents/fact_check.py`](../multiagent/src/agents/fact_check.py)
- Rubric CP1–CP8 (mục 6): [`rubrics.md`](rubrics.md)
- Căn cứ pháp lý + thiết kế: [`architecture.md`](architecture.md) mục 5.4

### 2.3. Aggregator

Module tính toán **tất định, không gọi LLM** — điều kiện bắt buộc để calibrate ngưỡng ở Sprint 3, vì chấm lại cùng đầu vào phải ra cùng kết quả.

Hai cơ chế chính:

- **Quyền phủ quyết của Compliance**: điểm Compliance dưới ngưỡng, hoặc có cờ `critical` → `rejected`, bất kể điểm tổng. Khi điểm Compliance vẫn cao mà bị từ chối, hệ thống ghi rõ `veto_reason` để người duyệt không hiểu nhầm.
- **Fail-safe khi agent lỗi**: chia lại trọng số theo các agent còn lại và ghi rõ *"điểm chưa đầy đủ"*, thay vì cho 0 điểm. Riêng Compliance lỗi thì `final_score = null` và không bao giờ tự đề xuất publish — chưa xác minh được rủi ro pháp lý thì không cho qua.

- Code (hàm `aggregator_node`): [`multiagent/src/graph.py`](../multiagent/src/graph.py)
- Thiết kế + căn cứ chọn trọng số và ngưỡng (mục 6): [`architecture.md`](architecture.md)

### 2.4. UI báo cáo trong giao diện soạn bài

Module Drupal `vf_ai_review`: khối tổng quan ở cột phải, và **chú thích lỗi ngay dưới từng field tương ứng** — phần đáp ứng đúng chữ "báo cáo lỗi theo từng field ngay trong giao diện editor" của đề bài.

Module **chỉ đọc**: không tính điểm, không gọi API, không sửa dữ liệu node. Hỏng thì cùng lắm không thấy báo cáo, không thể làm sai dữ liệu đánh giá.

- Code module: [`drupal/web/modules/custom/vf_ai_review`](../drupal/web/modules/custom/vf_ai_review)
- Thiết kế giao diện: [`editor-ui-design.md`](editor-ui-design.md)

### 2.5. Tự động hóa — event-driven + hàng đợi bền Postgres

Hiện đã bật thật Content Moderation "Needs Review" trên content type Article, và pipeline không còn kích hoạt thủ công. Hai đường chạy song song:

- **Đường chính, event-driven.** Module Drupal thứ hai `vf_ai_trigger` (tách khỏi `vf_ai_review` vì module kia cam kết chỉ đọc) bắt sự kiện chuyển sang `needs_review`, tự chặn ở tầng so `content_hash` trước khi gọi service để Save lặp lại không tốn tiền, rồi POST job sang service HTTP (`multiagent/src/api.py`). Đo thật: từ Save tới lúc job chuyển `running` mất **1,6 giây**, tới lúc có kết quả đầy đủ mất **~15,8 giây** (`docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 1).
- **Lưới an toàn, đối soát định kỳ.** Worker quét mỗi 300 giây, bắt các bài lọt đường event (ví dụ service tắt tạm thời). Đo thật: tắt service, Save một bài, bật lại service - đối soát bắt được sau **~3 phút 28 giây**, trong ngưỡng ≤5 phút (tiêu chí 2).

**Vì sao chọn một bảng Postgres làm hàng đợi thay vì dựng Redis/RabbitMQ:** `SELECT ... FOR UPDATE SKIP LOCKED` cho đúng những thứ một message broker cho - nhiều worker không giẫm chân nhau, job không mất khi worker chết, retry có backoff, dead-letter - và đây là mẫu dùng trong sản phẩm thật (pgmq, Oban, River, Solid Queue). Khác biệt so với broker riêng chỉ lộ ra ở quy mô hàng nghìn job/giây; ở đây là vài chục bài/ngày. Thêm một container Redis không giải quyết vấn đề nào ở quy mô này - đúng loại "số ảo" dự án tránh. Postgres cũng đã chạy sẵn cho kho vector từ 2026-08-05, nên chi phí biên gần như bằng không. Chi tiết: spec `2026-08-07-needs-review-automation-design.md` mục 2 quyết định Q1.

**Vì sao vẫn giữ cả hai đường thay vì chỉ dùng event:** event một mình chỉ đảm bảo *at-most-once* nếu bên gửi không tự retry - một cú POST thất bại là một bài lọt vĩnh viễn mà không ai biết, đúng loại bẫy im lặng dự án dành nhiều công để diệt (B2, B6, B9, B11 ở `technical-debt.md`). Vòng đối soát tốn khoảng 40 dòng, dùng lại đúng khoá idempotency `(node_id, content_hash)` đã phải viết cho việc chặn Save lặp lại, và nó bao trọn luôn deliverable "polling worker" ban đầu của roadmap thay vì bỏ cam kết cũ. Chi tiết: spec cùng file, quyết định Q2.

8/8 tiêu chí hoàn thành đã kiểm tra chạy thật (spec mục 13), toàn bộ 37 file test xanh gồm cả bốn bộ cần container Postgres (`test_job_queue`, `test_audit`, `test_worker`, `test_api`).

- Thiết kế đầy đủ (mục 9): [`architecture.md`](architecture.md)
- Thiết kế chi tiết + 5 quyết định đã chốt: [`superpowers/specs/2026-08-07-needs-review-automation-design.md`](superpowers/specs/2026-08-07-needs-review-automation-design.md)
- Bằng chứng chạy thật end-to-end: [`evidence/tu_dong_hoa_e2e.txt`](evidence/tu_dong_hoa_e2e.txt)

---

## 3. Chưa xong

### 3.1. Gold set — đã thu xong, chưa gán nhãn

**Đã làm:** thu và xử lý 33 mẫu (20 bài thật + 13 bài chèn lỗi có chủ đích), bóc tách sạch phần template dùng chung (header, footer, khối CTA), ghi lại chính xác lỗi nào được chèn vào bài nào.

**Chưa làm:** gán nhãn `publish` / `needs_revision` / `rejected` cho từng mẫu.

**Đây là việc đang chặn toàn bộ Sprint 3** — cả ba phép đo còn lại (calibration ngưỡng, so sánh multi-agent với single-agent, test trên tập held-out) đều cần nhãn làm đáp án chuẩn.

**Một vấn đề phát hiện khi rà lại — ĐÃ XỬ LÝ 2026-08-10, guideline v1.3, chờ mentor xác nhận:** quy tắc quy nhãn hiện tại là *có lỗi nhóm A → `rejected`, có lỗi nhóm B → `needs_revision`, không có gì → `publish`*. Nhưng chạy script đếm trên 33 mẫu thì **cả 33 bài đều dính ít nhất một lỗi nhóm B** — toàn bộ đến từ mã B9 "câu quá dài" (33/33 bài). Nghĩa là gán nhãn xong sẽ **không có bài nào ra nhãn `publish`**, gold set chỉ còn 2 lớp, và ngưỡng publish không có dữ liệu để calibrate.

Đo kỹ thêm thì tìm ra hai điều nữa:

- **B9 gộp 3 tín hiệu nhưng chỉ 1 cái từng kích hoạt.** Câu dài: 33/33. Đoạn dài: 0/33. Thiếu heading: 0/33. Một tiêu chí hoặc luôn đúng hoặc không bao giờ đúng thì phương sai bằng 0, không phân biệt được bài nào với bài nào.
- **6/13 bài perturbation mất tác dụng ở mức nhãn.** Các bản chèn mã B có nhãn giống hệt bài gốc vì bài gốc đã `needs_revision` sẵn do B9 — công chèn lỗi không tạo thêm tín hiệu nào cho calibration nhãn.

Đã kiểm: các câu dài là **câu thật** (dài nhất 70 tiếng, đúng ngữ pháp), không phải lỗi của bộ tách câu.

**Cách xử lý — tránh vòng luẩn quẩn bằng cách không đụng tới ngưỡng.** Rủi ro ban đầu là: lấy dữ liệu để chỉnh chính cái ngưỡng sinh ra đáp án chuẩn. Nên lời giải đã chọn **không chỉnh ngưỡng nào cả** mà phân loại lại tín hiệu: câu dài → **C4**, đoạn dài → **C5** (nhóm C, ghi vào `notes`, không đổi nhãn); riêng "thiếu heading" giữ ở **B9** vì đó là lỗi cấu trúc thật. Ba căn cứ, không căn cứ nào nhìn phân bố nhãn:

1. `needs_revision` định nghĩa là *"lỗi **phải** sửa"*; câu dài là khuyến nghị văn phong, đúng định nghĩa C1.
2. Cả 20 bài thật **đã qua kiểm duyệt thật của đội content VinFast và được đăng** với những câu đó.
3. Guideline v1.1 đã sửa **đúng lỗi cùng loại** cho mã B4 (dùng dải lý tưởng làm ranh giới nhãn → mọi bài dính → phân bố sụp). B9 là mã bị sót trong đợt đó.

Chuyển xuống nhóm C **không mất thông tin nào**: script vẫn đếm và in, người gán vẫn chép vào `notes`, Sprint 3 vẫn đối chiếu được. Thứ duy nhất bị tước là quyền quyết định nhãn.

Phân bố sau khi sửa (chạy lại trên 33 mẫu): **18/33 bài không dính mã đổi nhãn nào**, B9 còn 0/33, C4 33/33. Trần trên của từng lớp — người gán sẽ trừ bớt khi xét tiếp A1–A6, B1, B2, B5, B8, B10:

| Nhãn | Số bài | Từ đâu |
|---|---|---|
| `rejected` | 7 | perturbation chèn mã A |
| `needs_revision` | 13 | 6 perturbation chèn mã B + 7 bài thật dính B3/B4 |
| `publish` | ≤ 13 | 13 bài thật không dính mã máy nào |

Quyết định được chốt **trước** khi gán bất kỳ nhãn nào và trước khi chạy AI trên gold set. Bảng thay đổi đầy đủ: `goldset/annotation-guideline.md` mục 11 (v1.3).

- Bảng 33 mẫu (cột nhãn còn trống): [`goldset/labels.csv`](goldset/labels.csv)
- Quy ước gán nhãn + bảng mã lỗi: [`goldset/annotation-guideline.md`](goldset/annotation-guideline.md)
- Nguồn dữ liệu + cách chia tập BRAND/GOLD/PERT: [`goldset/sources.md`](goldset/sources.md)

---

## 4. Phép đo đã chạy

| Mã | Đo gì | Kết quả |
|---|---|---|
| **E1** | Độ ổn định điểm qua nhiều lần chấm | Đạt ngưỡng — ⚠️ xem cảnh báo dưới |
| **E2** | Retrieval lấy đúng đoạn | Fact-check **1.00**; brand **78,3%** so với mốc ngẫu nhiên **21,7%** |
| **E4** | Chi phí mỗi bài | TB **$0,057**/bài; cả chương trình đến giờ **$8,33** |

**E2 — con số 78,3% là chặn dưới, không phải tỉ lệ thật.** Ground truth chỉ gán một nhóm chủ đề mỗi bài, trong khi nhiều bài thuộc hai nhóm nên bị tính trượt oan. **Không** sửa nhãn để chữa các ca này — sửa sau khi đã nhìn kết quả là tự tạo thiên vị. Báo cáo con số bị đánh giá thấp, lệch về hướng an toàn.

**⚠️ E1 — số hiện có thuộc về code cũ.** Đợt sửa lỗi cuối Sprint 2 (mục 5 dưới đây) làm thay đổi cách chấm điểm Brand Voice, mà Brand chiếm trọng số 0,25 trong điểm tổng. Nên **σ hiện có không còn áp dụng cho code đang chạy**, kể cả σ điểm tổng. Chưa đo lại, và chưa trích vào báo cáo nào.

- Kế hoạch 6 phép đo, thứ tự phụ thuộc, tiêu chí đạt: [`evaluation-plan.md`](evaluation-plan.md)
- Số liệu thô E1/E4: [`evidence/e1_e4_report.txt`](evidence/e1_e4_report.txt), [`evidence/e1_rubric_v2_report.txt`](evidence/e1_rubric_v2_report.txt)

---

## 5. Nợ kỹ thuật đã xử lý trong Sprint 2

Rà lại toàn bộ code cuối sprint, tìm và sửa **6 lỗi**. Mỗi lỗi đều viết test cho fail trước, xác nhận fail đúng lý do, rồi mới sửa.

Hai lỗi đáng kể nhất:

**B8 — hai cụm từ cấm mức `critical` chưa từng bắt được lần nào.** Lỗi biểu thức chính quy khiến `cam kết 100%` và `hiệu quả 100%` không bao giờ khớp. Bộ test cũ vẫn xanh suốt vì không có case nào phủ đúng dạng cụm từ kết thúc bằng ký tự đặc biệt. Đáng lo vì blacklist là cách đo **duy nhất** của CP1, và là thứ vẫn chạy khi LLM bị lừa hoàn toàn.

**B9 — CP3 tin `index` do LLM tự điền.** Index ngoài biên gây lỗi, nhưng lỗi đó bị `try/except` (vốn dựng để KB chưa dựng không làm sập agent) **nuốt mất**, khiến CP3 âm thầm thành `NA`. Mất hẳn tiêu chí fact-check trên đúng đường rủi ro cao nhất của hệ thống, không có dấu hiệu gì. Viết test còn lộ thêm lỗi thứ hai: LLM trả thiếu verdict cho một claim thì bài lên mức 2 trong khi có claim chưa hề được đối chiếu.

Bốn lỗi còn lại: `score` của hai agent không có chặn biên; cache toàn cục bỏ qua tham số đường dẫn; BV6 không thực sự kiểm trích dẫn nguyên văn; và `graph.py` không truyền khoá `(content_type, langcode)` xuống agent.

**Hiện 28/28 bộ test xanh**, không cần API key, không cần Drupal, không cần KB.

- Danh sách đầy đủ kèm bằng chứng đo được: [`technical-debt.md`](technical-debt.md)

---

## 6. Việc tiếp theo

| Thứ tự | Việc | Bị chặn bởi |
|---|---|---|
| 1 | Chốt hướng gán nhãn gold set | **Chờ mentor** |
| 2 | Tiếp tục giảm dao động điểm của Compliance | Không bị chặn, nhưng tốn API và kết quả không chắc |
| 3 | Đo lại E1 | Nên làm **sau** (2), để đo một lần cho cả hai thay đổi |
| 4 | Calibration ngưỡng → so sánh baseline → held-out test | Cần nhãn từ (1) |

## 7. Ba việc cần mentor quyết

1. ~~**Ngưỡng "câu quá dài"** nên để bao nhiêu từ cho bài tiếng Việt — hoặc mã B9 có nên tính vào việc quy nhãn không?~~ → **Đã xử lý 2026-08-10 (guideline v1.3), chỉ cần mentor xác nhận.** Không chỉnh ngưỡng nào (chỉnh sẽ thành vòng luẩn quẩn); thay vào đó chuyển câu dài/đoạn dài xuống nhóm C, giữ "thiếu heading" ở B9. Phân bố nhãn phục hồi về 3 lớp. Chi tiết + 3 căn cứ: mục 3.1.
2. **Cách gán nhãn 33 bài**: gán tay toàn bộ, giảm cỡ mẫu, hay cho phép AI hỗ trợ ở phần liệt kê mã lỗi?
3. **Đo lại E1 ngay hay chờ code ổn định?** Đo lại tốn khoảng vài đô; nếu còn sửa tiếp Compliance thì sẽ phải đo thêm lần nữa.

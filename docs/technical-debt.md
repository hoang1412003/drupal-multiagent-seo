# Nợ kỹ thuật và giới hạn đã biết

**Phiên bản:** v1 (2026-08-04)
**Mục đích:** một chỗ duy nhất liệt kê thứ chưa làm, làm dở, hoặc làm sai — kèm mức độ ảnh hưởng và bằng chứng.

Tài liệu này cũng là bản nháp cho mục **"Giới hạn đã biết"** của báo cáo cuối. Nêu rõ giới hạn mạnh hơn nhiều so với để người chấm tự phát hiện.

**Cách đọc:** mỗi mục ghi *bằng chứng* (đo được ở đâu) chứ không chỉ *nhận định*. Mục nào không có bằng chứng thì ghi rõ là suy luận.

---

## 1. Phân loại

| Nhóm | Nghĩa |
|---|---|
| **A** | Chặn Sprint 3 (calibration) — deliverable quan trọng nhất |
| **B** | Nợ thật: đã gây lỗi, hoặc chắc chắn sẽ gây |
| **C** | Kế hoạch chưa tới lượt — **không phải nợ** |
| **D** | Phép đo chưa chạy |

Phân biệt A/B với C là quan trọng: gộp chung làm bức tranh đáng sợ hơn thực tế. Polling worker chưa làm **không phải nợ** — nó là việc đã lên lịch, chưa tới lượt.

---

## 2. Nhóm A — Chặn Sprint 3

### A1. Ba agent còn để LLM tự cho `score`

**Bằng chứng:** `src/agents/content_quality.py:16`, `seo.py:24`, `compliance.py:77` đều còn `"score": {"type": "integer"}` trong output schema — LLM tự phát minh thang điểm mỗi lần gọi.

**Vì sao chặn:** `docs/rubrics.md` mục 1 lập luận điểm không định nghĩa thì không tái lập được, nên calibrate ngưỡng trên nó cho ra ngưỡng trôi nổi.

**Đã đo bằng E1 (2026-08-04) — 7 bài × 5 lần = 35 lượt chấm.** Kết quả đảo ngược một phần giả thuyết ban đầu:

| Agent | σ điểm | σ lớn nhất trên 1 bài |
|---|---|---|
| content_quality | 0.38 | — |
| seo | 0.19 | — |
| brand *(đã có rubric)* | **0.00** | 0.00 |
| **compliance** | **0.78** | **5.48** |
| **điểm tổng** | **0.28** | — |

**100% số bài giữ nguyên quyết định qua cả 5 lần.** Báo cáo đầy đủ: `docs/evidence/e1_e4_report.txt`, số liệu thô: `docs/evidence/e1_stability_raw.json`.

**Kết luận, thay cho quan sát sơ bộ cũ:**

- Quan sát tình cờ trước đó (`81.75 → 79.25 → 81.75`, dao động 2.5 điểm trên một bài ba lần) **không đại diện**. Nguyên nhân dao động ở lần đó nhiều khả năng là **mức BV6 lật**, không phải nhiễu LLM nói chung — vì brand giờ đã có rubric và đo được σ = 0.00.
- **Ưu tiên A1 với `content_quality` và `seo` hạ xuống.** σ = 0.38 và 0.19 đều nhỏ hơn nhiều so với bước nhảy 2 điểm của E5, nên viết lại rubric cho hai agent này **không còn là điều kiện chặn calibration**.
- **Ưu tiên A1 với `compliance` giữ nguyên mức cao.** σ = 5.48 trên bài G-002 lớn gấp đôi bước nhảy quét ngưỡng. Điều tra nguyên nhân: LLM **tự nghĩ ra nội dung trường `rule`** và **chọn `severity` tuỳ ý** — trên G-002 nó lật giữa "0 flag, score 95" và "2-3 flag mức low, score 85". Đây đúng là loại bất định mà `rubrics.md` mục 1 mô tả.

**Việc phải làm (đã sắp lại theo E1):** làm rubric cho **Compliance trước**, giống Brand Voice — `docs/rubrics.md` mục 8. Hai bẫy đã gặp khi làm Brand Voice, ghi ở mục 8.1 tài liệu đó: *thoả mãn rỗng* và *phân loại quá rộng*. `content_quality` và `seo` chuyển xuống nhóm "nên làm, không chặn".

**Compliance: ✅ đã chuyển sang rubric CP1–CP8 (2026-08-04).** `src/agents/compliance.py` + `src/compliance_analysis.py` + `scoring.severity_for()` + `fact_check.danh_gia()`. LLM không còn tự cho `score`, không còn tự chọn `severity`. Chi tiết ở `rubrics.md` mục 8.1.

**Đo lại sau khi chuyển (50 lượt sạch):** σ `final_score` = **1.33, đạt ngưỡng 2.0** → điều kiện 1 của E5 đạt. Nhưng σ Compliance = **4.18, trượt** — đây là **nợ còn lại**, ghi rõ chứ không giấu:

- Bài nào Compliance dao động mạnh thì ngưỡng E5 calibrate ra kém tin cậy hơn ở vùng đó.
- Nguyên nhân đã chẩn đoán bằng số, không phải đoán: mẫu số trung bình 4.6/8 nên một tiêu chí nhích một bậc là ±16.7 điểm (`rubrics.md` mục 9.1).
- Hướng giảm tiếp đã kiểm chứng được: chuyển thêm tiêu chí sang đo bằng máy. CP2/CP4/CP7 hiện vẫn do LLM chấm và đều cần đọc hiểu, nên không rẻ như CP5/CP6.

**Cảnh báo bắt buộc khi trích bất kỳ σ nào trong dự án này:** σ Brand Voice đi từ `0.00` lên `1.27` giữa hai lần đo **trong khi code Brand không đổi một dòng**. σ = 0 đo trên 5 lượt là may, không phải tính chất.

`content_quality` và `seo`: **vẫn để LLM tự cho điểm** — có chủ ý, xem lại số σ ở bảng trên.

### A2. SEO Agent không đọc `alt` của ảnh nằm trong `body` — ✅ ĐÃ SỬA (2026-08-04)

`_extract_image_alt()` giờ nhận thêm `body_html` và bóc mọi thẻ `<img>` trong thân bài, trả về danh sách nhiều dòng (`Ảnh đại diện: …` / `Ảnh N trong bài: …`); dòng trống sau dấu hai chấm nghĩa là thiếu `alt`. Test: `scripts/test_image_alt.py`.

Kèm theo đã sửa một lỗi regex ở **cả** `drupal_client.py` và `label_helper.py`: `\balt` khớp nhầm cả `data-alt`, tức một ảnh **thiếu** `alt` nhưng có `data-alt` sẽ bị coi là có — bỏ sót lỗi B6. Đổi sang `(?<![\w-])`. Đã kiểm: 0 ảnh trong corpus hiện tại bị ảnh hưởng, nên **không có nhãn nào phải gán lại**.

**Bằng chứng của vấn đề gốc (giữ lại để tra cứu):** `_extract_image_alt()` trước đây chỉ đọc `relationships.field_image.data.meta.alt`. Ảnh nhúng trong chuỗi HTML của `body` không được bóc ra.

**Vì sao chặn:** mã lỗi **B6** trong `docs/goldset/annotation-guideline.md` v1.2 xét **mọi thẻ `<img>` trong `body`**, còn hệ thống chỉ xét **một ảnh đại diện**. Hai bên đo hai tập ảnh khác nhau → Recall/F1 của tiêu chí SEO9 lệch có hệ thống.

Đã ghi ở `docs/evaluation-plan.md` mục 4.5 điều kiện 4, kèm bằng chứng đo trên `node/7` (2026-07-30) và bài `G-001`.

### A3. Gold set chưa gán nhãn

**Trạng thái:** 33 mẫu đã thu, bóc tách, chèn perturbation. Cột `label` trong `docs/goldset/labels.csv` còn trống toàn bộ.

**Chặn bởi:** đang chờ mentor quyết quy trình. Người thực hiện thấy đọc + gán tay 33 bài quá tốn thời gian và đang hỏi mentor: giảm cỡ mẫu, cho phép AI gán nháp, hay giữ nguyên thủ công.

**Lưu ý bắt buộc:** không được dùng AI gán nháp nếu mentor chưa duyệt. `annotation-guideline.md` mục 2 yêu cầu **gán mù**; nhãn do AI nháp sẽ neo người gán và thổi phồng Cohen's Kappa mà cả Sprint 3 dựa vào.

---

## 3. Nhóm B — Nợ thật

### B1. Ngưỡng và trọng số chưa tách ra config — ✅ ĐÃ SỬA (2026-08-04)

`multiagent/config/scoring.yaml` + `src/config.py`. `graph.py` đọc `weights`/`decision` từ config, `label_helper.py` đọc khối `labelling`, `state.py` có `content_type`/`langcode`. Bước 1–4 của `docs/config-spec.md` mục 7 xong; bước 5 (khối `scoring` cho rubric) chờ A1.

**Bằng chứng đây là refactor thuần:** 22/22 bộ test cũ xanh, không sửa test nào; `label_helper.py` chạy lại trên 33 mẫu gold set cho ra file **giống hệt từng byte** với báo cáo đã commit.

**Có thêm cảnh báo lúc chạy** (`config-spec.md` mục 5a): khối `meta.calibrated = false` → log cảnh báo mỗi lần chạy, để không lỡ trình bày kết quả chạy bằng ngưỡng minh hoạ như thể đã calibrate; `meta.model` lệch `ANTHROPIC_MODEL` → cảnh báo riêng, vì model đọc từ biến môi trường nên đổi `.env` là ngưỡng calibrate mất hiệu lực mà không có dấu hiệu gì.

**Lỗi thật mà nó phòng (giữ lại để tra cứu):** cùng một tập số từng nằm ở **4 nơi** và **đã trôi lệch một lần** — mã B3 từng ghi `150-160` trong guideline trong khi rubric ghi `140-170`. Phát hiện tình cờ khi đối chiếu; nếu phát hiện sau khi đã gán 33 nhãn thì phải gán lại toàn bộ.

### B2. Ba agent còn ghép prompt bằng nhãn text thuần

**Bằng chứng:** `content_quality.py`, `seo.py`, `fact_check.py` còn ghép chuỗi dạng `[title] ... [body] ...`. (`compliance.py` đã chuyển sang M1 ngày 2026-08-04.)

**Rủi ro:** nhãn đó **giả mạo được** — người viết gõ đúng chuỗi vào body là xoá ranh giới giữa dữ liệu và chỉ dẫn. Nguy hiểm hơn: `body` là HTML nên chỉ dẫn giấu trong bình luận HTML **vô hình với người duyệt nhưng LLM vẫn đọc**. Phân tích đầy đủ: `docs/prompt-injection.md` mục 2–3.

**Đã làm được phần nào:** BV6 (`brand_voice.py`) và Compliance (`compliance.py`, từ 2026-08-04) dùng thẻ có hậu tố ngẫu nhiên — biện pháp **M1**. Compliance được ưu tiên vì nó là agent duy nhất có quyền phủ quyết: một câu chèn thành công ở đó đổi được kết luận "chặn xuất bản" thành "cho qua".

`content_quality.py`, `seo.py`, `fact_check.py` chưa. **M3** (bóc phần ẩn trước khi đưa vào prompt) và **M2** (tiêu chí phát hiện chỉ dẫn ẩn) chưa làm.

**Giảm nhẹ sẵn có:** `docs/prompt-injection.md` mục 4 nêu ba thứ đang hạn chế hậu quả — structured output ràng buộc hình dạng đầu ra, hệ thống không tự xuất bản, và phần tất định (blacklist regex, Aggregator) miễn nhiễm hoàn toàn.

### B3. `score` của Compliance độc lập với `flags` — ✅ ĐÃ SỬA (2026-08-04)

Giải quyết luôn khi chuyển Compliance sang rubric CP1–CP8 (A1). Điểm và flag giờ sinh từ **cùng một bộ `criteria`**: điểm qua `scoring.score_from_criteria()`, flag qua `_flags_from_criteria()` với severity tra bảng `scoring.severity_for()`. Không còn đường nào để một bài mang 3 flag `critical` mà vẫn 95 điểm — có test khoá lại (`test_diem_va_flag_khong_con_mau_thuan`).

**Bằng chứng của vấn đề gốc (giữ để tra cứu):** `compliance.py` trước đây lấy `score` nguyên từ LLM, còn flag rule-based cộng thêm vào sau, nên hai thứ không liên quan gì nhau. Compliance là agent duy nhất có quyền phủ quyết nên đây là chỗ nguy hiểm nhất để có hai nguồn sự thật.

---

## 4. Nhóm C — Chưa tới lượt (không phải nợ)

| Hạng mục | Ghi ở đâu | Ghi chú |
|---|---|---|
| Polling worker + Content Moderation "Needs Review" | `architecture.md` mục 9 | Sprint 2 còn lại. Không chặn gì |
| Nhật ký truy vết JSONL | `operations.md` mục 2 | Đã **hạ ưu tiên** 2026-08-03 sau khi phát hiện Drupal giữ revision — 3 field AI không mất, chỉ mất bối cảnh chấm |
| Vòng phản hồi người duyệt | `operations.md` mục 3 | Cần nhật ký truy vết xong trước mới khớp được `(node_id, scored_at)` |
| ~~KB fact-check chưa verify số thật~~ | `sources.md` mục 2.1 | ✅ **xong 2026-08-04** — 4/4 entry `verified: true`. Tìm ra 3 chỗ sai, trong đó `sources.md` nói **ngược** sự thật về chuẩn đo. Còn một rủi ro không khử được: VinFast công bố **ba** con số khác nhau cho VF 5 Plus |
| Mở rộng corpus `BRAND` | `sources.md` mục 1.7 | Chỉ làm nếu có quy ước rơi vào vùng chưa đủ căn cứ. Hiện "trạm sạc" ở 9/11 (p = 0,065) — **cố ý không thu thêm** vì đó là *optional stopping* |

---

## 5. Nhóm D — Phép đo chưa chạy

| Mã | Đo gì | Trạng thái |
|---|---|---|
| **E1** | Độ ổn định điểm qua nhiều lần chấm | ✅ **đạt** (2026-08-04) — điểm tổng σ = 0,28; 100% giữ nguyên quyết định |
| **E2** | Retrieval lấy đúng đoạn (recall@k) | ✅ fact-check 1.00; brand 78,3% vs mốc 21,7% |
| **E3** | Multi-agent có hơn single-agent không | ❌ chưa — cần gold set |
| **E4** | Chi phí và độ trễ mỗi bài | ✅ **đo rồi** (2026-08-04) — $0,042–0,052/bài, ~28–38k token vào |
| **E5** | Ngưỡng quyết định tối ưu (calibration) | ❌ chưa — cần gold set (E1 đã đạt, không còn chặn) |
| **E6** | Held-out test | ❌ chưa — sau E5 |

**E4 làm lộ một sai số trong tài liệu:** `evaluation-plan.md` mục 4.4 ước tính $0,025/bài và ~12k token. Số đo thật gấp khoảng **2×** — cần sửa lại con số trong tài liệu đó.

**Một phát hiện ngoài dự kiến trong lúc chạy E1:** khi API Anthropic hết hạn mức giữa chừng, **chỉ Brand Voice còn chấm được** (6/7 tiêu chí của nó là regex, không cần LLM); 3 agent kia hỏng hoàn toàn. Đây là kiểm chứng ngoài đời thật cho thiết kế *suy giảm có kiểm soát* ở `architecture.md` mục 6.4 — không phải thí nghiệm có chủ đích, nhưng đáng ghi.

---

## 6. Giới hạn cố ý, không phải nợ

Những thứ dưới đây là **quyết định có cân nhắc**, ghi ở đây để không bị hiểu nhầm là thiếu sót:

| Giới hạn | Lý do |
|---|---|
| Shadow-test thật (E6) không làm được | Cần Drupal thật của VinFast, đội content thật, luồng duyệt thật — dự án không được cấp. Thay bằng held-out test (`evaluation-plan.md` mục 4.6) |
| Gold set do **một người** gán nhãn | Không được cấp nhân sự. Dùng Kappa test-retest làm trần thay cho Kappa người-người, và nêu rõ đó là ước lượng lạc quan |
| Brand guideline tự trích xuất, không phải tài liệu nội bộ | Dự án không được cấp tài liệu nội bộ VF O2O |
| Quy ước "trạm sạc / trụ sạc" để `NA` | Thu thêm corpus để đẩy p qua ngưỡng là *optional stopping* — làm mọi p-value mất giá trị |
| `url_alias` không nằm trong `content_hash` | Bên PHP phải tra bảng `path_alias` riêng; thêm phức tạp để bắt trường hợp hiếm |
| Chưa hiển thị `criteria` chi tiết của Brand Voice trong UI | Dữ liệu đã có trong pipeline, chờ xem giao diện thật rồi mới quyết |

---

## 7. Thứ tự đề xuất

```
[x] 1. E1 + E4  (độ ổn định, chi phí)   <- xong 2026-08-04
[x] 2. A2  (SEO đọc alt trong body)     <- xong 2026-08-04
[x] 3. B1  (tách config)                <- xong 2026-08-04
--------- sắp lại sau khi có số liệu E1 ---------
    4. A1-compliance  (rubric cho Compliance)  <- σ = 5,48, VẪN chặn E5
    5. Sửa con số chi phí sai ở evaluation-plan.md mục 4.4
---- chờ mentor ----
    6. A3  (gán nhãn gold set)
    7. E3, E5, E6
---- không chặn gì, làm lúc nào cũng được ----
    8. A1-content_quality, A1-seo   <- E1 hạ ưu tiên: σ = 0,38 và 0,19
    9. Polling worker, nhật ký truy vết, B2 (prompt injection M1/M3), B3
```

Lý do E1 đứng đầu, và kết quả của việc đó: nó **rẻ, không phụ thuộc gì**, và là thí nghiệm quyết định số phận của `rubrics.md`. Nếu điểm đã ổn định bất ngờ thì luận điểm chính của rubric yếu đi và nên biết **trước** khi bỏ công viết lại 3 prompt (`evaluation-plan.md` mục 3 điểm 2). **Đó đúng là chuyện đã xảy ra:** E1 cho thấy hai trong ba agent ổn định hơn dự kiến, nên công viết lại rubric giờ dồn vào **một** agent (Compliance) thay vì ba. Chạy E1 trước đã tiết kiệm khoảng hai phần ba khối lượng của A1.

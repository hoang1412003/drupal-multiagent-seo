# Nợ kỹ thuật và giới hạn đã biết

**Phiên bản:** v1 (2026-08-04, cập nhật 2026-08-05: thêm B8–B11; đóng B6, B7)
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

Phân biệt A/B với C là quan trọng: gộp chung làm bức tranh đáng sợ hơn thực tế. Nhóm C là việc đã lên lịch, chưa tới lượt — **không phải nợ** (tự động hoá, từng nằm trong nhóm này, đã xong 2026-08-07, xem mục 4).

---

## 2. Nhóm A — Chặn Sprint 3

### A1. Ba agent còn để LLM tự cho `score` — ✅ ĐÃ ĐÓNG (2026-08-10), cả 4 agent dùng rubric

**Bằng chứng:** `src/agents/content_quality.py:16`, `seo.py:24`, `compliance.py:77` đều còn `"score": {"type": "integer"}` trong output schema — LLM tự phát minh thang điểm mỗi lần gọi.

**Vì sao chặn:** `docs/rubrics.md` mục 1 lập luận điểm không định nghĩa thì không tái lập được, nên calibrate ngưỡng trên nó cho ra ngưỡng trôi nổi.

**Đã đo bằng E1 (2026-08-04) — 7 bài × 5 lần = 35 lượt chấm.** Kết quả đảo ngược một phần giả thuyết ban đầu:

| Agent | σ điểm | σ lớn nhất trên 1 bài |
|---|---|---|
| content_quality | 0.38 | — |
| seo | 0.19 | — |
| brand *(đã có rubric)* | **0.00** ⚠️ | 0.00 ⚠️ |
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

⚠️ **Hai ô σ brand ở trên đã HẾT HIỆU LỰC từ 2026-08-05** — code Brand Voice đã đổi ở B7 (BV6 siết kiểm trích dẫn). Giữ lại làm bản ghi của lần đo đó, **không** trích như số của hệ thống đang chạy. Xem mục B7.

**Cảnh báo bắt buộc khi trích bất kỳ σ nào trong dự án này:** σ Brand Voice đi từ `0.00` lên `1.27` giữa hai lần đo **trong khi code Brand không đổi một dòng**. σ = 0 đo trên 5 lượt là may, không phải tính chất.

**Cảnh báo thứ hai, thêm 2026-08-04 sau khi sửa B5:** σ thấp cũng có thể là **triệu chứng của lỗi**, không phải bằng chứng của chất lượng. Bài G-008 có σ = 0,00 và điểm cố định 66,7 qua 5/5 lượt — trông ổn định nhất bộ — nhưng đó là vì một phép kiểm hỏng đang kẹp cứng các tiêu chí về cùng giá trị ở mọi lượt; sửa xong điểm rải 42,9–57,1. Trước khi khoe một σ thấp, phải trả lời được nó đến từ đo chính xác hay từ vứt bỏ thông tin.

**σ = 4,18 đã loại trừ được một nghi phạm (2026-08-04):** B5 không phải nguyên nhân — sửa xong σ trên 4 bài xấu nhất chỉ đi từ 7,70 xuống 7,29 (mục B5, có số đo trước/sau). Nguồn dao động còn lại nằm ở CP2/CP4/CP7/CP8, bốn tiêu chí LLM chấm, đúng như hướng đã ghi ở trên.

**`content_quality` và `seo`: ĐÃ CHUYỂN sang rubric (2026-08-10).** Trước đó quyết định giữ thang tự do, lập luận dựa trên σ = 0,38 và 0,19 ở bảng trên. Lập luận ấy **đúng về độ ổn định nhưng thiếu một vế**: σ thấp chứng minh điểm *tái lập được*, không chứng minh điểm *có định nghĩa*. LLM trả 78 đều đặn qua 5 lượt vẫn không ai nói được 78 khác 74 ở chỗ nào — mà calibrate ngưỡng trên một đại lượng không định nghĩa thì ngưỡng cũng không định nghĩa được. Đó chính là luận điểm gốc ở `rubrics.md` mục 1, và nó không bị σ bác bỏ.

Cài đặt: `src/seo_analysis.py` + `src/content_analysis.py` (phần đo bằng máy, tách theo đúng khuôn `compliance_analysis.py`), agent chỉ còn ghép mức. Ngưỡng đọc từ khối `scoring` của `scoring.yaml` — **lần đầu khối đó được dùng**, đóng nốt bước 5 của `config-spec.md` mục 7.

Tỉ lệ đo bằng máy: **SEO 7/10** tiêu chí, **CQ 3/8** (+CQ1/CQ2 do LLM liệt kê lỗi nhưng MÁY đếm và quy mức). Vì thế SEO nhiều khả năng làm σ **giảm**, CQ thì có thể **tăng** — chưa biết, phải đo lại E1.

Dọn theo: `scoring.kiem_diem_llm()`, hằng `DIEM_MIN/DIEM_MAX` và `scripts/test_diem_llm.py` **đã xoá** — chúng chặn điểm LLM tự đặt ra ngoài thang (nợ B10), mà nay không agent nào để LLM cho điểm nên không còn đường nào cho con số đó lọt vào. `scripts/test_seo_prompt.py` cũng xoá: nó khoá bản chép ngưỡng trong prompt (nợ B4), mà bản chép đó biến mất. *(Từ 2026-08-05 điểm hai agent này bị chặn trong dải 0-100 khi nhận — mục B10. Đó là kiểm giá trị vô lý, **không** phải rubric: nó không làm điểm tái lập được, nên không thay thế được gì của A1.)*

### A2. SEO Agent không đọc `alt` của ảnh nằm trong `body` — ✅ ĐÃ SỬA (2026-08-04)

`_extract_image_alt()` giờ nhận thêm `body_html` và bóc mọi thẻ `<img>` trong thân bài, trả về danh sách nhiều dòng (`Ảnh đại diện: …` / `Ảnh N trong bài: …`); dòng trống sau dấu hai chấm nghĩa là thiếu `alt`. Test: `scripts/test_image_alt.py`.

Kèm theo đã sửa một lỗi regex ở **cả** `drupal_client.py` và `label_helper.py`: `\balt` khớp nhầm cả `data-alt`, tức một ảnh **thiếu** `alt` nhưng có `data-alt` sẽ bị coi là có — bỏ sót lỗi B6. Đổi sang `(?<![\w-])`. Đã kiểm: 0 ảnh trong corpus hiện tại bị ảnh hưởng, nên **không có nhãn nào phải gán lại**.

**Bằng chứng của vấn đề gốc (giữ lại để tra cứu):** `_extract_image_alt()` trước đây chỉ đọc `relationships.field_image.data.meta.alt`. Ảnh nhúng trong chuỗi HTML của `body` không được bóc ra.

**Vì sao chặn:** mã lỗi **B6** trong `docs/goldset/annotation-guideline.md` v1.2 xét **mọi thẻ `<img>` trong `body`**, còn hệ thống chỉ xét **một ảnh đại diện**. Hai bên đo hai tập ảnh khác nhau → Recall/F1 của tiêu chí SEO9 lệch có hệ thống.

Đã ghi ở `docs/evaluation-plan.md` mục 4.5 điều kiện 4, kèm bằng chứng đo trên `node/7` (2026-07-30) và bài `G-001`.

### A3. Gold set chưa gán nhãn — ✅ ĐÃ XONG (2026-08-10), 33/33

**Cách làm cuối cùng:** gán tay toàn bộ, **giữ nguyên 33 mẫu**, **không** dùng AI gán nháp. Khối lượng nhỏ hơn dự kiến nhiều vì quy tắc quy nhãn (guideline mục 5) vốn **dừng sớm** — chỉ 20/33 bài phải đọc, 13 bài còn lại suy nhãn từ `injected_codes`. Công cụ hỗ trợ: `scripts/quet_ung_vien.py` (đánh dấu chỗ cần xem, không kết luận) + `label_helper.py` (mã máy đo được).

**Phân bố cuối:**

| | `rejected` | `needs_revision` | `publish` |
|---|---|---|---|
| 20 bài thật | 3 | 17 | **0** |
| 13 perturbation | 7 | 6 | 0 |
| **Tổng 33** | **10** | **23** | **0** |

**Con số này là KẾT QUẢ CỦA MỘT ĐỢT RÀ LẠI, không phải lần gán đầu.** Lần gán đầu cho 2 bài `publish` (G-016, G-019). Rà lại có hệ thống 33 bài × 16 mã lỗi (2026-08-10) tìm ra **6 lỗi B8 bị bỏ sót**, trong đó **cả hai bài `publish` đều dính**:

| Bài | Lỗi tìm thêm | Hệ quả |
|---|---|---|
| G-016 | `"thấp hơn **ít nhất ít hơn** 40%"` | `publish` → `needs_revision` |
| G-019 | `"đều **được được** trang bị"` | `publish` → `needs_revision` |
| G-009, G-010, G-014, P-007a, P-009a | lặp từ (`"nên nên"`, `"thêm thêm"`, `"cần cần"`, `"hơn hơn"`, `"sản sản"`) | chỉ thêm mã, nhãn không đổi |

Toàn bộ đã đối chiếu `raw_html` gốc xác nhận là lỗi của nguồn. **B8 là mã duy nhất không có công cụ nào lúc gán lần đầu** — cả 6 lỗi đều lọt qua mắt người đọc lướt, và cả 6 đều là **lặp từ**, loại lỗi mà mọi từ đều đúng chính tả nên đọc rất dễ trượt.

Đã rà nhất quán toàn bộ: `rejected` ⟺ có mã A, `needs_revision` ⟺ chỉ mã B, `publish` ⟺ không mã nào; `defect_codes` của bài perturbation đã gộp `injected_codes` (cần cho phép đo Recall/F1 theo mã).

**Đợt rà lại đó cũng đóng nốt hai mã chưa ai kiểm có hệ thống:** A5 (lạc đề >50%) và A6 (mất an toàn) — quét ứng viên trên cả 33 bài, **không bài nào dính**. Trước đó chúng là 0/33 vì *chưa ai rà*, khác hẳn 0/33 vì *đã rà và không có*.

**Cổng còn lại trước khi tin bất kỳ con số Sprint 3 nào:** test-retest (guideline mục 8.1) — đợi ≥3 ngày, gán lại 3-4 bài mù với nhãn cũ, yêu cầu Kappa ≥ 0,80. Sớm nhất **2026-08-13**. Chưa chạy.

**Giữ nguyên nguyên tắc đã cam kết:** không dùng AI gán nháp. Ba lần trong lúc gán có cân nhắc sửa nội dung bài cho ra `publish` — **không làm**, lý do ở mục 6 (dòng "Gold set lệch lớp").

---

## 3. Nhóm B — Nợ thật

### B1. Ngưỡng và trọng số chưa tách ra config — ✅ ĐÃ SỬA (2026-08-04)

`multiagent/config/scoring.yaml` + `src/config.py`. `graph.py` đọc `weights`/`decision` từ config, `label_helper.py` đọc khối `labelling`, `state.py` có `content_type`/`langcode`. Bước 1–4 của `docs/config-spec.md` mục 7 xong; bước 5 (khối `scoring` cho rubric) chờ A1.

**Bằng chứng đây là refactor thuần:** 22/22 bộ test cũ xanh, không sửa test nào; `label_helper.py` chạy lại trên 33 mẫu gold set cho ra file **giống hệt từng byte** với báo cáo đã commit.

**Có thêm cảnh báo lúc chạy** (`config-spec.md` mục 5a): khối `meta.calibrated = false` → log cảnh báo mỗi lần chạy, để không lỡ trình bày kết quả chạy bằng ngưỡng minh hoạ như thể đã calibrate; `meta.model` lệch `ANTHROPIC_MODEL` → cảnh báo riêng, vì model đọc từ biến môi trường nên đổi `.env` là ngưỡng calibrate mất hiệu lực mà không có dấu hiệu gì.

**Lỗi thật mà nó phòng (giữ lại để tra cứu):** cùng một tập số từng nằm ở **4 nơi** và **đã trôi lệch một lần** — mã B3 từng ghi `150-160` trong guideline trong khi rubric ghi `140-170`. Phát hiện tình cờ khi đối chiếu; nếu phát hiện sau khi đã gán 33 nhãn thì phải gán lại toàn bộ.

### B2. Ba agent còn ghép prompt bằng nhãn text thuần — ✅ ĐÃ XONG (2026-08-04)

`src/prompt_builder.py` (mới) dùng chung cho **cả 5 chỗ gọi LLM**. Không còn chỗ nào ghép chuỗi `[title] ... [body] ...`.

**Một lỗ hổng thật phát hiện khi nối M3 vào Compliance:** `strip_html()` khớp trọn `<!-- xe này tốt nhất -->` bằng regex `<[^>]+>` và xoá luôn chữ bên trong, nên **cụm từ cấm giấu trong bình luận HTML đi qua blacklist CP1 mà không bị bắt lần nào**. Người duyệt cũng không thấy vì họ đọc bài đã render. Tệ hơn dự kiến ở chỗ: không phải LLM bị lừa, mà chính *phần tất định* — thứ `prompt-injection.md` mục 4 liệt kê là "miễn nhiễm hoàn toàn" — bị mù. Đã sửa, có test khoá cả hai chiều.

**M2 (CP9) cũng xong.** Phát hiện chỉ dẫn ẩn nhắm vào hệ thống đánh giá tự động → flag `critical` → veto. **Đứng ngoài công thức tính điểm**: thêm một tiêu chí gần như luôn ở mức 2 sẽ cộng điểm miễn phí cho mọi bài (trên G-004 thật: 50,0 → 62,5 mà bài không đổi một chữ) và làm σ đẹp lên bằng cách pha loãng mẫu số. Chi tiết + hai giới hạn đã biết: `prompt-injection.md` mục 5 M2.

**Biện pháp duy nhất không làm là M5** (lọc bằng danh sách từ khoá) — tài liệu đã lập luận nó dễ vòng tránh và tạo cảm giác an toàn giả.

**Bằng chứng của vấn đề gốc (giữ để tra cứu):** trước đây `content_quality.py`, `seo.py`, `fact_check.py` ghép chuỗi dạng `[title] ... [body] ...`.

**Rủi ro:** nhãn đó **giả mạo được** — người viết gõ đúng chuỗi vào body là xoá ranh giới giữa dữ liệu và chỉ dẫn. Nguy hiểm hơn: `body` là HTML nên chỉ dẫn giấu trong bình luận HTML **vô hình với người duyệt nhưng LLM vẫn đọc**. Phân tích đầy đủ: `docs/prompt-injection.md` mục 2–3.

**Vì sao Compliance là chỗ đáng làm nhất:** nó là agent duy nhất có quyền phủ quyết, nên một câu chèn thành công ở đó đổi được kết luận "chặn xuất bản" thành "cho qua".

**Giảm nhẹ sẵn có:** `docs/prompt-injection.md` mục 4 nêu ba thứ đang hạn chế hậu quả — structured output ràng buộc hình dạng đầu ra, hệ thống không tự xuất bản, và phần tất định (blacklist regex, Aggregator) miễn nhiễm hoàn toàn.

### B3. `score` của Compliance độc lập với `flags` — ✅ ĐÃ SỬA (2026-08-04)

Giải quyết luôn khi chuyển Compliance sang rubric CP1–CP8 (A1). Điểm và flag giờ sinh từ **cùng một bộ `criteria`**: điểm qua `scoring.score_from_criteria()`, flag qua `_flags_from_criteria()` với severity tra bảng `scoring.severity_for()`. Không còn đường nào để một bài mang 3 flag `critical` mà vẫn 95 điểm — có test khoá lại (`test_diem_va_flag_khong_con_mau_thuan`).

**Bằng chứng của vấn đề gốc (giữ để tra cứu):** `compliance.py` trước đây lấy `score` nguyên từ LLM, còn flag rule-based cộng thêm vào sau, nên hai thứ không liên quan gì nhau. Compliance là agent duy nhất có quyền phủ quyết nên đây là chỗ nguy hiểm nhất để có hai nguồn sự thật.

### B4. Ngưỡng trong system prompt của SEO Agent đã trôi lệch khỏi `scoring.yaml` — ✅ ĐÃ SỬA (2026-08-04)

**Đây là bản chép thứ NĂM của cùng tập số, và nó đã lệch.** `config-spec.md` mục 1 đếm bốn bản (`graph.py`, `label_helper.py`, `rubrics.md`, `annotation-guideline.md`) và B1 đã gộp chúng về một chỗ — nhưng bỏ sót một bản: các ngưỡng nằm **trong chuỗi system prompt** của SEO Agent. Chúng không trông giống hằng số nên không ai đi tìm ở đó.

**Bằng chứng:**

| Ngưỡng | `scoring.yaml` | `seo.py` (prompt) | Lệch? |
|---|---|---|---|
| `title` | `scoring.title_ideal` = 50-60 | `seo.py:10` — "50-60 ký tự" | không |
| `meta_description` | `scoring.meta_ideal` = **140-170**<br>`labelling.meta_ok` = **140-170** | `seo.py:11` — "**150-160** ký tự" | **có** |
| độ dài `body` | `scoring.body_min_words` = **600** | `seo.py:16` — "tối thiểu **~300** từ" | **có** |

`title` khớp `title_ideal` nên không phải sửa — ghi vào bảng để lần sau khỏi kiểm lại. Lưu ý `meta` là trường hợp hiếm khi hai họ ngưỡng (`scoring` và `labelling`, `config-spec.md` mục 2) **trùng giá trị**, nên con số trong prompt lệch khỏi **cả hai**.

**Vì sao là nợ thật chứ không phải "chưa tới lượt":**

- **Meta — lệch sống, ảnh hưởng ground truth.** `label_helper.py:54-56` đọc `labelling.meta_ok` và sinh mã **B3** khi độ dài ra ngoài 140-170 (`label_helper.py:192-193`). Bài có meta dài 145 hoặc 165 ký tự thì **ground truth nói không lỗi**, còn SEO Agent được dặn dải lý tưởng là 150-160 nên nhiều khả năng vẫn báo lỗi. Hai bên đo hai thang khác nhau → Recall/F1 của tiêu chí **SEO3 lệch có hệ thống**, đúng hình dạng của A2 (nơi hệ thống xét một ảnh còn nhãn xét mọi ảnh).
- **Body — lệch ngầm, sẽ nổ ở bước 5.** Khối `scoring` hiện chưa có ai đọc (B1, `config-spec.md` mục 7 bước 5), nên `600` chưa va vào `~300` lần nào. Nhưng khi viết rubric cho SEO thì đây đúng là chỗ "hard-code rồi tách sau" mà bước 5 dặn tránh — chênh gấp đôi, không phải sai số làm tròn.

**Đã sửa:** `seo.py` giờ ghi `140-170 ký tự` (meta) và `đạt là từ ~600 từ trở lên` (body).

Con số body đổi từ `~300` sang `600` chứ không phải chỉ sửa lỗi chép: rubric **SEO7** định nghĩa `<300 từ` = mức 0, `300-599` = mức 1, `≥600` = mức 2. Bản cũ đưa cho LLM **mốc "quá tệ" làm mục tiêu**, nên một bài 350 từ được prompt coi là đủ dài trong khi rubric xếp nó ở mức 1.

**Chặn tái diễn bằng test, không bằng lời dặn:** `scripts/test_seo_prompt.py` (mới) đọc khối `scoring` từ `scoring.yaml` rồi assert prompt có đúng các con số đó, cộng một test chặn riêng chuỗi `150-160` / `~300 từ` quay lại qua một lần copy-paste. Đã kiểm test **thật sự đỏ** khi hoàn nguyên con số cũ, chứ không phải xanh vì không kiểm gì.

**Còn lại (không chặn gì):** khi làm A1-seo thì ghép prompt **thẳng từ config**, bỏ hẳn bản chép này — lúc đó `test_seo_prompt.py` thành thừa và xoá được.

**Bài học ghi lại vì nó sẽ tái diễn:** con số nằm trong prompt là hằng số như mọi hằng số khác, chỉ khác ở chỗ `grep` theo tên biến không thấy.

**Đã rà nốt ba prompt còn lại (2026-08-04) — sạch, không có bản chép thứ sáu:**

| Prompt | Con số bên trong | Kết luận |
|---|---|---|
| `content_quality.SYSTEM_PROMPT` | *(không có con số nào)* | sạch |
| `compliance._LLM_PROMPT` | mã tiêu chí CP2/4/7/8, mức 0/1/2, "Luật Cạnh tranh 2018" | sạch — không phải ngưỡng chấm điểm |
| `brand_voice._BV6_PROMPT` | mức 0/1/2 | sạch |

Một ngưỡng thật còn nằm ngoài config, nhưng **không phải nợ mới**: `brand_voice._NGUONG_MUC_0 = 3` (từ 3 chỗ sai trở lên → mức 0) hiện chép tay từ `rubrics.md` mục 5. Nó thuộc đúng **bước 5** của `config-spec.md` mục 7 (đọc khối `scoring` từ config khi implement rubric), đã ghi ở B1. Tương tự, `scoring.long_sentence_words` và `long_paragraph_sentences` trong `scoring.yaml` hiện **chưa có ai đọc** — chúng chờ A1-content_quality, và `content_quality.SYSTEM_PROMPT` hiện không nêu con số nào nên LLM tự định nghĩa thế nào là "câu quá dài".

### B5. CP8 trả mức **2** khi LLM chấm 0/1 mà không trích dẫn được — ✅ ĐÃ SỬA (2026-08-04)

**Bằng chứng (đường đi trong code):** CP8 nằm trong `_MAY_QUYET_AP_DUNG`, nên nhánh hợp thức hoá của nó là `compliance.py:306-309`:

```python
if ma in _MAY_QUYET_AP_DUNG:
    return muc if (muc == 2 or _trich_dan_co_that(evidence, text_theo_field)) else 2
```

LLM chấm mức 0 hoặc 1 nhưng `evidence` không khớp nguyên văn trong bài → hàm trả **2**, tức **điểm tối đa**. `_chot_cp8()` sau đó chỉ ghi đè khi `level is None` (`compliance.py:372`), nên mức 2 đó đi thẳng vào công thức tính điểm.

**Vì sao là nợ chứ không phải lựa chọn:** cùng một tình huống — "LLM không chứng minh được điều nó vừa nói" — hiện cho **ba** kết cục khác nhau:

| Tiêu chí | Không trích được thì thành | Hiệu ứng lên điểm |
|---|---|---|
| CP2 | mức 2 | đúng thiết kế — mức 2 của CP2 nghĩa là "không tìm thấy vi phạm" |
| CP4, CP7 | NA | bị loại khỏi cả tử số lẫn mẫu số |
| **CP8** | **mức 2** | **cộng điểm tối đa cho tiêu chí vừa bị nghi là vi phạm** |

Kết cục của CP8 ngược với chính lập luận trong docstring `_chot_cp8`: *"bài CÓ số liệu mà LLM vẫn trả NA → mức 0, vì mức 0 của CP8 định nghĩa đúng là 'có số liệu nhưng không nêu nguồn nào'"*. Theo đúng lập luận đó, "máy đã xác nhận bài có số liệu, LLM không chỉ ra được nguồn nào" cũng phải là mức 0 — không thể là mức 2. Đây là mẫu **điểm miễn phí** mà `rubrics.md` mục 2.2 cảnh báo, cùng loại với lỗi *thoả mãn rỗng* đã sửa ở BV7.

**Đã đo (2026-08-04), 2 × 20 lượt, $0,92.** Script `scripts/chan_doan_lat_muc.py` (mới) chạy lặp trên 4 bài có σ Compliance lớn nhất và ghi **nhật ký mỗi lần `_hop_thuc_hoa` ghi đè mức LLM chấm** — thứ mà nhìn `criteria` ở đầu ra không thấy được. Số liệu thô: `docs/evidence/cp_lat_muc_truoc_sua.json` và `cp_lat_muc_sau_sua.json`.

**Kết quả 1 — B5 có thật và rất thường xuyên:** CP8 bị đẩy lên mức 2 ở **10/20 lượt** (LLM chấm 0 → 2: 7 lần; 1 → 2: 3 lần).

**Kết quả 2 — nguyên nhân gốc nằm sâu hơn một tầng, và KHÔNG phải LLM bịa.** `_trich_dan_co_that()` đòi đoạn trích là **một chuỗi liền mạch**, trong khi LLM trả về bằng chứng thật nhưng nhiều mảnh. Kiểm lại từng mảnh thì **không có lần nào LLM bịa** — ví dụ G-008:

```
đoạn trích bị loại : "Trong khoảng 1 giờ ... từ 0 lên tới 10%.
                      Đây là bộ sạc cho phép người dùng..."
khớp nguyên khối   : False
mảnh 1 / mảnh 2    : True / True     <- cả hai đều có nguyên văn trong bài
```

Hai câu nằm ở hai thẻ HTML khác nhau; `strip_html` chèn `".\n"` vào giữa nên chúng **không bao giờ liền mạch được**. Dạng còn lại: LLM nối hai trích dẫn bằng `" và "` hoặc `;`. Việc loại oan này không chỉ chạm CP8 — **6/10** lần CP4/CP7 bị đẩy về NA cũng là loại oan y hệt, tức rút tiêu chí khỏi **mẫu số**.

**Đã sửa cả hai:** CP8 không trích được → **mức 0** (không phải 2); và `_trich_dan_co_that()` xét **theo mảnh** — tách ở `" và "`, `;`, `". "`, **mọi** mảnh phải khớp nguyên văn. Phép kiểm mới chỉ nhận THÊM, không bao giờ loại đi thứ bản cũ đã chấp nhận, nên nó không phải là nới lỏng cơ chế chống bịa: bịa nửa câu vẫn trượt (có test khoá cả hai chiều).

**Kết quả 3 — và đây là phần quan trọng nhất, ngược hẳn dự đoán ban đầu:**

| | TRƯỚC | SAU |
|---|---|---|
| Số lần ghi đè oan | **20** | **4** |
| Mẫu số trung bình (/8) | 4,75 | **5,10** |
| σ trung bình 4 bài | 7,70 | **7,29** |

Số lần ghi đè oan giảm 80% và mẫu số lớn lên, **nhưng σ gần như không đổi**. Giả thuyết ban đầu — rằng sửa khâu trích dẫn sẽ kéo σ xuống mạnh — **là sai**, và dữ liệu bác bỏ nó.

**Lý do, đo được trên G-008:** trước khi sửa nó có σ = **0,00**, điểm cố định 66,7 qua cả 5 lượt — con số trông ổn định nhất trong cả bộ. Sau khi sửa, điểm rải **42,9–57,1** và σ = 6,16. Nghĩa là **σ cũ thấp không phải vì hệ thống chấm ổn định, mà vì một phép kiểm hỏng đang kẹp cứng các tiêu chí về cùng một giá trị ở mọi lượt.** Nó cũng có nghĩa điểm 66,7 của G-008 là **sai một cách nhất quán** — và sai kiểu đó nguy hiểm hơn dao động, vì σ = 0 làm nó trông đáng tin.

**Bài học cho cách đọc mọi σ trong dự án này:** σ thấp chỉ đáng mừng khi biết chắc nó không đến từ việc vứt bỏ thông tin. Ghi thêm vào cảnh báo σ đã có ở mục A1.

**Hệ quả cho A1/E5:** B5 **không phải** nguyên nhân của σ Compliance = 4,18, và giờ đã loại trừ được bằng số. Nguồn dao động còn lại là CP2/CP4/CP7/CP8 — bốn tiêu chí LLM chấm. Hướng duy nhất còn lại vẫn là hướng A1 đã ghi: chuyển thêm tiêu chí sang đo bằng máy.

*(Ghi nhận về phương pháp: mô phỏng offline trên dữ liệu đã đo dự đoán σ = 7,35, đo thật ra 7,29. Mô phỏng lại Aggregator/rubric trên kết quả đã lưu là cách rẻ và đủ chính xác để thử một thay đổi trước khi trả tiền chạy lại — cùng lợi ích mà `architecture.md` mục 8.2 nêu cho việc quét ngưỡng.)*

### B6. `graph.py` không truyền `content_type`/`langcode` xuống agent — ✅ ĐÃ SỬA (2026-08-05)

**Đã sửa:** thêm `graph._khoa_cua(state)` — **một chỗ duy nhất** suy ra cặp khoá, dùng cho cả `_config_cua` lẫn hai node agent. Gộp về một chỗ chứ không chép hai dòng vào mỗi node, vì thứ hỏng ở đây đúng là *Aggregator và agent tra theo hai giá trị khác nhau trong cùng một lần chấm*; để hai đường suy ra riêng là chừa nguyên khả năng đó.

**Refactor thuần, không đổi hành vi hiện tại** — có test khoá cả hai chiều: khoá từ state được truyền xuống, và state thiếu/rỗng khoá vẫn ra `cam_nang`/`vi` như trước (`scripts/test_graph_truyen_khoa.py`). Test ghi ở đúng ranh giới `graph → agent`, tức đúng chỗ đã hỏng.

**Ảnh hưởng lên kết quả hiện tại: KHÔNG có.** Xếp vào nhóm B chứ không phải C vì thứ đang sai là **một khẳng định trong tài liệu**, và người chấm kiểm được bằng cách mở đúng hai file.

**Bằng chứng:** `graph.py:72` và `graph.py:80` gọi `brand_voice.run(state["fields"])` và `compliance.run(state["fields"])` — không truyền tham số nào, nên rơi vào default `content_type="cam_nang"`, `langcode="vi"` trong chữ ký hàm. Default đó chảy tiếp xuống `retrieve()` của BV6 và `fact_check.danh_gia()` của CP3, tức **hai truy vấn RAG luôn lọc Chroma theo hằng số**.

Trong khi đó `aggregator_node` **có** đọc đúng từ state (`graph.py:98` → `_config_cua`). Cùng một lần chấm: Aggregator tra config theo state, hai agent RAG dùng hằng số.

**Vì sao vẫn tính là nợ:**

- `state.py:6-9` viết: *"Không hard-code 'vi' ở đâu trong logic agent - đây là một trong ba điểm giữ sẵn để mở rộng ngôn ngữ/loại nội dung mà không đập đi làm lại"*.
- `architecture.md` mục 5.6 trục 2 điểm (1): *"`langcode` là tham số đầu vào của Orchestrator và mọi agent, không hard-code 'vi'"*.
- Đọc code thì điều đó **chưa đúng**. Hai field trong `ContentReviewState` được thêm vào đúng vì mục đích này nhưng chưa đi hết đường xuống agent.

**Vì sao chưa gây lỗi lần nào:** `scoring.yaml` mới có một khoá thật (`cam_nang:vi`), và cả hai KB đều nạp với đúng cặp giá trị đó (`build_brand_kb.py:77-78`, `kb/build_kb.py`), nên hằng số hard-code **trùng khớp** giá trị đúng. Thêm khoá thứ hai là lỗi hiện ra ngay — và hiện ra ở dạng khó chẩn đoán: điểm vẫn tính được, chỉ là RAG lấy về đoạn của sai phân vùng.

### B7. BV6 không hề kiểm trích dẫn — comment nói một đằng, code làm một nẻo — ✅ ĐÃ SỬA (2026-08-05)

**Đã sửa:** `_trich_dan_co_that` chuyển ra `text_utils.trich_dan_co_that` (đúng chỗ tài liệu này đề xuất), Compliance và Brand Voice giờ dùng **chung một phép kiểm**. BV6 hạ mức mà không trích được nguyên văn → quay về mức 2.

Mức 2 chứ không phải NA, cùng hướng với CP2: mức 2 của BV6 nghĩa là "không thấy lệch chuẩn", nên đó là kết luận đúng khi không có bằng chứng. Khác CP4/CP7 (→ NA) vì hai tiêu chí đó còn phải chứng minh bài **có** bàn tới chủ đề, còn bài nào cũng có giọng văn để so.

3 test mới, gồm một test khoá đúng ca mà B5 đã sửa (trích dẫn nhiều mảnh ở hai thẻ HTML khác nhau vẫn được chấp nhận) — nếu BV6 dùng phép kiểm riêng thì nó sẽ loại oan đúng kiểu đó.

> ⚠️ **HỆ QUẢ ĐO LƯỜNG — ĐỌC TRƯỚC KHI TRÍCH BẤT KỲ σ BRAND NÀO.**
> Sửa này **đổi điểm Brand Voice** trên các bài đã đo. Mọi số σ Brand trong tài liệu (`0.00`, `1.27`, và bảng ở mục A1) đo trên code **trước** B7 và **không còn áp dụng cho code hiện tại**. E1 chưa chạy lại — chưa chạy thì không được trình bày số cũ như số của hệ thống đang chạy.
>
> Hướng dao động cũng **chưa biết trước**: siết trích dẫn đẩy một số lượt BV6 từ mức 0/1 lên mức 2, nên nó vừa có thể làm σ giảm (bớt lật mức) vừa có thể làm σ tăng (mức lật ở tập bài khác). Đúng bài học B5: đừng đoán, đo.

### B7 — bằng chứng của vấn đề gốc (giữ để tra cứu)

**Bằng chứng:** `brand_voice.py:301-304`

```python
# rubrics.md mục 2.5: hạ mức mà không trích được nguyên văn thì không
# được hạ. Đây là cơ chế chống bịa lỗi.
if level in (0, 1) and not kq["evidence"].strip():
    level = 2
```

Comment nói "trích được **nguyên văn**", code chỉ kiểm chuỗi **khác rỗng**. LLM trả về bất kỳ ký tự nào là qua — kể cả một câu hoàn toàn bịa. Cơ chế chống bịa thật (`_trich_dan_co_that`) chỉ tồn tại ở Compliance.

**Vì sao đáng sửa:** BV6 là tiêu chí LLM **duy nhất** của Brand Voice (6/7 tiêu chí kia là regex), nên nó là toàn bộ bề mặt bịa lỗi của agent này. Và `rubrics.md` mục 2.5 đặt quy tắc trích dẫn cho **mọi** tiêu chí, không riêng Compliance.

**Chỗ đặt đã chọn:** `text_utils.py`, đúng lý do file đó tồn tại — dùng chung giữa các phía để hai bên không đo bằng hai cách khác nhau.

### B8. Hai cụm blacklist `critical` chưa từng khớp lần nào — ✅ ĐÃ SỬA (2026-08-05)

**Bằng chứng (chạy được, không phải suy luận):** `match_blacklist()` ghép pattern `\b + re.escape(cụm) + \b` cho **mọi** cụm. `\b` là ranh giới giữa ký tự chữ/số và ký tự không phải chữ/số, nên `\b` đặt sau `%` đòi hỏi ngay sau đó phải có chữ/số — mà trong văn bản thật, sau `%` luôn là dấu cách hoặc dấu câu.

```
'hiệu quả 100%'  -> False      <- không bắt được
'cam kết 100%'   -> False      <- không bắt được
'số 1'           -> True
'tốt nhất'       -> True
```

**Ảnh hưởng: 2/19 cụm cấm chết, cả hai đều `severity: critical`.** Nghĩa là một bài quảng cáo "cam kết 100%" đi qua CP1 sạch sẽ, không sinh flag, không kích hoạt veto.

**Vì sao là nợ thật chứ không phải sai sót nhỏ:**

- Blacklist là **cách đo duy nhất của CP1**, không còn nguồn flag song song nào bù lại sau khi A1-compliance gộp về một bộ `criteria`.
- Nó là phần **vẫn chạy khi LLM bị lừa hoàn toàn** (`prompt-injection.md` mục 4c). "Miễn nhiễm với injection" **không có nghĩa là đúng** — đây là lần thứ hai đúng lớp phòng vệ đó bị mù vì lỗi của chính nó, sau B2 (`strip_html` xoá luôn chữ trong bình luận HTML).
- **Test cũ không phủ.** 8 case trong `test_compliance_rules.py` đều dùng cụm kết thúc bằng chữ, nên bộ test xanh suốt trong khi hai cụm chết.

**Đã sửa:** thêm `_mau_khop()` — chỉ đặt `\b` ở đầu/cuối khi ký tự ở đó là chữ/số. Không nới lỏng thành so khớp chuỗi con thô: `"số 1"` vẫn không khớp `"số 10"` (có test khoá cả hai chiều, 5 case mới).

**Bài học, cùng họ với B4:** con số/ký tự đặc biệt trong **dữ liệu cấu hình** cũng là hằng số như hằng số trong code, chỉ khác ở chỗ lỗi không nằm ở giá trị mà ở **giả định của đoạn code đọc nó** — ở đây là giả định ngầm "mọi cụm cấm đều bắt đầu và kết thúc bằng chữ". Cách chặn tái diễn là test phủ đúng **hình dạng** khác thường của dữ liệu, không phải đọc lại danh sách bằng mắt.

### B9. CP3 tin `index` do LLM tự điền — ✅ ĐÃ SỬA (2026-08-05)

**Bằng chứng:** `fact_check.danh_gia()` tra ngược `pairs[v["index"]][0]` với `index` là số LLM tự sinh trong `_COMPARE_SCHEMA`. Chạy thử với `index = 7` trên một pair: `IndexError: list index out of range`.

**Vì sao nguy hiểm hơn một exception bình thường:** lỗi đó không nổ ra ngoài. `compliance._cp3_so_lieu()` bọc `try/except` để KB chưa dựng không làm sập agent, nên nó **nuốt luôn** IndexError và **CP3 âm thầm thành NA** — mất hẳn tiêu chí fact-check, trên đúng đường CP3 → `critical` → veto, mà không có dấu hiệu gì. Đây là mặt trái của một quyết định đúng: `try/except` bảo vệ đường hạ tầng lại che luôn lỗi logic.

**Lỗi thứ hai tìm ra khi viết test:** LLM trả **thiếu** verdict cho một pair thì bản cũ bỏ qua pair đó, nên bài chỉ còn toàn `match` → **mức 2** ("mọi claim đều khớp") trong khi có claim chưa hề được đối chiếu. Cùng họ *điểm miễn phí* với B5.

**Đã sửa:** gom verdict theo **vị trí** (`verdicts_hop_le()` lọc index ngoài biên, chấm trùng giữ lần đầu — cùng quy ước với `compliance._danh_gia_llm`), rồi duyệt `pairs`; pair không có verdict hợp lệ → *chưa kết luận* → mức 1. 3 test mới.

### B10. `score` của Content Quality/SEO không có chặn biên — ✅ ĐÃ SỬA (2026-08-05)

**Bằng chứng:** output schema của hai agent chỉ ghi `"score": {"type": "integer"}`. Hai điều kiện cộng lại làm chỗ này hở:

1. **Không chỗ nào nói cho LLM biết thang điểm là gì.** Cả `content_quality.SYSTEM_PROMPT` lẫn `seo.SYSTEM_PROMPT` đều không nhắc "0-100" — LLM chỉ suy ra từ tên trường `score`.
2. **Structured outputs không chặn hộ.** `minimum`/`maximum` nằm trong nhóm ràng buộc JSON Schema mà Anthropic **không hỗ trợ** (kiểu `integer` thì có hiệu lực). Nên thêm hai khoá đó vào schema là để cho có — kiểm tra trước khi tin là bước bắt buộc, không phải chi tiết.

Điểm ngoài dải đi thẳng vào trung bình có trọng số của Aggregator và vỡ thang điểm của cả hệ thống.

**Đã sửa:** `scoring.kiem_diem_llm()`, gọi ngay khi nhận ở cả hai agent (`architecture.md` mục 7 "validate ngay khi nhận"). **Ném ValueError chứ không kẹp về biên**: `graph.py` bắt exception → agent lỗi → Aggregator chia lại trọng số và ghi `note`, nên người duyệt thấy "điểm chưa đầy đủ". Kẹp biên là sửa lặng lẽ một con số bất thường.

**Không sửa cái này thay cho A1.** Nó chỉ chặn giá trị vô lý, không làm điểm tái lập được — A1 vẫn nguyên như bảng σ ở trên.

### B11. Cache toàn cục bỏ qua tham số đường dẫn — ✅ ĐÃ SỬA (2026-08-05)

**Bằng chứng:** `config._nap_file()` cache vào một biến duy nhất và bỏ qua tham số `path`; `retrieval._get_collection()` giữ một `PersistentClient` và bỏ qua `chroma_path`. Lần gọi thứ hai với đường dẫn khác vẫn trả dữ liệu cũ — tham số hứa một đằng, hàm làm một nẻo.

**Ảnh hưởng lên kết quả hiện tại: KHÔNG có** — production chỉ có một `scoring.yaml` và một thư mục Chroma, còn test `retrieve()` thì tiêm `collection=` nên không đi qua chỗ hỏng. Ghi vào nhóm B chứ không phải C vì nó cùng loại **bẫy im lặng** với B6: không sai gì cho tới lúc có khoá/KB thứ hai, và lúc đó hiện ra ở dạng khó chẩn đoán nhất — đọc đúng file, ra sai nội dung.

**Đã sửa:** cả hai cache khoá theo đường dẫn. 2 test mới, mỗi test kiểm cả hai chiều (file mới đọc đúng, file cũ không bị đè).

> **Ghi chú 2026-08-05:** `retrieval._get_collection()` nói ở trên **không còn tồn tại** — kho vector đã chuyển sang Postgres + pgvector (`rag-design.md` mục 4.2a). Phép kiểm không bị mất theo: nó chuyển sang `db.get_conn()` (cache khoá theo **DSN** thay vì theo đường dẫn thư mục), và test khoá lại nằm ở `scripts/test_retrieval.py::test_ket_noi_cache_theo_dsn`. Giữ nguyên đoạn trên làm bản ghi của lỗi gốc.

### B12. Blacklist CP1 veto oan 10/13 bài — ✅ ĐÃ SỬA (2026-08-10)

**Bằng chứng (đo được, không phải suy luận):** chạy `match_blacklist()` trên 33 mẫu gold set — **13 bài sinh flag `critical`, chỉ 3 bài vi phạm thật**. Precision **0,21**.

10 bài bị chặn oan, tất cả đều là cách dùng hợp lệ:

| Bài | Đoạn khớp | Thực chất |
|---|---|---|
| G-003 | "cách **tốt nhất** để khắc phục sự cố" | trạng ngữ |
| G-005, G-006, G-008 | "giữ pin ở **trạng thái tốt nhất**" | lời khuyên bảo dưỡng |
| G-009 | "Thời gian **sạc nhanh nhất**" | **tiêu đề cột bảng thông số** |
| G-012, G-013 | "áp dụng **duy nhất** 01 Gói cố định" | lượng từ trong điều khoản |
| G-004, G-016, P-003a | "ánh sáng **tốt nhất**", "chăm sóc xe **tốt nhất**" | trạng ngữ |

**Vì sao là nợ nặng chứ không phải sai số chấp nhận được:**

- Flag `critical` → Aggregator veto → `rejected` **bất kể điểm tổng**. Đây là đường rủi ro cao nhất của hệ thống, và nó đang sai 10/13 lần.
- **Calibration KHÔNG sửa được.** E5 quét ngưỡng trên `final_score`, nhưng veto đi vòng qua ngưỡng — 10 bài đó không ngưỡng nào chạm tới. Chạy E5 trước khi sửa thì mọi ngưỡng đều trông tệ vì lý do không liên quan tới ngưỡng.
- 9 trong 13 bài ứng viên `publish` (sau khi v1.3 khôi phục lớp này) nằm đúng trong nhóm bị veto oan — tức lớp `publish` vừa cứu được ở guideline v1.3 sẽ bị CP1 xoá lần nữa.
- **Test cũ không phủ.** 13 ca trong `test_compliance_rules.py` chỉ kiểm *số lượng* flag `match_blacklist()` trả về, không kiểm mức CP1 suy ra từ đó.

**Đã sửa:** tách CP1 thành mức 0 (có nêu phạm vi so sánh → `critical`, vẫn veto) và mức 1 (không nêu phạm vi → `low`, không veto). Cùng hình dạng lập luận với CP3 mức 1 đã có sẵn trong rubric. Cờ `can_pham_vi` cho từng cụm trong `compliance_rules.json` phân biệt cụm so sánh nhất với cam kết tuyệt đối ("cam kết 100%", "an toàn tuyệt đối" — vi phạm không cần phạm vi). Sau khi sửa: precision **1,00**, recall giữ **1,00**.

**Đánh đổi đã biết:** claim thật không nêu phạm vi rơi xuống mức 1 — vẫn sinh flag `low` cho người duyệt thấy, chỉ thôi tự động từ chối. Có test khoá đúng ca đó.

**Cảnh báo về con số 1,00:** quy tắc được thiết kế bằng cách nhìn chính 33 mẫu này, nên precision/recall tuyệt đối trên chúng **là fit vào tập test, không phải bằng chứng tổng quát hoá**. Đã kiểm thêm 13 ca tự soạn ngoài corpus: 11/13 đúng, 2 ca trượt đều là đánh đổi đã biết ở trên. Con số đáng tin sẽ đến từ E6 (held-out).

**Bài học, cùng họ với B8:** cả hai lần đều là *lớp phòng vệ tất định bị sai bởi chính giả định của nó*. B8 giả định "mọi cụm cấm bắt đầu và kết thúc bằng chữ"; B12 giả định "khớp chuỗi là đủ để kết luận vi phạm". Và cả hai lần bộ test đều xanh suốt, vì test kiểm *cơ chế khớp* chứ không kiểm *kết luận rút ra từ nó*.

#### B12b. Mặt còn lại: CP1 bỏ sót claim không có trong blacklist — ⚠️ CHƯA SỬA, CỐ Ý

B12 đo **precision**. Mặt **recall** có một ca đã bắt được bằng tay khi gán nhãn gold set (2026-08-10), ghi lại vì nó là bằng chứng thật chứ không phải suy luận.

**Bài G-011** chứa câu:

> *"Chính sách bảo dưỡng xe máy điện tại VinFast hiện đang là ưu đãi **có một không hai** dành riêng cho khách hàng, **không có ở bất kì loại xe điện hãng khác trên thị trường**."*

Người gán nhãn xếp đây là **A1** (khẳng định độc nhất, có nêu phạm vi "trên thị trường") → nhãn `rejected`. Nhưng cụm *"có một không hai"* **không có trong `compliance_rules.json`**, nên CP1 sẽ báo sạch → AI đề xuất `needs_revision`. Đây là **false negative trên đúng đường veto**.

Ca này cũng cho thấy giới hạn của cả `scripts/quet_ung_vien.py`: danh sách mẫu độc lập của nó cũng không có cụm đó.

**Ca thứ hai, tìm được cùng đợt — G-020:**

> *"…cơ hội sở hữu mẫu xe được **săn đón nhất thị trường** xe xanh…"*

Cũng thoả cả hai điều kiện A1 (nêu phạm vi + nói về sản phẩm VinFast), cũng **không có trong blacklist**, cũng dẫn tới `rejected` theo nhãn người nhưng CP1 sẽ báo sạch.

**Hai ca độc lập trong 20 bài thật (10%) cho thấy đây không phải cá biệt.** Blacklist 19 cụm phủ được các cách nói phổ biến ("tốt nhất", "số 1", "duy nhất") nhưng tiếng Việt có vô số biến thể diễn đạt cùng ý — *"có một không hai"*, *"săn đón nhất"*, và chắc chắn còn nữa. Đây là **giới hạn bản chất của cách đo bằng danh sách cụm cố định**, không phải một lỗi vá được bằng cách thêm vài dòng.

Hướng xử lý sau Sprint 3, ghi lại để không quên: cách duy nhất phủ hết là chuyển CP1 sang **nhận diện ngữ nghĩa** (LLM xác nhận "câu này có phải claim so sánh nhất không") thay vì so khớp chuỗi. Nhưng nó đánh đổi đúng thứ B12 vừa bảo vệ — tính tất định và khả năng miễn nhiễm prompt injection của CP1 (`prompt-injection.md` mục 4c). Không làm trong phạm vi hiện tại.

**⚠️ CỐ Ý KHÔNG SỬA — thêm cụm này vào blacklist bây giờ là rò rỉ dữ liệu.** Gold set tồn tại để **đo** AI. Bổ sung luật dựa trên nội dung đọc được từ chính gold set thì lúc đo, AI bắt được — nhưng chỉ vì đã được mách đáp án, và recall thu được không nói lên gì về nội dung chưa thấy. Muốn mở rộng blacklist thì lấy mẫu từ **nguồn độc lập** (văn bản Luật Quảng cáo, corpus ngoài 33 mẫu), không lấy từ đây.

**Giá trị của việc ghi lại:** khi chạy AI trên gold set ở Sprint 3, G-011 chắc chắn lệch. Có ghi chép này thì kết luận rút ra được ngay — *"lệch vì blacklist thiếu cụm, không phải vì cơ chế hỏng"* — thay vì phải điều tra lại từ đầu. Đây là chẩn đoán, không chỉ là một con số xấu.

### B13. Năm tiêu chí gần như không mang thông tin trên corpus hiện tại — ⚠️ CHƯA SỬA, CỐ Ý

**Bằng chứng:** chạy khô phần tất định của Brand Voice trên 33 mẫu gold set (stub BV6 để không gọi LLM, $0):

| Mã | mức 0 | mức 1 | mức 2 | NA | Nhận xét |
|---|---|---|---|---|---|
| BV1 tên model | 0 | 0 | 21 | 12 | **chưa bao giờ phát hiện gì** |
| BV2 thuật ngữ | 1 | 0 | 32 | 0 | bắt đúng P-007a (bài chèn B5) ✅ |
| **BV3 nhất quán xưng hô** | **14** | **19** | **0** | 0 | **không bài nào đạt** |
| BV4 khớp corpus | 0 | 0 | 0 | 33 | NA vĩnh viễn, đã có tài liệu |
| BV5 viết hoa title | 0 | 0 | 33 | 0 | **chưa bao giờ phát hiện gì** |
| BV7 từ bị loại | 0 | 0 | 33 | 0 | **chưa bao giờ phát hiện gì** |

Điểm Brand vì thế nén trong dải hẹp **70–90**, dù trọng số của nó là 0,25.

**Sau khi chuyển SEO/CQ sang rubric (2026-08-10), thêm hai tiêu chí cùng loại:**

| Mã | mức 0 | mức 1 | mức 2 | Nhận xét |
|---|---|---|---|---|
| **SEO10** internal link | 0 | 0 | **33** | mọi bài đều có ≥3 link; ít nhất là 3, nhiều nhất 81 |
| **CQ5** cấu trúc heading | 0 | 0 | **33** | mọi bài đều có `<h2>` đúng phân cấp |

Tổng cộng **5 tiêu chí** không phân biệt được bài nào với bài nào: BV1, BV5, BV7, SEO10, CQ5 (luôn mức 2) và BV3 (không bao giờ đạt mức 2).

**Một ca CÙNG HÌNH DẠNG nhưng đã sửa, để đối chiếu:** CQ3 (câu quá dài) ban đầu cũng cho **33/33 mức 0**. Khác biệt là ở đó **tìm được lập luận không nhắc tới phân bố**: ngưỡng 30 là quy ước readability tiếng Anh vốn đếm **từ**, còn phép đếm ở đây là `len(s.split())` trên tiếng Việt viết rời từng âm tiết, tức đếm **tiếng**. Đổi sang 45 tiếng (≈30 từ, đúng chuẩn gốc) cho phân bố **13/14/6**.

Đó cũng là phép thử để phân biệt "sửa cho đúng" với "chỉnh cho phân bố đẹp": **lý do phải phát biểu được mà không cần nhắc tới phân bố thu được.** Với 5 tiêu chí ở trên thì không phát biểu được — chúng luôn mức 2 vì nội dung của VinFast thật sự đạt ở những điểm đó — nên **không đụng tới**.

**Chẩn đoán BV3 — cùng họ lỗi với B12.** `_UNG_VIEN_XUNG_HO = ["bạn", "quý khách", "khách hàng", "người dùng"]`, và mức = 2 nếu bài chỉ dùng 1 kiểu, 1 nếu 2 kiểu, 0 nếu ≥3. Nhưng **"khách hàng" và "người dùng" là danh từ ngôi thứ ba, không phải cách xưng hô ngôi thứ hai**. Bài cẩm nang nào cũng viết *"người dùng nên sạc pin…"* và *"khách hàng có thể đặt cọc…"* — hai cụm chỉ hai đối tượng khác nhau, không phải xưng hô lẫn lộn. Nên gần như mọi bài có ≥2 "kiểu" và **0/33 đạt mức 2**.

Giống hệt hình dạng của B12: **một bộ so khớp từ vựng gộp hai cách dùng ngôn ngữ khác nhau.** B12 gộp so-sánh-nhất-làm-claim với so-sánh-nhất-làm-trạng-ngữ; BV3 gộp xưng-hô với danh-từ-chỉ-người.

**Vì sao CỐ Ý chưa sửa, khác với B12:**

1. **Không gây quyết định sai.** Brand không có quyền phủ quyết; BV3 chỉ dịch điểm xuống đều cho mọi bài, mà calibration hấp thụ được bằng cách hạ ngưỡng. B12 thì tạo ra 10 lần **từ chối oan** mà không ngưỡng nào chạm tới.
2. **Sửa cần một quyết định thiết kế thật, có bẫy vòng luẩn quẩn.** "Xưng hô" nghĩa là gì trong văn marketing tiếng Việt — *"Khách hàng có thể đặt cọc"* là xưng hô với người đọc hay mô tả khách hàng nói chung? Thu hẹp danh sách cho tới khi phân bố đẹp chính là lỗi B9 lặp lại.
3. **Đang khoá code.** Mỗi lần sửa Brand là một lần phải đo lại E1 (`evaluation-plan.md` mục 3a).

**Hệ quả phải nêu khi báo cáo:** Brand Voice đóng góp rất ít khả năng phân biệt vào điểm tổng ở phạm vi hiện tại — 0,25 trọng số của nó gần như là một hằng số cộng thêm. Điều này cần nói khi diễn giải kết quả E5, vì nó ảnh hưởng cách đọc trọng số đã calibrate.

*(BV1/BV5/BV7 luôn ở mức 2 thì khác BV3: chúng là tiêu chí "không được có X" trên nội dung do đội content chuyên nghiệp viết, nên không tìm thấy vi phạm là kết quả hợp lý — chỉ là chúng không giúp phân biệt bài nào với bài nào.)*

---

## 4. Nhóm C — Chưa tới lượt (không phải nợ)

| Hạng mục | Ghi ở đâu | Ghi chú |
|---|---|---|
| ~~Polling worker + Content Moderation "Needs Review"~~ | `architecture.md` mục 9 | ✅ **xong 2026-08-07** — đường chính đã là event-driven, polling giữ lại làm lưới an toàn. Bằng chứng chạy thật: `docs/evidence/tu_dong_hoa_e2e.txt`. Cảnh báo `USAGE_LOG` đã được xử lý đúng như lưu ý cũ: `worker.py` `clear()` list này trong khối `finally` sau **mỗi** job (không chỉ đường thành công), kèm cảnh báo log nếu job hỏng giữa chừng mà đã tiêu token trước khi kịp ghi `run_log` |
| Nhật ký truy vết JSONL | `operations.md` mục 2 | ✅ **xong 2026-08-07** — đã đổi kết luận sang bảng Postgres `run_log` (không phải JSONL), lý do đổi: `operations.md` mục 2.4 |
| Vòng phản hồi người duyệt | `operations.md` mục 3 | Chưa triển khai — không còn hạng mục nào chặn |
| ~~KB fact-check chưa verify số thật~~ | `sources.md` mục 2.1 | ✅ **xong 2026-08-04** — 4/4 entry `verified: true`. Tìm ra 3 chỗ sai, trong đó `sources.md` nói **ngược** sự thật về chuẩn đo. Còn một rủi ro không khử được: VinFast công bố **ba** con số khác nhau cho VF 5 Plus |
| Bật lại CSS/JS aggregation trong Drupal | `pre-demo-checklist.md` mục 1 | Đang **tắt** từ lúc làm module `vf_ai_review`. Không phải nợ — là cấu hình dev, nhưng để nguyên lúc demo thì trang admin tải chậm thấy rõ |
| Mở rộng corpus `BRAND` | `sources.md` mục 1.7 | Chỉ làm nếu có quy ước rơi vào vùng chưa đủ căn cứ. Hiện "trạm sạc" ở 9/11 (p = 0,065) — **cố ý không thu thêm** vì đó là *optional stopping* |

---

## 5. Nhóm D — Phép đo chưa chạy

| Mã | Đo gì | Trạng thái |
|---|---|---|
| **E1** | Độ ổn định điểm qua nhiều lần chấm | ✅ **đạt** (2026-08-04) — điểm tổng σ = 0,28; 100% giữ nguyên quyết định. ⚠️ **Cần chạy lại phần Brand** sau B7 (2026-08-05): số σ Brand hiện có đo trên code cũ |
| **E2** | Retrieval lấy đúng đoạn (recall@k) | ✅ fact-check 1.00; brand 78,3% vs mốc 21,7% |
| **E3** | Multi-agent có hơn single-agent không | ❌ chưa — cần gold set |
| **E4** | Chi phí và độ trễ mỗi bài | ✅ **đo rồi** (2026-08-04) — TB **$0,057**/bài (~37,9k token vào), dải theo bài **$0,033–0,089** |
| **E5** | Ngưỡng quyết định tối ưu (calibration) | ❌ chưa — gold set **đã có nhãn** (A3 xong 2026-08-10). Còn chặn bởi: test-retest (≥2026-08-13) và đo lại E1 sau khi khoá code. ⚠️ Chỉ calibrate được **ngưỡng 50**; ngưỡng `publish` = 80 không đủ mẫu, xem mục 6 |
| **E6** | Held-out test | ❌ chưa — sau E5 |

**E4 làm lộ hai sai số trong tài liệu — ✅ đã sửa cả hai (2026-08-04), `evaluation-plan.md` mục 4.4:**

1. Ước tính ban đầu $0,025/bài và ~12k token — **hụt khoảng 2×** so với số đo thật. Nguyên nhân: phép nhân "4 agent × 3k token" bỏ sót đoạn KB mà RAG nhét thêm vào prompt của Compliance và Brand Voice.
2. Bản sửa lần đầu lại ghi dải `$0,042–0,052` và `28–38k token`, tức **lấy giá trị trung bình làm cận trên** — trung bình thật ($0,0565 và 37.894 token) nằm *ngoài* dải đó, nên nó không thể đúng về mặt số học. Đã tính lại trực tiếp từ `e1_stability_raw.json`: TB **$0,057**, dải theo bài **$0,033–0,089** (chênh 2,7× giữa bài ngắn nhất và dài nhất, gần như hoàn toàn do độ dài bài).

Bảng ngân sách trong mục đó cũng đã đổi từ *ước tính* sang **số thật cộng từ `usage`**: đã tiêu $8,33 cho 165 lượt chấm, dự kiến cả chương trình ~$11.

**Bài học chung của cả hai lần:** con số nào trong tài liệu cũng phải **tính ra được từ một file trong `docs/evidence/`**. Cả hai lần sai đều đến từ việc chép tay một con số thay vì tính lại từ dữ liệu — đúng loại lỗi mà `scoring.yaml` sinh ra để chặn, nhưng ở tài liệu thì chưa có cơ chế tương đương.

**Một phát hiện ngoài dự kiến trong lúc chạy E1:** khi API Anthropic hết hạn mức giữa chừng, **chỉ Brand Voice còn chấm được** (6/7 tiêu chí của nó là regex, không cần LLM); 3 agent kia hỏng hoàn toàn. Đây là kiểm chứng ngoài đời thật cho thiết kế *suy giảm có kiểm soát* ở `architecture.md` mục 6.4 — không phải thí nghiệm có chủ đích, nhưng đáng ghi.

**Phát hiện thứ hai, trùng loại, trong lúc chạy E2E tự động hoá (2026-08-07/08, `docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 7):** khởi động worker với `ANTHROPIC_API_KEY` **sai** (ghi đè biến môi trường tiến trình, `.env` không đổi) rồi chuyển một bài sang Needs Review — job **không** rơi vào dead-letter mà vẫn `done` với điểm suy giảm, vì Compliance và Brand Voice dùng rubric tất định (không gọi LLM cho phần lõi chấm điểm), chỉ Content Quality và SEO thiếu do key sai; `missing_agents = 2 < 4` nên pipeline coi là "chấm được một phần" đúng thiết kế fail-safe, `run_log` xác nhận `usage = []` (không tốn tiền API thật ở lần thử này). Hai lần quan sát độc lập, hai nguyên nhân khác nhau (hết hạn mức và sai key), cùng xác nhận một hành vi thiết kế ở `architecture.md` mục 6.4.

---

## 6. Giới hạn cố ý, không phải nợ

Những thứ dưới đây là **quyết định có cân nhắc**, ghi ở đây để không bị hiểu nhầm là thiếu sót:

| Giới hạn | Lý do |
|---|---|
| Với bài **đã xuất bản** rồi tạo bản nháp mới đưa sang Needs Review, `worker.py` chấm nhầm nội dung **bản cũ đã xuất bản**, không phải bản nháp mới | Cả đối soát lẫn worker đều đọc nội dung qua JSON:API, mà JSON:API trả về **revision mặc định** của node — với workflow `needs_review` có `default_revision = false`, revision mặc định vẫn là bản đã xuất bản. Đường **event bắn đúng** (hook tính `content_hash` trực tiếp từ revision vừa lưu, không qua JSON:API) — nhưng `worker.py` gọi `fetch_content()` (JSON:API, không `resourceVersion`) để lấy nội dung đưa vào pipeline, nên với bài đã xuất bản nó **chấm sai nội dung** dù hash gửi kèm job là đúng. Đây là giới hạn đã biết, không phải mất bài hoàn toàn (job vẫn chạy, vẫn ghi kết quả) mà là chấm nhầm bản. Cách khắc phục triệt để — đổi `fetch_content()` sang `?resourceVersion=rel:working-copy` — **cố ý chưa làm** trong đợt tự động hoá này, đó là một quyết định thiết kế riêng ngoài phạm vi. Trong lúc chờ, `worker.chay_mot_job()` so `content_hash` của nội dung THẬT đã fetch với `content_hash` của job và ghi `logging.warning` khi hai giá trị lệch nhau — đó là thứ làm giới hạn này **lộ ra** thay vì âm thầm ghi sai `run_log` vĩnh viễn |
| Shadow-test thật (E6) không làm được | Cần Drupal thật của VinFast, đội content thật, luồng duyệt thật — dự án không được cấp. Thay bằng held-out test (`evaluation-plan.md` mục 4.6) |
| Gold set do **một người** gán nhãn | Không được cấp nhân sự. Dùng Kappa test-retest làm trần thay cho Kappa người-người, và nêu rõ đó là ước lượng lạc quan |
| **Gold set KHÔNG CÓ lớp `publish`: 0/33 → ngưỡng `publish` KHÔNG calibrate được** | Đo được, không phải ước lượng: **0/20 bài thật đạt `publish`**. Lần gán đầu ra 2 bài, nhưng đợt rà lại có hệ thống (33 bài × 16 mã, 2026-08-10) tìm ra lỗi B8 ở **cả hai** — xem A3.<br><br>**Nguyên nhân đo được, không phải phỏng đoán: B8 có ở 10/20 bài thật (50%).** Lỗi chính tả và lặp từ phổ biến tới mức không bài nào qua nổi cửa đó. Vì vậy **thu thêm bài từ cùng nguồn gần như chắc chắn không cứu được lớp `publish`** — nó không phải vấn đề cỡ mẫu mà là **tính chất của nội dung**. Đã cân nhắc thu thêm ~30 bài (≈7 giờ gán nhãn, thu thủ công vì WAF chặn bot) và **bác bỏ**: kỳ vọng thu về 0-1 mẫu `publish`.<br><br>**Điều làm giới hạn này chấp nhận được:** quy tắc quyết định có hai ngưỡng, và cái calibrate được lại là cái quan trọng hơn. Ngưỡng **50** (`rejected` ↔ `needs_revision`) có phân bố **10/23** — đủ để quét, và nó chính là ngưỡng gắn với **quyền phủ quyết**, tức phần rủi ro pháp lý. Ngưỡng **80** chỉ phân biệt "đề xuất đăng luôn" với "đề xuất xem lại", mà hệ thống **không bao giờ tự xuất bản** (`architecture.md` mục 2.3) nên hậu quả sai thấp hơn hẳn.<br><br>**Phải nêu trong báo cáo Sprint 3:** *"ngưỡng `publish` = 80 giữ nguyên giá trị minh hoạ, chưa calibrate, do gold set không có mẫu `publish` nào"*. Và nêu kèm phát hiện nghiệp vụ đi cùng: **20/20 bài cẩm nang đã xuất bản của VinFast đều cần ít nhất một chỉnh sửa** — đó chính là lý do công cụ này đáng tồn tại.<br><br>**Hai cách làm đã cân nhắc và BÁC BỎ**, ghi lại vì cả hai đều hấp dẫn: (1) *sửa nội dung bài cho sạch rồi gán `publish`* — gold set là thước đo, sửa bài tới khi ra nhãn mong muốn là mài lại thước; khác perturbation ở chỗ chèn lỗi thì biết chính xác đã thêm gì (`injected_codes`), còn dọn sạch thì không bao giờ chắc đã hết. (2) *nhờ AI duyệt web tìm bài sạch* — sàng lọc theo chất lượng làm mẫu mất tính đại diện, và tệ hơn là sàng theo tiêu chí giống rubric nên gold set thành tương quan với chính hệ thống đang bị đo. |
| Con số `publish` thấp phản ánh chất lượng nguồn, không phải lỗi rubric | Kiểm bằng chính định nghĩa: các mã đẩy bài xuống `needs_revision` đều là **lỗi phải sửa thật** — B3 (meta sai độ dài, 30% bài thật), B8 (lỗi chính tả: `"hành trinh"`, `"viêc"`, `"thông suất"`, `"khuyến cáokhách"` — đều đã đối chiếu `raw_html` xác nhận có trong nguồn gốc), B2 (thời gian sạc thiếu loại trụ). Khác hẳn B9 trước đây — B9 sai vì "câu dài" là **văn phong**, không phải lỗi. Đã cân nhắc nới B8 xuống và **bác bỏ**: một lỗi chính tả đúng là thứ phải sửa trước khi đăng, nới nó là lặp lại bẫy chỉnh ngưỡng cho phân bố đẹp |
| **Không kiểm được "AI có báo lỗi giả trên bài sạch không"** — vì gold set không có bài sạch nào | Đây là **phản biện mạnh nhất** với việc lớp `publish` rỗng, và gold set không trả lời được. Nhưng `architecture.md` mục 8.1 đã thiết kế sẵn chỗ khác cho nó: **bộ mẫu kiểm thử chức năng**, dòng đầu tiên của bảng là *"Bài sạch \| (không) \| Không báo lỗi giả"*. Mục đó ghi rõ bộ này **tách biệt với gold set** và cho phép tạo mẫu nhân tạo — *"thêm mẫu rẻ: không cần gán nhãn mù, không cần test-retest, không đếm vào 33"*.<br><br>**Phân vai phải giữ rõ, vì lẫn hai thứ này là gốc của mọi tranh cãi ở trên:**<br>• **Gold set** trả lời *"AI có khớp nhãn người không?"* → mẫu BẮT BUỘC là bài thật, không sửa, không sàng lọc.<br>• **Bộ kiểm thử chức năng** trả lời *"AI có bắt đúng / không bắt oan loại lỗi này không?"* → được phép TỰ DỰNG mẫu, vì nó không tham gia calibration và không tính Kappa.<br><br>**Việc cần làm (chưa làm):** dựng 1 bài sạch cho bộ chức năng — lấy một bài thật rồi sửa hết lỗi — và xác nhận hệ thống trả `publish`. Nó chứng minh **hệ thống CÓ đường ra `publish`**, chỉ là nội dung thật của VinFast không đi qua đó. Đây đúng là thao tác "sửa bài cho sạch" mà mục trên đã BÁC BỎ với gold set — hợp lệ ở đây chính vì bộ chức năng có mục đích khác: nó kiểm *cơ chế*, không đo *mức đồng thuận*. |
| Brand guideline tự trích xuất, không phải tài liệu nội bộ | Dự án không được cấp tài liệu nội bộ VF O2O |
| Quy ước "trạm sạc / trụ sạc" để `NA` | Thu thêm corpus để đẩy p qua ngưỡng là *optional stopping* — làm mọi p-value mất giá trị |
| `url_alias` không nằm trong `content_hash` | Bên PHP phải tra bảng `path_alias` riêng; thêm phức tạp để bắt trường hợp hiếm |
| Chưa hiển thị `criteria` chi tiết của Brand Voice trong UI | Dữ liệu đã có trong pipeline, chờ xem giao diện thật rồi mới quyết |
| Hoàn tác nội dung → kẹt: một cặp `(node, hash)` đã chấm xong (`done`) không bao giờ được chấm lại bằng đường tự động | Index dedup phủ cả `done`. Editor sửa C1→C2 rồi hoàn tác về C1: hook và đối soát đều gửi job cho hash của C1, nhưng đều bị `duplicate` vì `(node, hash_C1)` đã có job `done` từ trước khi sửa — node giữ nguyên report của C2, băng "nội dung đã thay đổi" **không bao giờ tắt**. Lối thoát duy nhất là nút "Chấm lại" thủ công — mà `content_editor` (chỉ có quyền `xem bao cao ai`) không có quyền bấm. Trớ trêu: `audit.da_cham()` vẫn còn payload đúng của C1 trong `run_log`, ghi lại tốn 0 đồng, nhưng đường tự động không tới được đó |
| Với bài **đã xuất bản** đang được sửa lại, mỗi lần bấm Save đều tốn tiền API — chốt chặn tiền không cứu được | Hệ quả trực tiếp của việc sửa lỗi ghi `run_log` theo hash nội dung thật (mục 6 dòng trên). Trước khi sửa, `audit.ghi()` ghi theo hash do hook gửi, nên mọi job sau có cùng hash job đều `da_cham()` trúng và không tốn thêm đồng nào — nhưng cái "trúng" đó phục vụ **kết quả của nội dung khác**, sai vĩnh viễn và im lặng. Sau khi sửa, `run_log` mang hash của nội dung thật đã chấm, nên trong đúng ca lệch revision này `da_cham(node, hash_job)` **không bao giờ khớp** → Save lại là chấm lại thật. **Đây là đánh đổi có chủ đích:** thà lộ ra và tốn tiền còn hơn âm thầm trả về điểm của một bài khác. Đo được bằng script tái hiện trên Postgres thật lúc re-review đợt sửa cuối. Khắc phục triệt để cùng chỗ với dòng trên: cho `fetch_content()` đọc `?resourceVersion=rel:working-copy` |
| `job_queue.enqueue(force=True)` có khe hở nguyên tử hiếm gặp dưới tải đồng thời | Nhánh `force=True` mở `conn.transaction()` tường minh trên connection dùng chung (`db.get_conn()` cache theo DSN), trong khi handler FastAPI chạy đồng bộ trong threadpool. Nếu đúng lúc đó có hai POST đồng thời và một cái là `force=True`, INSERT của luồng kia có thể lọt vào transaction của luồng force và biến mất nếu transaction đó rollback. Xác suất thấp ở quy mô một editor thao tác tuần tự, chưa xử lý vì chưa quan sát được trong thực tế |

---

## 7. Thứ tự đề xuất

```
[x] 1. E1 + E4  (độ ổn định, chi phí)   <- xong 2026-08-04
[x] 2. A2  (SEO đọc alt trong body)     <- xong 2026-08-04
[x] 3. B1  (tách config)                <- xong 2026-08-04
--------- sắp lại sau khi có số liệu E1 ---------
[x] 4. A1-compliance  (rubric CP1–CP8)  <- xong 2026-08-04: σ tổng 1,33 ĐẠT,
                                           σ Compliance 4,18 còn nợ (mục A1)
[x] 5. B5  (CP8 mức 2 + trích dẫn nhiều mảnh)  <- xong 2026-08-04, $0,92:
                                                  ghi đè oan 20 -> 4, nhưng
                                                  σ 7,70 -> 7,29. B5 KHÔNG
                                                  phải nguyên nhân của σ
[x] 6. B4  (ngưỡng meta/body trong prompt SEO)  <- xong 2026-08-04, có test
                                                  hợp đồng khoá lại
[x] 7. Con số chi phí ở evaluation-plan.md mục 4.4  <- xong 2026-08-04; tìm
                                                      thêm 1 sai số thứ hai
                                                      (dải lấy TB làm cận trên)
[x] 8. B8  (2 cụm blacklist critical chết vì \b)   <- xong 2026-08-05, không
                                                      tốn API; test cũ xanh
                                                      suốt vì không phủ hình
                                                      dạng cụm kết thúc bằng '%'
[x] 9. B9 + B10 + B11  (index CP3, chặn biên score, cache theo path)
                                                <- xong 2026-08-05, không tốn
                                                   API; B9 làm lộ thêm lỗi
                                                   "thiếu verdict -> mức 2"
[x] 10. B7  (BV6 kiểm trích dẫn)  <- xong 2026-08-05: tách
                                     text_utils.trich_dan_co_that dùng chung.
                                     SINH RA việc mới: E1-Brand phải đo lại
[x] 11. B6  (graph.py truyền content_type/langcode)  <- xong 2026-08-05, gộp
                                                       về _khoa_cua(), có test
[x] 16. Tự động hoá Needs Review + nhật ký truy vết  <- xong 2026-08-07, event-
                                                        driven + đối soát an
                                                        toàn, xem architecture.md
                                                        mục 9
[x] 17. B12 (CP1 veto oan 10/13 bai)  <- xong 2026-08-10, khong ton API:
                                        precision 0,21 -> 1,00. PHAI xong
                                        truoc E1 (doi diem Compliance) va
                                        truoc E5 (veto di vong qua nguong)
---- chờ mentor ----
   12. A3  (gán nhãn gold set)  <- KHONG con bi chan: guideline v1.3 +
                                   scripts/quet_ung_vien.py, chi 20/33 bai
                                   phai doc
   13. E3, E5, E6
---- không chặn gì, làm lúc nào cũng được ----
   14. Đo lại E1-Brand sau B7  <- tốn API, chưa chạy
   15. A1-content_quality, A1-seo   <- E1 hạ ưu tiên: σ = 0,38 và 0,19
```

Lý do E1 đứng đầu, và kết quả của việc đó: nó **rẻ, không phụ thuộc gì**, và là thí nghiệm quyết định số phận của `rubrics.md`. Nếu điểm đã ổn định bất ngờ thì luận điểm chính của rubric yếu đi và nên biết **trước** khi bỏ công viết lại 3 prompt (`evaluation-plan.md` mục 3 điểm 2). **Đó đúng là chuyện đã xảy ra:** E1 cho thấy hai trong ba agent ổn định hơn dự kiến, nên công viết lại rubric giờ dồn vào **một** agent (Compliance) thay vì ba. Chạy E1 trước đã tiết kiệm khoảng hai phần ba khối lượng của A1.

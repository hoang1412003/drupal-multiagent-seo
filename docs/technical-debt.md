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

**Số đo thực nghiệm sơ bộ (2026-08-04):** cùng bài `node/1`, chấm 3 lần trong một ngày, cùng code, cùng model:

```
81.75  ->  79.25  ->  81.75
```

Dao động **2.5 điểm**. `docs/architecture.md` mục 8.2 dự kiến quét ngưỡng theo **bước nhảy 2 điểm** — dao động lớn hơn bước nhảy thì mọi ngưỡng chọn được đều là nhiễu.

**Cảnh báo khi trích số này:** đây là quan sát tình cờ trên **một bài, ba lần**, không phải phép đo có thiết kế. Chưa tách được dao động đến từ agent nào (BV6 cũng gọi LLM). Nó là *giả thuyết cần kiểm*, không phải kết luận — E1 (mục D1) mới là phép đo tử tế.

**Việc phải làm:** chuyển 3 agent sang rubric như Brand Voice — `docs/rubrics.md` mục 8 liệt kê chi tiết. Hai bẫy đã gặp khi làm Brand Voice, ghi ở mục 8.1 tài liệu đó: *thoả mãn rỗng* và *phân loại quá rộng*.

### A2. SEO Agent không đọc `alt` của ảnh nằm trong `body`

**Bằng chứng:** `src/drupal_client.py:44` — `_extract_image_alt()` chỉ đọc `relationships.field_image.data.meta.alt`. Ảnh nhúng trong chuỗi HTML của `body` không được bóc ra.

**Vì sao chặn:** mã lỗi **B6** trong `docs/goldset/annotation-guideline.md` v1.2 xét **mọi thẻ `<img>` trong `body`**, còn hệ thống chỉ xét **một ảnh đại diện**. Hai bên đo hai tập ảnh khác nhau → Recall/F1 của tiêu chí SEO9 lệch có hệ thống.

Đã ghi ở `docs/evaluation-plan.md` mục 4.5 điều kiện 4, kèm bằng chứng đo trên `node/7` (2026-07-30) và bài `G-001`.

### A3. Gold set chưa gán nhãn

**Trạng thái:** 33 mẫu đã thu, bóc tách, chèn perturbation. Cột `label` trong `docs/goldset/labels.csv` còn trống toàn bộ.

**Chặn bởi:** đang chờ mentor quyết quy trình. Người thực hiện thấy đọc + gán tay 33 bài quá tốn thời gian và đang hỏi mentor: giảm cỡ mẫu, cho phép AI gán nháp, hay giữ nguyên thủ công.

**Lưu ý bắt buộc:** không được dùng AI gán nháp nếu mentor chưa duyệt. `annotation-guideline.md` mục 2 yêu cầu **gán mù**; nhãn do AI nháp sẽ neo người gán và thổi phồng Cohen's Kappa mà cả Sprint 3 dựa vào.

---

## 3. Nhóm B — Nợ thật

### B1. Ngưỡng và trọng số chưa tách ra config

**Bằng chứng:** `src/graph.py:19` còn `WEIGHTS = {...}`; dòng 101–112 còn hard-code `< 50`, `>= 80`, `>= 50`. Thư mục `multiagent/config/` chưa tồn tại.

**Đã gây lỗi thật:** `docs/config-spec.md` mục 1 ghi cùng một tập số nằm ở **4 nơi** (`graph.py`, `label_helper.py`, `rubrics.md`, `annotation-guideline.md`) và **đã trôi lệch một lần** — mã B3 từng ghi `150-160` trong guideline trong khi rubric ghi `140-170`. Phát hiện tình cờ khi đối chiếu; nếu phát hiện sau khi đã gán 33 nhãn thì phải gán lại toàn bộ.

**Điểm chặn kèm theo:** `src/state.py` chưa có `content_type`/`langcode` (kiểm 2026-08-04: 0 lần xuất hiện). Thiếu hai trường này thì không tra config theo khoá `(content_type, langcode)` được.

### B2. Ba agent còn ghép prompt bằng nhãn text thuần

**Bằng chứng:** `content_quality.py`, `seo.py`, `compliance.py`, `fact_check.py` đều còn ghép chuỗi dạng `[title] ... [body] ...`.

**Rủi ro:** nhãn đó **giả mạo được** — người viết gõ đúng chuỗi vào body là xoá ranh giới giữa dữ liệu và chỉ dẫn. Nguy hiểm hơn: `body` là HTML nên chỉ dẫn giấu trong bình luận HTML **vô hình với người duyệt nhưng LLM vẫn đọc**. Phân tích đầy đủ: `docs/prompt-injection.md` mục 2–3.

**Đã làm được phần nào:** BV6 (`brand_voice.py`) dùng thẻ có hậu tố ngẫu nhiên — biện pháp **M1**. Ba agent kia chưa. **M3** (bóc phần ẩn trước khi đưa vào prompt) và **M2** (tiêu chí CP9 phát hiện chỉ dẫn ẩn) chưa làm.

**Giảm nhẹ sẵn có:** `docs/prompt-injection.md` mục 4 nêu ba thứ đang hạn chế hậu quả — structured output ràng buộc hình dạng đầu ra, hệ thống không tự xuất bản, và phần tất định (blacklist regex, Aggregator) miễn nhiễm hoàn toàn.

### B3. `score` của Compliance độc lập với `flags`

**Bằng chứng:** `src/agents/compliance.py` lấy `score` nguyên từ LLM, còn flag rule-based cộng thêm vào sau. Một bài dính 3 flag `critical` từ blacklist vẫn có thể mang `score = 95`.

**Vì sao quan trọng:** Compliance là agent duy nhất có quyền phủ quyết. `docs/rubrics.md` mục 6.1 chủ trương cả `score` lẫn `severity` phải tất định — severity tra bảng theo mã tiêu chí, không để LLM tự chọn, vì `critical` là thứ kích hoạt chặn xuất bản.

**Giảm nhẹ:** veto vẫn hoạt động độc lập với điểm, nên bài có flag `critical` vẫn bị chặn dù điểm cao. Nợ này ảnh hưởng *tính nhất quán của điểm*, không ảnh hưởng *quyết định chặn*.

---

## 4. Nhóm C — Chưa tới lượt (không phải nợ)

| Hạng mục | Ghi ở đâu | Ghi chú |
|---|---|---|
| Polling worker + Content Moderation "Needs Review" | `architecture.md` mục 9 | Sprint 2 còn lại. Không chặn gì |
| Nhật ký truy vết JSONL | `operations.md` mục 2 | Đã **hạ ưu tiên** 2026-08-03 sau khi phát hiện Drupal giữ revision — 3 field AI không mất, chỉ mất bối cảnh chấm |
| Vòng phản hồi người duyệt | `operations.md` mục 3 | Cần nhật ký truy vết xong trước mới khớp được `(node_id, scored_at)` |
| KB fact-check chưa verify số thật | `sources.md` mục 2.1 | **4/4 entry còn `verified: false`**. Cần mở trang thật đối chiếu |
| Mở rộng corpus `BRAND` | `sources.md` mục 1.7 | Chỉ làm nếu có quy ước rơi vào vùng chưa đủ căn cứ. Hiện "trạm sạc" ở 9/11 (p = 0,065) — **cố ý không thu thêm** vì đó là *optional stopping* |

---

## 5. Nhóm D — Phép đo chưa chạy

| Mã | Đo gì | Trạng thái |
|---|---|---|
| **E1** | Độ ổn định điểm qua nhiều lần chấm | ❌ **chưa** — chặn E5 |
| **E2** | Retrieval lấy đúng đoạn (recall@k) | ✅ fact-check 1.00; brand 78,3% vs mốc 21,7% |
| **E3** | Multi-agent có hơn single-agent không | ❌ chưa — cần gold set |
| **E4** | Chi phí và độ trễ mỗi bài | ❌ chưa — chạy được ngay |
| **E5** | Ngưỡng quyết định tối ưu (calibration) | ❌ chưa — cần gold set + E1 đạt |
| **E6** | Held-out test | ❌ chưa — sau E5 |

`evaluation-plan.md` mục 6 khuyến nghị thứ tự: **E1 + E4 trước tiên**, vì chúng chạy được ngay và E1 quyết định có phải viết lại 3 system prompt hay không.

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
1. E1  (độ ổn định)     <- rẻ (~$1.25), chạy ngay, quyết định có phải viết lại 3 prompt
2. A2  (SEO đọc alt trong body)   <- nhỏ, độc lập, gỡ điều kiện 4 của E5
3. A1  (rubric cho 3 agent)       <- lớn, làm sau khi E1 cho số liệu
4. B1  (tách config)              <- nên xong TRƯỚC E5 vì E5 phải quét nhiều bộ ngưỡng
5. E4  (chi phí/độ trễ)           <- rẻ, ghép vào lúc chạy E1
---- chờ mentor ----
6. A3  (gán nhãn gold set)
7. E3, E5, E6
---- không chặn gì, làm lúc nào cũng được ----
8. Polling worker, nhật ký truy vết, B2 (prompt injection M1/M3), B3
```

Lý do E1 đứng đầu: nó **rẻ, không phụ thuộc gì**, và là thí nghiệm quyết định số phận của `rubrics.md`. Nếu điểm hiện tại đã ổn định bất ngờ thì luận điểm chính của rubric yếu đi và nên biết **trước** khi bỏ công viết lại 3 prompt (`evaluation-plan.md` mục 3 điểm 2).

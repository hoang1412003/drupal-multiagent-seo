# Kế hoạch thí nghiệm và đo lường

**Phiên bản:** v1 (2026-07-27)
**Trạng thái (cập nhật 2026-08-14):** E2 và E4 còn hiệu lực. E1 và E5 đã từng chạy nhưng đều **hết hiệu lực với bản 4** sau chốt CP4 ngày 2026-08-12. Preflight E1 bản 4 đã đạt trên snapshot `04f10e1`/prompt `020738e209017213`, nhưng **không gọi API, không tạo output và không phải kết quả E1**.

⚠️ **Tính đến 2026-08-14, test–retest và E1 bản 4 VẪN CHƯA CHẠY.** Lượt trả phí từng được xếp cho 2026-08-13 nhưng chưa diễn ra; đừng đọc mốc ngày cũ thành "đã làm xong". Thứ tự bắt buộc không đổi: **test–retest mù trước, rồi mới E1**, và không được xem output E1 trước khi người gán khoá nhãn lượt hai.

E5 bản 3 đạt Kappa 0,713, accuracy 0,879, sai 4/33; đây là bằng chứng lịch sử đã giúp tìm B14/CP4, không phải kết quả của code hiện hành. Gold set 33/33. Còn E3/E6, E1/E5 bản 4 và test–retest nhãn.

**Luồng productization P1→P5 (hoàn tất 2026-08-14) KHÔNG ảnh hưởng hợp đồng đo lường này:** `prompt_version` vẫn `020738e209017213`, `git diff` score-path so với `04f10e1` vẫn rỗng, và không lần gọi Anthropic nào phát sinh. Mọi run sinh ra trong P1→P5 đều `is_fixture=true` do engine giả — **không phải kết quả chấm điểm** và không được đưa vào bất kỳ phép đo nào.

Gold set calibration: 33 mẫu (20 original + 13 perturbed), không có lớp publish.

Functional-clean: 10 mẫu corrected, expected publish, không tham gia E5/Kappa.

Evaluation suite: 43 mẫu, chỉ số phải báo cáo riêng theo lát dữ liệu.

---

## 1. Vì sao gom vào một tài liệu

Dự án có 6 phép đo phải chạy, nhưng chúng đang nằm rải rác: test-retest ở `rubrics.md` mục 9, recall@k ở `rag-design.md` mục 5, calibration ở `architecture.md` mục 8.2, shadow-test ở mục 8.3, còn baseline và chi phí thì chưa ở đâu cả.

Hệ quả của việc rải rác không phải là khó tra cứu, mà là **không ai nhìn thấy thứ tự phụ thuộc**. Có ít nhất hai chỗ mà chạy sai thứ tự sẽ phải làm lại toàn bộ:

- Calibration ngưỡng (E5) chạy trước khi biết điểm có ổn định không (E1) → ngưỡng chọn ra có thể chỉ là nhiễu
- Nối RAG vào agent trước khi đo recall@k (E2) → retrieval sai sẽ hiện ra dưới dạng "LLM chấm sai", dẫn đến sửa nhầm chỗ

Tài liệu này chốt: đo cái gì, bằng cách nào, tiêu chí đạt là bao nhiêu, và **theo thứ tự nào**.

---

## 2. Sáu phép đo

| Mã | Đo cái gì | Cần có trước | Tiêu chí đạt |
|---|---|---|---|
| **E1** | Độ ổn định điểm của agent qua nhiều lần chấm | Agent hiện có (đã xong) | σ điểm < 2 — **đã đo 2026-08-16: σ `final_score` = 1,60, ĐẠT** |
| **E2** | Retrieval lấy đúng đoạn không (recall@k) | KB đã dựng | recall@3 ≥ 0.9 (fact-check) — **đã đo: 1.00 (fact-check), 78,3% vs mốc 21,7% (brand)** |
| **E3** | Multi-agent có hơn single-agent không | Gold set | (không có ngưỡng) — **đã đo 2026-08-16: 4 agent thắng, Kappa CV 0,406 so với 0,302** |
| **E4** | Chi phí và độ trễ mỗi bài | Agent hiện có (đã xong) | (không có ngưỡng) — **đã đo 2026-08-16 kèm E1: $0,0567/bài, 39,3s/lượt** |
| **E5** | Ngưỡng quyết định tối ưu (calibration) | Gold set + **E1 đạt** | Kappa cao nhất trong dải quét — ⛔ **đã đo 2026-08-16 nhưng KHÔNG chốt được ngưỡng**, xem mục 4.5 |
| **E6** | Shadow-test trước khi vận hành | E5 | k-fold theo mục 4.6.1 — **đã đo 2026-08-16: selection bias +0,000** |

---

## 3. Thứ tự chạy

```
Chạy được NGAY (không phụ thuộc gì):
  E1  Độ ổn định điểm  ─────┐
  E4  Chi phí / độ trễ      │
                            │
Sau khi có gold set:        │
  E3  Baseline              │
  E5  Calibration  ◄────────┘  (E1 phải ĐẠT trước)
                              │
Sau khi dựng KB:              │
  E2  recall@k                │
                              ▼
Cuối cùng:                  E6  Shadow-test
```

Năm điểm chặn quan trọng:

1. **E1 chặn E5.** Nếu điểm dao động ±5 thì việc quét ngưỡng theo bước nhảy 2 điểm là vô nghĩa - mọi ngưỡng chọn ra chỉ là nhiễu.
2. **E1 cũng chặn việc implement rubric.** E1 là thí nghiệm quyết định số phận `rubrics.md`: nếu điểm 0-100 hiện tại đã ổn định bất ngờ thì luận điểm chính của rubric yếu đi, và nên biết **trước** khi viết lại 4 prompt.
3. **E2 chặn việc nối RAG vào agent** (`rag-design.md` mục 5).
4. ~~**Brand Voice Agent thật chặn E5.**~~ **ĐÃ GỠ (2026-08-03)** — `brand_voice.py` thay stub, không còn 25 điểm giả. Xem mục 4.5.
5. **SEO Agent đọc được alt của ảnh trong body chặn E5** (phần tiêu chí SEO9). Xem mục 4.5.

**E1 và E4 chạy được ngay hôm nay** - không phụ thuộc gold set, không phụ thuộc rubric, không phụ thuộc KB. Đây là hai phép đo duy nhất trong danh sách không bị chặn bởi gì cả.

---

## 3a. KHOÁ CODE CHẤM ĐIỂM — 2026-08-12 (bản 4)

`rubrics.md` mục 10 quy định: ngưỡng calibrate được **chỉ có hiệu lực với đúng bộ (rubric version, prompt version, model)** đã dùng lúc đo. Nên trước khi chạy E1 và E5 phải chốt bộ đó lại, và ghi ra để về sau kiểm chứng được.

**Bộ đã khoá:**

| Thành phần | Giá trị |
|---|---|
| Score-path snapshot | `04f10e1`: bản sửa **chốt CP4 tất định** (LLM chấm điều kiện + code kiểm thời hạn) và fix N1 double write-back. Có thể chạy từ descendant chỉ thêm tài liệu nếu xác minh diff đường chấm so với snapshot này rỗng; evidence vẫn phải ghi HEAD thực tế |
| Model | `claude-haiku-4-5-20251001` |
| Rubric version | v1 (`rubrics.md`) — **áp dụng cho cả 4 agent** |
| Prompt version | **`020738e209017213`** — tính từ code, phủ **6** prompt (4 agent + 2 của `fact_check`). Bản 3 là `0bdc5ab12ec65f89`; mọi file kết quả mang hash đó nay là dữ liệu lịch sử |
| Guideline gán nhãn | v1.3 (`annotation-guideline.md`) |
| Gold set | `labels.csv` 33/33, phân bố **10** `rejected` / **23** `needs_revision` / **0** `publish` (sau đợt rà lại 2026-08-10, xem `technical-debt.md` A3) |
| KB fact-check | **5 mục** (thêm VF e34 ngày 2026-08-10, nguồn độc lập với gold set). E2 recall@3 = 1,00 sau khi thêm |
| E1 | ⚠️ **CHƯA đo trên bản này.** Preflight ngày 2026-08-12 đạt nhưng không gọi API/không tạo output; số 1,79 thuộc code trước B14/CP4 hiện hành |
| E5 | ✅ **Đã đo 2026-08-16.** Kappa CV **0,406** với cấu hình đang chạy (`publish=80`), **0,713** nếu vô hiệu hoá nhánh `publish`. ⛔ **Không chốt được ngưỡng** — xem [`evidence/e5_e6_ban4_report.md`](evidence/e5_e6_ban4_report.md) và `technical-debt.md` mục 8.2 |
| E6 | ✅ **Đã đo 2026-08-16, $0.** k-fold theo thiết kế đăng ký trước ở mục 4.6.1. Selection bias **+0,000** — dự đoán out-of-fold trùng khít in-sample trên cả 33 mẫu |

> ### ⚠️ Bản khoá cũ có lỗ hổng — phát hiện khi sửa B14
>
> Công thức `prompt_version` của bản 1 và bản 2 chỉ băm **4 system prompt của 4 agent**. Nhưng CP3 gọi hai prompt riêng nằm trong `fact_check.py` (`_EXTRACT_PROMPT`, `_COMPARE_PROMPT`) — **không nằm trong phép băm**.
>
> Nghĩa là: **phần lớn bản sửa B14 nằm ở chỗ mà `prompt_version` không nhìn thấy.** Sửa xong hai prompt đó thì hash 4-agent vẫn có thể không đổi, và bản khoá sẽ khẳng định "cùng một bộ" trong khi hành vi chấm điểm đã khác hẳn — đúng thứ mà bản khoá sinh ra để chặn.
>
> Lần này hash 4-agent *có* đổi (do CP4 nằm trong `compliance._LLM_PROMPT`), nên lỗ hổng không gây hậu quả. Đó là **may, không phải thiết kế**.
>
> **Đã xử lý — công thức nay nằm trong CODE, không phải trong tài liệu:** hàm `eval_calibration.prompt_version()` là nguồn duy nhất. Chép công thức vào đây rồi cũng trôi lệch, đúng như `config-spec.md` mục 1 mô tả.
>
> **Và nó đã được dùng làm chốt chặn thật:** `eval_calibration.py` ghi `prompt_version` vào file kết quả, rồi **từ chối resume** nếu hash lệch. Chốt này sinh ra từ một cái bẫy có thật — script resume để khỏi trả lại $1,9, nhưng sau khi sửa B14 thì file cũ mang điểm của bản code khác; chạy tiếp sẽ **trộn điểm hai bản mà không ai nhìn ra**. File cũ nay đổi tên thành `e5_truoc_sua_cp3_cp4.json` và đánh dấu hết hiệu lực.

`prompt_version` là SHA-256 của **6** system prompt nối theo thứ tự tên. Kiểm bất cứ lúc nào:

```bash
.venv/Scripts/python.exe -c "import sys; sys.path[:0]=['scripts','src']; \
import eval_calibration as e; print(e.prompt_version())"      # phải ra 020738e209017213
```

**Thêm prompt ở module mới thì phải sửa `prompt_version()`** — nếu không, bản khoá sẽ khẳng định "cùng một bộ" trong khi hành vi đã đổi, đúng lỗi vừa mắc ở bản 1-2.

*(Công thức của bản 1 tham chiếu `content_quality.SYSTEM_PROMPT` và `seo.SYSTEM_PROMPT` — hai tên đó **không còn tồn tại** sau khi chuyển rubric. Đó là lần đầu công thức chép-tay này hỏng; lỗ hổng `fact_check` là lần thứ hai. Nên nay nó nằm trong code.)*

**Quy tắc trong thời gian khoá:** mọi thay đổi chạm vào đường chấm điểm — 4 agent, `scoring.py`, `graph.aggregator_node`, `compliance_rules.json`, `brand_rules.json`, `scoring.yaml` — đều **làm mất hiệu lực E1 và E5 đã chạy**, và phải đo lại. Sửa tài liệu, test, script gán nhãn thì không ảnh hưởng. Chốt CP4 vừa đổi đúng đường này, nên bản 4 chưa có E1/E5 hợp lệ.

`04f10e1` là **snapshot của đường chấm**, không phải yêu cầu HEAD phải đứng mãi ở đúng commit đó. Commit chỉ sửa tài liệu được phép là descendant nếu trước lượt đo đã chứng minh không có diff ở agent/fact-check/graph/scoring/config/rule/retrieval/KB so với snapshot; evidence phải ghi cả HEAD thực tế và score-path snapshot. Cách phân biệt này tránh việc một commit tài liệu làm mất hiệu lực phép đo, nhưng không cho phép núp thay đổi hành vi trong commit mang nhãn `docs`.

> #### Làm rõ nghĩa của "config" trong danh sách trên (thêm 2026-08-16 — làm rõ, **không đổi luật**)
>
> Danh sách liệt kê cụ thể ở đoạn trên ghi **`scoring.yaml`**, còn đoạn này ghi gọn là "config". Hai cách viết lệch nhau khi `multiagent/config/` có thêm file **không phục vụ việc chấm điểm** — đã xảy ra thật: P5 thêm `model_pricing.yaml` (đơn giá token cho dashboard chi phí).
>
> **Tiêu chí phân định — kiểm được bằng máy, không phải phán đoán:** một file trong `multiagent/config/` thuộc đường chấm **khi và chỉ khi có module thuộc đường chấm đọc nó**. Phải chạy phép kiểm này trước mỗi lượt đo và ghi kết quả vào evidence:
>
> ```bash
> grep -rn "<ten_file>" multiagent/src multiagent/scripts --include=*.py | grep -v ".venv"
> ```
>
> Nếu mọi nơi đọc đều nằm ngoài đường chấm (admin UI, observability, script vận hành) thì file đó **không** làm mất hiệu lực E1/E5. Nếu có **bất kỳ** nơi đọc nào nằm trong agent/fact-check/graph/scoring/retrieval/KB thì diff của nó **là** diff đường chấm, và phải đo lại.
>
> **Áp dụng lần đầu — `model_pricing.yaml`, kiểm ngày 2026-08-16:** chỉ có `review_platform/admin/queries.py` và `scripts/test_admin_dashboard.py` đọc nó; `config.py` hardcode đúng một đường dẫn tới `scoring.yaml` (dòng 19) chứ không quét thư mục, nên bộ nạp config của đường chấm không bao giờ chạm tới file này. Kết luận: **ngoài đường chấm**, không làm mất hiệu lực phép đo.
>
> **Không đổi luật và không kết quả đã đo nào bị đổi.** Đây là làm rõ một chỗ mà quy tắc chưa lường tới, đúng cách `annotation-guideline.md` đã xử lý ca A3 (mục "Ghi chú A3"). Tiêu chí "file nào được đường chấm đọc" vốn đã là *ý* của quy tắc gốc — chỗ này chỉ viết nó ra thành phép kiểm chạy được. Bản khoá vẫn là `04f10e1`, `prompt_version` vẫn `020738e209017213`.
>
> ⚠️ **Đây không phải cửa miễn trừ cho cả thư mục `config/`.** `scoring.yaml` được `config.py` đọc trực tiếp nên vĩnh viễn nằm trong đường chấm; sửa nó là mất hiệu lực E1/E5, không có ngoại lệ nào.

**Hàng rào cho luồng productization song song:** thiết kế service độc lập/admin ngày 2026-08-12 chỉ được thay lớp API, auth, migration, site/profile, connector, admin UI và observability. Nếu việc triển khai làm đổi prompt, input chuẩn hóa của agent, retrieval, scoring, rule, Aggregator hoặc output report với cùng input thì đó **không còn là refactor lớp bao quanh**: phải dừng, ghi nhận thay đổi score-path và đo lại E1/E5. `site_id`, `profile_id` và `policy_version` chỉ là metadata cho tới khi profile mới được calibrate; chúng không được phép âm thầm chọn bộ ngưỡng/prompt khác cho profile `cam-nang-vn` hiện hành.

**Vì sao có bản 2:** bản 1 khoá lúc mới 2/4 agent dùng rubric, kèm lập luận rằng σ của `content_quality` (0,38) và `seo` (0,19) đủ nhỏ nên không cần chuyển. Lập luận đó **đúng về độ ổn định nhưng thiếu một vế**: σ thấp chứng minh điểm *tái lập được*, không chứng minh điểm *có định nghĩa*. LLM trả 78 đều đặn qua 5 lượt vẫn không ai biết 78 khác 74 ở chỗ nào, mà calibrate một ngưỡng trên đại lượng không định nghĩa thì ngưỡng cũng không định nghĩa được — đó chính là luận điểm gốc của `rubrics.md` mục 1. Nên đã chuyển nốt: **4/4 agent dùng rubric, nợ A1 đóng.**

Rủi ro đã lường trước và đo được: rubric làm dao động **hiện ra** (mục 4.1: chuyển Compliance đẩy σ từ 0,28 lên 1,43). Với SEO thì ngược lại — 7/10 tiêu chí đo bằng máy nên σ nhiều khả năng giảm; với Content Quality thì 4/8 do LLM chấm nên có thể tăng. Đó là lý do E1 phải chạy lại, và là chỗ có thể phải hoàn nguyên riêng Content Quality nếu σ vượt 2.

**Hai thứ cố ý KHÔNG sửa trước khi khoá**, ghi rõ để không ai tưởng là bỏ sót:

- **σ Compliance = 4,18** (chưa đạt ngưỡng < 2). Không chặn E5 vì thứ E5 quét là `final_score`, mà σ `final_score` = 1,33 đã đạt. Tiền lệ B5 cho thấy loại sửa này khó đoán kết quả (7,70 → 7,29), và mỗi lần sửa lại phải đo lại E1.
- **Năm tiêu chí gần như không mang thông tin trên corpus này:** BV3 (0/33 đạt mức 2), BV1/BV5/BV7 và **SEO10** (33/33 luôn mức 2 — mọi bài đều có ≥3 internal link). Chẩn đoán ở `technical-debt.md` B13; không sửa vì chúng không gây quyết định sai, và với chúng **không tìm được lập luận nào không nhắc tới phân bố** — chỉnh ngưỡng lúc đó sẽ là đúng bẫy B9.

  *(Ngoại lệ đã sửa: CQ3 ban đầu cũng 33/33 mức 0, nhưng ở đó có lập luận độc lập — ngưỡng 30 là quy ước readability tiếng Anh đếm **từ**, áp nhầm lên số **tiếng**. Đổi sang 45 tiếng ≈ 30 từ, phát biểu được mà không cần nhắc tới phân bố. Sau khi sửa: 13/14/6.)*

---

## 4. Chi tiết từng phép đo

### 4.1. E1 - Độ ổn định điểm của agent

**Câu hỏi:** chấm lại cùng một bài nhiều lần thì điểm lệch bao nhiêu?

Đây là phép đo nền của cả dự án. `ai_core.py` đặt `temperature=0` với ghi chú rằng nó "giảm dao động điểm giữa các lần chấm" - nhưng **`temperature=0` không đảm bảo output giống hệt nhau**, kể cả trên các model đời trước. Nó giảm dao động, không loại bỏ. Nên đây là thứ phải **đo**, không phải giả định.

**Cách làm:**

1. Chọn 10 bài đại diện (đã có sẵn trong Drupal, không cần chờ gold set)
2. Chấm mỗi bài **5 lần**, cùng model, cùng prompt, cùng cấu hình
3. Với mỗi agent, tính **độ lệch chuẩn σ** của điểm qua 5 lần
4. Đếm tỉ lệ lần chấm cho ra **cùng một `decision`** cuối cùng

**Tiêu chí:** σ < 2 điểm. Ngưỡng này không tùy tiện - `architecture.md` mục 8.2 dự kiến quét ngưỡng theo bước nhảy 2 điểm, nên dao động phải nhỏ hơn bước nhảy thì việc quét mới có nghĩa.

#### ✅ Kết quả bản 4 — chạy 2026-08-16, ĐẠT

**σ `final_score` = 1,60 < 2.** Đo trên HEAD `08cebe3`, score-path snapshot `04f10e1` (diff rỗng), `prompt_version` `020738e209017213`, model `claude-haiku-4-5-20251001`, `calibrated: false`, mẫu `G-001..G-010` × 5 lượt = 50 lượt, chi phí thật **$3,07**.

| Agent | σ tb | Đạt < 2? |
|---|---|---|
| `content_quality` | 3,27 | ❌ |
| `seo` | 0,22 | ✅ |
| `brand` | 0,89 | ✅ |
| `compliance` | 4,02 | ❌ |
| **`final_score`** | **1,60** | ✅ |

Tỉ lệ ra cùng `decision`: **92%**. Hai agent trượt ngưỡng riêng **không chặn E5** — tiêu chí áp cho `final_score`, đại lượng E5 quét ngưỡng lên. Báo cáo đầy đủ kèm so sánh với bản 2 và cảnh báo diễn giải: [`evidence/e1_sau_cp4_deadline_guard_report.md`](evidence/e1_sau_cp4_deadline_guard_report.md).

Test–retest nhãn đã hoàn tất và khoá **trước** lượt chạy này (2026-08-15, Kappa 1,000 kèm ba giới hạn — `technical-debt.md` mục 8.3), nên ràng buộc "không xem output E1 trước khi người gán chốt nhãn lượt hai" đã được tuân thủ.

**Biến thể quan trọng - so rubric với cách hiện tại:** ✅ **đã chạy 2026-08-04**, kết quả đầy đủ ở `docs/rubrics.md` mục 9.1 và `docs/evidence/e1_rubric_v2_report.txt`.

Kết quả **âm**: rubric KHÔNG ổn định hơn thang 0-100 (σ `final_score` 0,28 → 1,43 trên 7 bài chung). Ghi lại nguyên văn đúng như đã cam kết. Chẩn đoán: rubric không tạo ra dao động mà làm dao động hiện ra - thang 0-100 tự do nuốt chỗ LLM lưỡng lự, còn rubric lượng tử hoá 0/1/2 rồi chia mẫu số nên khuếch đại lên. Điều kiện E5 vẫn đạt vì σ `final_score` = 1,33 < 2.

So sánh lại được nhờ `scripts/so_sanh_phuong_sai.py`, chạy trên **cùng bộ mẫu** - so trên tập khác nhau thì chênh lệch đến từ đổi mẫu chứ không phải đổi cách chấm.

**Quy mô:** 10 bài × 5 lần × 4 agent = 200 lần gọi LLM.

#### Kết quả E1 sau khi cả 4 agent dùng rubric (2026-08-11) — ⚠️ ĐÃ HẾT HIỆU LỰC

> **Không trích các con số dưới đây cho code hiện tại.** Chúng đo trên bản khoá **bản 2**; sau đó B14 sửa CP3/CP4, tức đổi đúng agent có σ cao nhất bảng. Giữ lại vì phần chẩn đoán bên dưới vẫn còn giá trị, và vì bảng này là **đầu vào của việc tìm ra B14**.

Số liệu thô: `docs/evidence/e1_sau_rubric_4_agent.json`. Chi phí thật **$3,06**, 50 lượt chấm, 39,5 giây/lượt (4 agent chạy tuần tự trong script; pipeline thật chạy song song nên nhanh hơn).

| Agent | σ trung bình | σ lớn nhất | Đạt < 2? | So với lần đo trước |
|---|---|---|---|---|
| **seo** | **0,27** | 2,74 | ✅ | 0,19 → 0,27 (gần như không đổi, nhưng điểm nay **có định nghĩa**) |
| brand | 1,44 | 5,48 | ✅ | — |
| content_quality | 4,38 | 14,40 | ❌ | **0,38 → 4,38** |
| compliance | 4,68 | 11,57 | ❌ | 4,18 → 4,68 |
| **`final_score`** | **1,79** | 4,04 | **✅ ĐẠT** | 1,33 → 1,79 |

**Ở bản 2, cổng E5 đã mở. Trạng thái đó không được kế thừa sang bản 4.** Tiêu chí σ < 2 áp cho `final_score` — đó là đại lượng E5 quét ngưỡng lên — và khi ấy nó đạt. σ từng agent chỉ quan trọng qua đường đóng góp vào điểm tổng.

**Dự đoán về SEO đúng hoàn toàn:** 7/10 tiêu chí đo bằng máy → σ = 0,27, gần như tất định. Đây là nước đi lãi rõ: giữ nguyên độ ổn định mà đổi được một con số LLM tự đặt lấy một con số giải thích được.

**Content Quality tăng từ 0,38 lên 4,38 — đúng như đã lường trước**, và đúng cơ chế mục 4.1 mô tả: rubric **không tạo ra** dao động mà **làm nó hiện ra**. Thang 0-100 tự do nuốt chỗ LLM lưỡng lự; rubric lượng tử hoá 0/1/2 rồi chia mẫu số nên phơi ra.

**Đóng góp vào phương sai điểm tổng** (trọng số² × σ²) — cho thấy Compliance mới là nguồn chính, không phải CQ vừa đổi:

```
compliance    0,30² × 4,68²  =  1,97   60%
content_qual  0,25² × 4,38²  =  1,20   36%
brand         0,25² × 1,44²  =  0,13
seo           0,20² × 0,27²  =  0,003
```

Tính thử: hoàn nguyên CQ về thang tự do cho σ `final_score` ≈ 1,45 thay vì 1,79 — **cả hai đều qua cổng**, nên hoàn nguyên chỉ đổi điểm-có-định-nghĩa lấy một con số đẹp hơn chút. Không làm.

#### ⚠️ Tỉ lệ ra cùng quyết định tụt từ 100% xuống **88%** — và nguyên nhân KHÔNG phải rubric

Đây là con số đáng lo hơn σ: khoảng 1 trong 8 lượt chấm cho ra đề xuất khác. Nhưng chẩn đoán từ dữ liệu thô chỉ đúng một chỗ:

```
G-001   compliance [50,0  50,0  50,0  50,0  50,0]   nằm ĐÚNG trên ngưỡng veto
G-010   compliance [50,0  50,0  50,0  50,0  50,0]   nằm ĐÚNG trên ngưỡng veto
G-003   compliance [66,7  37,5  62,5  50,0  50,0]   nhảy qua nhảy lại
G-005   compliance [58,3  58,3  58,3  58,3  50,0]
G-004   compliance [66,7  66,7  66,7  50,0  66,7]
```

**8/10 bài có điểm Compliance nằm trong dải 44–58**, tức sát ngưỡng `compliance_veto_below = 50`. Cả 4 bài đổi quyết định đều thuộc nhóm đó — chỉ cần một tiêu chí nhích một bậc là lật giữa `rejected` và `needs_revision`.

**Mà 50 là số minh hoạ chưa calibrate** (`scoring.yaml` ghi `meta.calibrated: false`; nguồn: `architecture.md` mục 6.2). Nói cách khác, 88% có thể là **ngưỡng đặt sai chỗ — đúng giữa vùng điểm dày nhất — chứ không phải agent hỏng.**

**Vì vậy thứ tự đúng là calibrate TRƯỚC, sửa agent SAU** (nếu còn cần). E5 sẽ dời ngưỡng ra khỏi cụm điểm; nếu số lần lật giảm thì không phải đụng dòng code nào. Nếu vẫn lật nhiều thì lúc đó **biết chắc** là lỗi agent chứ không phải lỗi ngưỡng, và sửa có mục tiêu.

> **Hậu kiểm (2026-08-11): suy đoán trên SAI một nửa, và cách bố trí thí nghiệm đã cứu được.**
>
> E5 cho thấy **cả hai** đều đúng: ngưỡng *có* đặt sai chỗ, nhưng agent **cũng hỏng thật** — CP3 gắn cờ `critical` sai 8/9 lần (B14). Mệnh đề *"chứ không phải agent hỏng"* là suy luận **hoặc-này-hoặc-kia** trên một tình huống có hai nguyên nhân cùng lúc.
>
> Điều đáng giữ lại: **thứ tự "calibrate trước" vẫn đúng, dù lý do đưa ra thì sai.** Đúng không phải vì ngưỡng là thủ phạm, mà vì E5 là *phép chẩn đoán rẻ nhất* — nó phơi ra lỗi agent (qua việc ngưỡng tối ưu bị dồn về đáy dải quét) mà không cần đoán trước lỗi nằm ở đâu. Nếu làm ngược lại — sửa Compliance trước rồi mới đo — thì sẽ sửa mò, và σ 4,68 không chỉ được vào CP3.

Thêm một căn cứ cho việc không vội sửa Compliance: nợ B5 đã thử một bản sửa rất hợp lý và σ chỉ đi từ **7,70 xuống 7,29**. Bốn tiêu chí còn dao động (CP2/CP4/CP7/CP8) đều cần đọc hiểu, không chuyển sang đo bằng máy được như CP5/CP6 đã làm.

### 4.2. E2 - recall@k của retrieval

Đã đặc tả đầy đủ ở `rag-design.md` mục 5. Tóm tắt để đặt đúng vị trí trong chuỗi: ~20 cặp `(truy vấn, chunk đúng)` tự soạn, đo tỉ lệ chunk đúng nằm trong top-k, tiêu chí **recall@3 ≥ 0.9** cho KB fact-check. Không đạt thì **sửa chunking trước, đổi embedding sau**.

**Đã chạy cho cả hai KB:**

| KB | Cách đo | Kết quả |
|---|---|---|
| fact-check | recall@3 trên 12 truy vấn seed (`scripts/eval_retrieval.py`) | **1.00** |
| brand | tỉ lệ top-3 cùng nhóm chủ đề vs mốc ngẫu nhiên (`scripts/eval_brand_retrieval.py`) | **78,3% vs 21,7% — gấp 3,6 lần** |

KB brand không dùng recall@k được vì nhiều đoạn cùng chủ đề đều hợp lệ — không tồn tại "một đáp án đúng". Chi tiết cách đo thay thế: `rag-design.md` mục 5.

**Con số 78,3% là chặn dưới, không phải tỉ lệ thật.** Ground truth chỉ gán một nhóm chủ đề mỗi bài, trong khi nhiều bài thuộc hai nhóm — ví dụ G-018 *"tìm trạm sạc bằng App"* bị tính trượt vì retrieval trả về nhóm `ung_dung`, dù các đoạn lấy về nói đúng về *"tìm kiếm trạm sạc bằng app"*. **Không** sửa nhãn để chữa các ca này: sửa sau khi đã nhìn kết quả là tự tạo thiên vị. Để nguyên và báo cáo con số bị đánh giá thấp — lệch về hướng an toàn.

### 4.3. E3 - Baseline single-agent

**Câu hỏi:** kiến trúc 4 agent có thật sự hơn 1 agent làm tất không?

`architecture.md` mục 4.3 đã lập luận rằng multi-agent phù hợp vì 4 khía cạnh độc lập và song song được, dẫn nghiên cứu bên ngoài. Nhưng dự án sẽ có gold set - tức là **đo được trên chính bài toán của mình**, thay vì chỉ trích dẫn. Biến một lập luận thành một bằng chứng là đúng tinh thần "research sâu hơn để hiểu thật sự" mà mentor yêu cầu.

**Cách làm:**

1. Viết **một** system prompt duy nhất yêu cầu LLM chấm cả 4 khía cạnh trong một lần gọi, trả về cùng cấu trúc output
2. Chạy trên **cùng gold set** đã dùng cho hệ 4 agent
3. So 4 chỉ số:

| Chỉ số | Vì sao đo |
|---|---|
| Kappa với nhãn người | Chất lượng quyết định cuối |
| F1 theo từng loại lỗi | Single-agent có bỏ sót loại lỗi nào không |
| Chi phí / bài | 4 lần gọi so với 1 lần gọi |
| Độ trễ / bài | 4 lần song song so với 1 lần dài |

**Không đặt tiêu chí đạt/trượt.** Đây là câu hỏi nghiên cứu, không phải cổng chất lượng. Nếu single-agent thắng thì đó cũng là một phát hiện đáng báo cáo - và trung thực báo cáo nó mạnh hơn là giấu đi.

**Lưu ý khi diễn giải:** single-agent không có quyền phủ quyết riêng cho Compliance, nên so sánh phải nêu rõ hai hệ không hoàn toàn tương đương về mặt cơ chế an toàn.

### 4.4. E4 - Chi phí và độ trễ

**Cách đo đúng:** dùng `usage` trả về trong response của mỗi lần gọi (`input_tokens`, `output_tokens`) và cộng dồn - **không ước lượng bằng cách đếm ký tự chia 4**. Với văn bản tiếng Việt, ước lượng kiểu đó sai đáng kể.

Muốn tính trước khi gọi thì dùng endpoint `count_tokens` với đúng model sẽ chạy.

**Giá hiện hành** (model đang dùng: `claude-haiku-4-5`):

| | Input | Output | Cửa sổ ngữ cảnh |
|---|---|---|---|
| Haiku 4.5 | $1.00 / 1M token | $5.00 / 1M token | 200K |
| Sonnet 5 | $3.00 / 1M token | $15.00 / 1M token | 1M |

**Số đo thật (2026-08-04, E1 - 7 bài × 5 lần = 35 lượt):**

```
Trung bình : $0,057 / bài   (~1.500 VNĐ),  ~37.900 token input
Dải theo bài: $0,033 – $0,089           ~20.800 – 56.900 token input
```

Số liệu thô: `docs/evidence/e1_stability_raw.json`; báo cáo: `docs/evidence/e1_e4_report.txt`.

**Chênh lệch giữa bài rẻ nhất và đắt nhất là 2,7×** (G-004 so với G-007), gần như hoàn toàn do độ dài bài. Vì vậy trích *một* con số chi phí mà không kèm dải là gây hiểu nhầm - chi phí thật phụ thuộc bài, không phải hằng số của hệ thống.

> ⚠️ **Sửa 2026-08-04:** bản trước ghi dải `$0,042 – $0,052` và `28.000 – 38.000 token`. **Cả hai đều lấy giá trị TRUNG BÌNH làm cận trên** - trung bình thật ($0,0565 và 37.894 token) nằm *ngoài* dải đã ghi, tức dải đó không thể đúng về mặt số học. Tính lại trực tiếp từ `e1_stability_raw.json`. Đây là lần thứ hai cùng một mục này sai số: lần đầu là ước tính hụt 2× (dưới đây), lần này là dải bịa hẹp lại. Bài học chung cho cả hai: **con số nào trong tài liệu cũng phải tính ra được từ một file trong `docs/evidence/`**, không chép tay từ trí nhớ.

**Ước tính sơ bộ trước đó SAI khoảng 2×** — giữ lại ở đây vì chỗ sai có ích:

```
Một bài cẩm nang ~1.200 từ tiếng Việt
  → mỗi agent nhận ~3.000 token input (gồm system prompt)
  → 4 agent = ~12.000 token input
  → output JSON ~600 token/agent = ~2.400 token output
Chi phí/bài ≈ ~$0,025
```

Ước tính trên hụt vì hai thứ không có trong phép nhân: (1) bài cẩm nang thật dài hơn 1.200 từ nhiều — mẫu gold set có bài 2.136 từ; (2) Compliance và Brand Voice **nhét thêm đoạn KB lấy từ RAG** vào prompt, phần này không tồn tại lúc viết ước tính. Kết luận rút ra: ước tính token bằng cách nhân đầu người luôn thiếu phần retrieval — phải đo.

**Ngân sách toàn bộ chương trình thí nghiệm:**

| Phép đo | Số lượt chấm | Chi phí | Nguồn |
|---|---|---|---|
| E1 thang 0-100 | 35 | **$1,98** | `e1_stability_raw.json` |
| E1 rubric v1 | 40 | **$2,39** | `e1_stability_rubric.json` |
| E1 rubric v2 | 50 | **$3,04** | `e1_stability_rubric_v2.json` |
| Chẩn đoán lật mức (B5) trước/sau | 40 | **$0,92** | `cp_lat_muc_{truoc,sau}_sua.json` |
| **Đã tiêu, số thật** | **165** | **$8,33** | |
| E3 baseline (33 mẫu, 1 agent) | 33 | ~$0,60 *(ước)* | |
| E5 chấm gold set (33 mẫu) | 33 | ~$1,90 *(ước)* | |
| **Tổng dự kiến cả chương trình** | | **~$11** | |

Bốn dòng đầu là **số thật cộng từ `usage` của từng lần gọi**, không phải ước tính; hai dòng E3/E5 tính theo đơn giá thật $0,057/bài. Con số vẫn nhỏ, và điều đó mới là ý chính: nó **loại bỏ "tốn kém" khỏi danh sách lý do không đo**. Toàn bộ chương trình đo lường rẻ hơn một bữa trưa.

Lưu ý khi đọc bảng: hai dòng chẩn đoán B5 rẻ hơn hẳn ($0,023/lượt) vì chúng **chỉ chạy Compliance**, không chạy cả 4 agent - không so trực tiếp với các dòng E1 được.

**Một điểm dễ hiểu nhầm về E5:** quét nhiều mức ngưỡng **không tốn thêm tiền**. Chấm gold set một lần, lưu lại kết quả 4 agent, rồi quét ngưỡng bằng cách chạy lại **Aggregator** trên kết quả đã lưu - mà Aggregator là module tất định không gọi LLM (`architecture.md` mục 6). Đây chính là một lợi ích cụ thể của thiết kế Aggregator tất định, đáng nêu khi bảo vệ.

**Độ trễ cần đo riêng:** thời gian mỗi agent, thời gian toàn pipeline, và phần chồng lấn nhờ chạy song song. Con số này quyết định chu kỳ polling worker (`architecture.md` mục 9.2) - đặt 30 giây mà một bài chấm mất 40 giây thì worker sẽ chồng lệnh.

**Quy mô production (để trong báo cáo):** ước tính theo số bài VF O2O xuất bản mỗi tháng × chi phí/bài. Nếu không có con số thật thì nêu rõ là ước tính theo giả định, kèm giả định là bao nhiêu.

### 4.5. E5 - Calibration ngưỡng

Đã đặc tả đầy đủ ở `architecture.md` mục 8.2 (Recall/F1, Cohen's Kappa, quét ngưỡng theo Youden's Index). Bốn điều kiện tiên quyết cần nhấn lại ở đây:

**Biên dữ liệu bắt buộc:** E5 đọc manifest `docs/goldset/labels.csv` và chỉ nhận hai split allowlist `gold-real`, `gold-pert`. Mọi split khác bị loại; 10 mẫu functional-clean có manifest riêng và không tham gia chấm E5 hoặc tính Kappa.

Functional-clean là phép kiểm cơ chế riêng: chạy 10 mẫu corrected có expected `publish`, rồi báo cáo `publish_rate`, `false_positive_articles` (số bài bị báo oan) và `false_positive_issues` (tổng số issue báo oan). Không gộp ba chỉ số này với Kappa/accuracy của gold calibration; nếu nêu tổng 43 thì phải gọi rõ là evaluation suite.

1. ⚠️ **E1 bản 4 phải đạt trước và hiện chưa chạy.** Bước nhảy 2 điểm chỉ có nghĩa nếu σ `final_score` < 2. Kết quả ngày 2026-08-04 và bản 2 là lịch sử; chốt CP4 đã đổi đúng đường Compliance nên không mở cổng E5 hiện hành. Preflight 2026-08-12 chỉ xác nhận an toàn vận hành, không thay thế phép đo.
2. **Ngưỡng chốt được chỉ có hiệu lực với đúng bộ `(rubric version, prompt version, model)`** đã dùng khi calibrate. Đổi model là phải calibrate lại - mà `ANTHROPIC_MODEL` đang đọc từ biến môi trường nên có thể đổi mà không ai để ý. ✅ **đã có cảnh báo tự động (2026-08-04)**: `src/config.py` so `meta.model` trong `scoring.yaml` với model đang chạy và log cảnh báo khi lệch.
3. ~~**Brand Voice Agent phải là agent thật, không còn stub.**~~ ✅ **đạt (2026-08-03)**
4. ~~**SEO Agent phải đọc được `alt` của ảnh nằm trong `body`.**~~ ✅ **đạt (2026-08-04)** — `_extract_image_alt()` bóc mọi thẻ `<img>` trong body; test `scripts/test_image_alt.py`.

Hai điều kiện cuối phát hiện ngày 2026-07-30 khi chạy pipeline thật lên `node/7` của Drupal local (bài đầu tiên có ảnh thật). Số liệu đo được, không phải suy luận:

**Điều kiện 3 - stub tạo điểm sàn 55.** Bài `node/7` gần như rỗng (tiêu đề "test", body chỉ có chữ "test" + 1 ảnh, không meta description, không URL alias). Hai agent thật chấm rất thấp, nhưng điểm tổng vẫn 70:

| Agent | Điểm | Trọng số | Đóng góp |
| --- | --- | --- | --- |
| Content Quality | 40 | 0.25 | 10 |
| SEO | 25 | 0.20 | 5 |
| **Brand (stub, luôn trả 100)** | **100** | 0.25 | **25** |
| Compliance | 100 | 0.30 | 30 |
| | | | **70.0** |

`brand_node` trong `graph.py` luôn trả `score = 100`. Cộng với Compliance 100 (đúng - bài rỗng thì không vi phạm gì), mọi bài viết đều được **55 điểm sàn miễn phí**, không bài nào xuống dưới mức đó dù tệ đến đâu. Calibrate trên hệ thống này sẽ cho ra ngưỡng phản ánh 25 điểm giả, và ngưỡng đó sai hoàn toàn khi Brand Agent thật đi vào hoạt động. Đây là lý do định lượng cho việc Brand Voice Agent phải xong trước Sprint 3 - mạnh hơn nhiều so với lập luận "vì nó là stub".

**ĐÃ XỬ LÝ (2026-08-03).** Stub được thay bằng agent thật (`docs/superpowers/specs/2026-08-03-brand-voice-agent-design.md`). Đo lại trên chính `node/7`: **70,0 → 57,5**. Nhưng con số đáng chú ý hơn nằm ở 20 bài `GOLD` thật:

| | Stub | Agent thật |
|---|---|---|
| Điểm brand trên 20 bài `GOLD` | **một giá trị duy nhất: 100** | dải **75–90**, trung bình 83,5 |

Đây mới là điều quyết định: stub **không phân biệt được bài nào với bài nào**, nên quét ngưỡng trên nó là quét trên một hằng số. Chạy thật end-to-end trên Drupal (`node d115f055`) cho `final_score` 84,25 → **81,75**, tức chỉ còn cách ngưỡng publish (80) đúng 1,75 điểm thay vì 4,25 — 25 điểm giả không chỉ làm điểm cao lên mà còn **đẩy các bài ra xa ranh giới quyết định**, đúng chỗ calibration cần độ nhạy nhất.

**Hệ quả bắt buộc nêu khi báo cáo:** mọi số liệu chấm **trước** ngày 2026-08-03 không so trực tiếp được với số liệu sau, vì thang điểm đã đổi.

**Điều kiện 4 - tiêu chí SEO9 chỉ đo được một phần thực tế.** Cùng bài `node/7` có 2 ảnh: ảnh chính trong `field_image` (alt = "xe vf6") và 1 ảnh chèn trong `body` **không có alt**. Pipeline chỉ bắt được ảnh chính; ảnh thiếu alt trong body lọt lưới hoàn toàn.

Nguyên nhân ở `drupal_client.py`: `image_alt` chỉ lấy từ `relationships.field_image.data.meta.alt`, còn ảnh trong body nằm lẫn trong chuỗi HTML của `attributes.body.value` và không được bóc ra. System prompt của `seo.py` cũng chỉ dặn LLM chấm field `[image_alt]`.

Hệ quả cho calibration: Recall/F1 của tiêu chí SEO9 sẽ lệch có hệ thống, vì ground truth (mã lỗi B6 trong `annotation-guideline.md` v1.2) xét **mọi ảnh trong body** còn hệ thống chỉ xét **một ảnh đại diện**. Hai bên đo hai tập ảnh khác nhau. Chi tiết và bằng chứng thứ hai (bài G-001 của gold set): `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md` mục 6.

#### Kết quả E5 lịch sử trên bản 3 (2026-08-11; hết hiệu lực với code hiện hành)

Số liệu thô: `docs/evidence/e5_sau_sua_cp3_cp4.json` (điểm 4 agent trên 33 bài) và `e5_quet_nguong.json` (50 bộ ngưỡng tốt nhất). Script: `scripts/eval_calibration.py`, hai pha — chấm 33 bài **một lần** (~$1,9), rồi quét **7056 tổ hợp ngưỡng** với chi phí **$0**. Quét miễn phí được là nhờ Aggregator là hàm thuần không gọi LLM (`architecture.md` mục 6); đây là lợi ích cụ thể của quyết định thiết kế đó, đáng nêu khi bảo vệ.

**E5 phải chạy HAI lần, và lần đầu là thứ tìm ra lỗi.**

| | Kappa (ngưỡng 50/50/80) | Kappa (tốt nhất) | Accuracy |
|---|---|---|---|
| Lần 1 — trước khi sửa CP3/CP4 | 0,090 | 0,264 | 0,636 |
| **Lần 2 — sau khi sửa** | **0,427** | **0,713** | **0,879** |

Kappa **0,713** nằm trong vùng *substantial agreement* (Landis–Koch 0,61–0,80). Sai **4/33 bài**. Đây là bằng chứng lịch sử đã dẫn tới chẩn đoán CP4; sau chốt CP4 ngày 2026-08-12, không được trình bày con số này như kết quả của code hiện hành.

**Lần 1 không phải thất bại — nó là phép chẩn đoán.** Kappa 0,264 với ngưỡng tối ưu bị đẩy về đáy dải quét là dấu hiệu *bài toán không nằm ở ngưỡng*. Truy ngược ra: **16/33 bài có cờ `critical` trong khi chỉ 7 bài đáng có** — precision đường veto 44%. Và 8/9 báo động giả đến từ **CP3**.

Nguyên nhân gốc, không phải "LLM bất định": **CP3 kiểm "cùng model" nhưng quên kiểm "cùng chỉ số".** Nó so mọi con số có `km` với `tam_hoat_dong`:

| Câu bị gắn cờ sai | Thực chất |
|---|---|
| *"VF e34 đã vượt qua cung đường 220km"* | quãng đường một chuyến đi |
| *"657.500 đồng/tháng với quãng đường 500km/tháng"* | hạn mức gói thuê pin |
| *"VF e34 có công suất pin là 42kWh"* | dung lượng pin |
| *"Trụ sạc nhanh DC 30kW - Khoảng 60 phút"* | thông số trụ sạc |

CP4 mắc lỗi cùng họ: gắn cờ *"khuyến mại thiếu thời hạn"* cho câu **có** thời hạn (*"từ 25/06 – 31/08/2024"*, *"Trước 6/4/2022"*).

**Đã sửa ba lớp** (chi tiết ở `technical-debt.md` B14):
1. Prompt trích claim tách bạch `tam_hoat_dong` khỏi bốn loại số hay bị nhầm
2. **Chốt chặn tất định**: claim `metric="khac"` không bao giờ vào so sánh LLM — phải chặn ở code vì `retriever` không có ngưỡng similarity nên luôn trả về chunk gần nhất
3. Prompt đối chiếu đòi đủ **ba** điều: đúng model, **đúng chỉ số**, số mâu thuẫn

Kết quả trên 12 bài chẩn đoán: **báo động giả 9 → 1**, và bắt được thêm P-010a (bài chèn A4 mà CP4 từng bỏ sót).

**Bốn bài còn sai, ba trong đó đã có tài liệu từ trước:**

| Bài | Người | Máy | Nguyên nhân |
|---|---|---|---|
| G-011 | rejected | needs_revision | `"có một không hai"` ngoài blacklist — B12b, **cố ý không vá** |
| G-020 | rejected | needs_revision | `"săn đón nhất"` ngoài blacklist — B12b, **cố ý không vá** |
| P-006a | needs_revision | rejected | CP4 báo oan câu có thời hạn — đã có test hồi quy và chốt tất định ở bản 4 |
| G-008 | needs_revision | rejected | CP4 tạo cờ `critical` oan dù có thời hạn — đã có test hồi quy và chốt tất định ở bản 4 |

#### ⚠️ Ba điều phải nêu khi trích con số 0,713

**1. Ngưỡng tối ưu vô hiệu hoá veto-theo-điểm.** `veto = 30` và `nr = 30` nằm ở đáy dải quét, mà điểm Compliance thấp nhất trong cả bộ là **33,3** — tức ngưỡng nằm dưới mọi điểm. Ở cấu hình tối ưu, `rejected` do **duy nhất cờ `critical`** sinh ra.

Đây không phải lỗi mà là kết luận: sau khi CP3/CP4 hết báo oan, **cờ `critical` một mình đã đủ khớp phán đoán của người**. Ngưỡng điểm không thêm được gì. Và đây là **plateau, không phải cực trị bị cắt cụt** — mọi giá trị ≤ 33 cho kết quả y hệt, nên không cần mở rộng dải quét.

**2. Ngưỡng `publish` không calibrate được.** Bộ tối ưu đẩy nó lên ≥92 chỉ vì gold set **không có mẫu `publish` nào** nên mọi dự đoán `publish` đều sai. Đó là hệ quả của lớp rỗng, không phải calibration thật (`technical-debt.md` mục 6).

**3. ~~CHƯA CÓ TRẦN~~ — đã có trần từ 2026-08-15, nhưng nó không giúp được nhiều.** Test–retest cho Kappa **1,000** (`technical-debt.md` mục 8.3). Trần bằng 1,000 là **hướng an toàn** theo `annotation-guideline.md` mục 8.2, nhưng **mất chức năng chẩn đoán**: với trần 1,000 thì không bao giờ kích hoạt được cảnh báo "AI cao bất thường so với trần". Và bản thân trần đó đứng trên n=4 với 3/4 mẫu cùng một nhãn — phải trích kèm ba giới hạn ở mục 8.3.

> **Cập nhật 2026-08-16 — bản 4 đã đo, và ba điều trên vẫn đúng, nhưng thứ tự quan trọng đã đổi.** Điểm 2 hoá ra không phải một chú thích bên lề mà là **phát hiện lớn nhất**: với `publish = 80` đang chạy thật, hệ thống đề xuất `publish` cho **9/33 bài (27%)** mà người gán nhãn nói là chưa đăng được, và Kappa tụt từ 0,713 xuống **0,406**. Toàn bộ khoảng cách giữa hai con số là ngưỡng `publish`. Xem [`evidence/e5_e6_ban4_report.md`](evidence/e5_e6_ban4_report.md).
>
> Điểm 1 cũng cần chỉnh: điểm Compliance thấp nhất ở bản 4 là **25,0** chứ không phải 33,3, nên `veto = 30` **không** còn nằm dưới mọi điểm. Nhưng kết luận plateau vẫn đúng vì lý do khác — chỉ một mẫu (`P-005a` = 37,5) nằm giữa các giá trị fold chọn (34 và 40), và nó không đổi dự đoán nào.

#### Chưa chốt ngưỡng vào `scoring.yaml`

`meta.calibrated` vẫn để `false`. Hai việc phải xong trước khi đổi:

- **Đo lại E1 và E5** — CP4 vừa đổi nên cả độ ổn định lẫn calibration ngày 2026-08-11 đã hết hiệu lực. Ghi `calibrated: true` hoặc chép ngưỡng cũ vào config lúc này là sai phiên bản.
- **Test-retest nhãn** (≥13/08) — để có trần Kappa.

---

### 4.6. E6 - Shadow-test: phải viết lại cho khả thi

`architecture.md` mục 8.3 hiện mô tả shadow-test 2-4 tuần chạy song song với quy trình duyệt của người thật. **Kế hoạch này không thực hiện được** trong phạm vi dự án: không có quyền truy cập Drupal thật của VinFast, không có đội content thật, không có luồng duyệt thật để chạy song song (spec mục 6.1).

Để nguyên như vậy là một lời hứa không giữ được - và hội đồng sẽ hỏi.

**Ba phương án thay thế, theo thứ tự khả thi:**

| Phương án | Nội dung | Khả thi |
|---|---|---|
| **A - Shadow-test trên gold set giữ lại** | Tách ~20% gold set ra làm tập kiểm tra cuối, **không** dùng khi calibrate. Sau khi chốt ngưỡng, chạy trên tập này để xem ngưỡng có tổng quát hoá không | ✅ Làm được ngay, không cần gì thêm |
| **B - Shadow-test trên bài mới** | Sau khi chốt ngưỡng, thu thêm ~10 bài cẩm nang **chưa từng dùng**, gán nhãn, chạy hệ thống | ✅ Cần thêm ~3 giờ thu và gán nhãn |
| **C - Shadow-test thật** | Đúng như mục 8.3 hiện tả | ❌ Ngoài phạm vi - ghi nhận là bước tiếp theo nếu dự án được triển khai thật |

**Khuyến nghị A**, và nêu rõ trong báo cáo rằng đây là **held-out test**, không phải shadow-test đúng nghĩa - vì shadow-test thật đòi hỏi một quy trình vận hành thật để chạy song song.

**Lưu ý về cỡ mẫu:** giữ lại 20% của 33 mẫu chỉ còn ~7 mẫu để calibrate ít đi. Với gold set nhỏ như vậy, cân nhắc **k-fold cross-validation** thay vì tách cứng - dùng hết 33 mẫu cho cả hai việc mà không rò rỉ. Đây là quyết định thống kê cần chốt trước khi bắt đầu E5.

### 4.6.1. ✅ QUYẾT ĐỊNH ĐÃ CHỐT — k-fold, đăng ký trước ngày 2026-08-16

**Chốt trước khi E5 chạy.** Commit của mục này phải là tổ tiên của commit chứa kết quả E5; nếu không, thiết kế mất tư cách "đăng ký trước" và Kappa CV chỉ còn là một con số chọn sau khi đã nhìn dữ liệu.

**Chọn k-fold, không tách cứng.** Ba căn cứ, không căn cứ nào nhìn vào kết quả mong muốn:

1. **Chi phí bằng nhau ($0 chênh lệch).** `eval_calibration.py` tách hai pha: PHA 1 chấm 33 bài một lần (~$2), PHA 2 quét ngưỡng là hàm thuần. k-fold thuần túy là cách phân tích khác trên **cùng một** output của PHA 1. Không có lý do ngân sách để chọn thiết kế yếu hơn.
2. **Cỡ mẫu tập kiểm tra: 33 so với 7.** Đo độ nhạy trên chính phân bố của gold set (10 `rejected` / 23 `needs_revision`):

   | Số dự đoán sai | Kappa nếu n=7 (tách cứng) | Kappa nếu n=33 (k-fold gộp) |
   |---|---|---|
   | 1 | 0,588 | 0,926 |
   | 2 | 0,000 | 0,848 |
   | 3 | −0,235 | 0,765 |

   Tách cứng biến E6 thành phép đo nhị phân: sai một bài là sập. Test–retest ngày 2026-08-15 đã cho bằng chứng thực nghiệm về đúng bệnh này ở n=4.
3. **Lớp `rejected` chủ yếu là mẫu nhân tạo.** `gold-real` chỉ có **3** `rejected` / 17 `needs_revision`; `gold-pert` có **7** / 6. Tách cứng 7 mẫu phân tầng cho ~2 `rejected`, xác suất cao cả hai đến từ nhóm chèn lỗi → E6 sẽ đo *"ngưỡng có bắt được lỗi tự chèn không"* thay vì *"ngưỡng có tổng quát hoá sang bài thật không"*.

**Đánh đổi phải nêu trong báo cáo, không được giấu:** Kappa CV ước lượng chất lượng của **quy trình calibration**, không phải của đúng bộ ngưỡng đem dùng. Ngưỡng đem dùng vẫn refit trên cả 33 mẫu và **không** có tập sạch nào validate riêng nó.

#### Thiết kế cố định (không đổi sau khi thấy dữ liệu)

| Tham số | Giá trị |
|---|---|
| Số fold | **5** |
| Đơn vị chia | **Nhóm theo `source_url`** — 33 mẫu chỉ đến từ **30 nguồn độc lập** |
| Phân tầng | Theo `label` (10 `rejected` / 23 `needs_revision`) |
| Seed gán fold | **`20260816`**, ghi vào file kết quả |
| Chỉ số chính | Cohen's Kappa trên **toàn bộ 33 dự đoán out-of-fold** gộp lại |
| Chỉ số phụ bắt buộc | Bộ ngưỡng mà **từng fold** chọn ra, in đủ 5 dòng |

⚠️ **Ràng buộc nhóm là bắt buộc, không phải tuỳ chọn.** `P-001a`/`P-001b`, `P-004a`/`P-004b`, `P-007a`/`P-007b` mỗi cặp dùng chung một bài gốc. Hai biến thể cùng nguồn rơi vào train/test khác nhau là **rò rỉ gần-trùng-lặp** và làm Kappa CV lạc quan giả.

#### Quy tắc phá hoà (tie-break) — phải cố định trước, đây là bậc tự do của người phân tích

Với 441 tổ hợp hiệu dụng trên ~26 mẫu mỗi fold, **hoà điểm Kappa gần như chắc chắn xảy ra** (dự án đã biết `veto ≤ 33` là một plateau vì điểm Compliance thấp nhất là 33,3). Không cố định quy tắc trước là để ngỏ chỗ chọn con số thuận lợi sau.

**Quy tắc:** trong các tổ hợp cùng đạt Kappa lớn nhất, chọn tổ hợp gần nhất (khoảng cách Euclid trên `(veto, nr)`) với **trung vị theo từng thành phần** của tập hoà. Còn hoà nữa thì lấy `veto` nhỏ hơn, rồi `nr` nhỏ hơn.

Lý do phát biểu được **mà không nhắc tới phân bố thu được**: chọn giữa plateau là chọn điểm xa biên quyết định nhất, nên nhiễu chấm điểm ít có cơ hội lật nhãn. E1 vừa đo σ `final_score` = 1,60 trong khi bước quét là 2 — cùng cỡ, nên khoảng cách tới biên là đại lượng đáng tối đa hoá.

#### `publish_min` không tham gia calibration

Gold set có **0** mẫu `publish` nên `publish_min` **không xác định được** — đã ghi ở `technical-debt.md` mục 6 và 8.2. Không quét, không chốt: giữ nguyên giá trị minh hoạ **80** hiện có trong `scoring.yaml` và ghi rõ trong báo cáo là *chưa calibrate*. Cách xử lý ngưỡng này vẫn cần mentor quyết.

Vì vậy số tổ hợp hiệu dụng là **441** (`veto` 21 × `nr` 21), không phải 7.056.

#### Hai con số phải báo cáo cạnh nhau

```
Kappa in-sample  (quét trên cả 33, lấy max)  = 0.xx   <- LẠC QUAN, có selection bias
Kappa CV         (33 dự đoán out-of-fold)    = 0.yy   <- ước lượng tổng quát hoá
```

Khoảng cách giữa hai số **chính là** mức selection bias của việc lấy max trên 441 tổ hợp. Báo cáo mỗi con số in-sample là giấu đúng thứ E6 sinh ra để đo.

---

## 5. Cái gì cố ý KHÔNG đo

| Không đo | Vì sao |
|---|---|
| Chất lượng nội dung sau khi sửa theo gợi ý | Cần đo tác động tới người dùng cuối - ngoài phạm vi và ngoài khả năng đo của dự án |
| So sánh với công cụ thương mại (Surfer, Clearscope...) | Không có quyền truy cập; và chúng chấm tiếng Anh, không so được |
| Thời gian tiết kiệm của đội content | Cần quy trình vận hành thật để làm mốc so sánh |
| A/B test thứ hạng SEO thật | Cần nhiều tháng và quyền truy cập Search Console |

Nêu rõ những thứ không đo cũng quan trọng như nêu những thứ đo - nó cho thấy phạm vi được chọn có ý thức, không phải bỏ sót.

---

## 6. Thứ tự khuyến nghị

Trạng thái lịch sử của các bước đã hoàn thành nằm ở mục 4. Thứ tự **hiện hành từ bàn giao 2026-08-12** là:

1. **Ngày 2026-08-13: test–retest nhãn trước** — 4 bài ngẫu nhiên, gán mù, lưu riêng và khóa nhãn lượt hai; chỉ sau đó mới mở nhãn lượt một để tính Kappa. Giao thức đầy đủ: `annotation-guideline.md` mục 8.1; checklist chống lộ nhãn: `technical-debt.md` mục 8.3.
2. **E1 bản 4 sau test–retest** — xin xác nhận riêng chi phí khoảng 3 USD, chạy vào file mới. Nếu σ `final_score` ≥ 2 thì dừng và chẩn đoán; không chạy E5.
3. **E5 bản 4 khi E1 đạt** — xin xác nhận chi phí riêng, dùng đúng bộ commit/prompt/model đã khóa; chưa chốt ngưỡng `publish` nếu chưa có quyết định mentor về lớp publish rỗng.
4. **Functional-clean** — chạy và báo cáo riêng `publish_rate`/false positive, tuyệt đối không gộp với Kappa/accuracy calibration.
5. **E3 baseline**, rồi **E6 held-out** sau khi có ngưỡng hợp lệ và đã có trần Kappa test–retest.

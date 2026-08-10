# Kế hoạch thí nghiệm và đo lường

**Phiên bản:** v1 (2026-07-27)
**Trạng thái:** E2, E4 đã chạy. **E1 phải chạy lại** (code chấm điểm đổi ở B7, B12 và đợt chuyển rubric 2026-08-10). Gold set **đã gán nhãn xong** 33/33; E3/E5/E6 còn chờ E1 và test-retest.

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
| **E1** | Độ ổn định điểm của agent qua nhiều lần chấm | Agent hiện có (đã xong) | σ điểm < 2 |
| **E2** | Retrieval lấy đúng đoạn không (recall@k) | KB đã dựng | recall@3 ≥ 0.9 (fact-check) — **đã đo: 1.00 (fact-check), 78,3% vs mốc 21,7% (brand)** |
| **E3** | Multi-agent có hơn single-agent không | Gold set | (không có ngưỡng - là kết quả nghiên cứu) |
| **E4** | Chi phí và độ trễ mỗi bài | Agent hiện có (đã xong) | (không có ngưỡng - là số liệu báo cáo) |
| **E5** | Ngưỡng quyết định tối ưu (calibration) | Gold set + **E1 đạt** | Kappa cao nhất trong dải quét |
| **E6** | Shadow-test trước khi vận hành | E5 | (xem mục 4.6 - phải viết lại cho khả thi) |

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

## 3a. KHOÁ CODE CHẤM ĐIỂM — 2026-08-10 (bản 2)

`rubrics.md` mục 10 quy định: ngưỡng calibrate được **chỉ có hiệu lực với đúng bộ (rubric version, prompt version, model)** đã dùng lúc đo. Nên trước khi chạy E1 và E5 phải chốt bộ đó lại, và ghi ra để về sau kiểm chứng được.

**Bộ đã khoá:**

| Thành phần | Giá trị |
|---|---|
| Commit | ghi lại khi commit đợt chuyển rubric. **Bản 1 (`56e1d6d`) đã hết hiệu lực** — khoá đó mở lại ngay trong ngày để chuyển nốt SEO và Content Quality sang rubric |
| Model | `claude-haiku-4-5-20251001` |
| Rubric version | v1 (`rubrics.md`) — **áp dụng cho cả 4 agent** |
| Prompt version | `51c0cba6c91e1435` *(bản 1 là `019c2d5e231aad48`, đổi vì SEO và CQ có prompt mới)* |
| Guideline gán nhãn | v1.3 (`annotation-guideline.md`) |
| Gold set | `labels.csv` 33/33, phân bố **10** `rejected` / **23** `needs_revision` / **0** `publish` (sau đợt rà lại 2026-08-10, xem `technical-debt.md` A3) |

`prompt_version` là SHA-256 của 4 system prompt nối theo thứ tự tên. Băm lại bất cứ lúc nào để kiểm prompt có bị đổi không:

```python
import hashlib, sys; sys.path.insert(0, "src")
from agents import content_quality, seo, compliance, brand_voice
ps = {"brand_voice_bv6": brand_voice._BV6_PROMPT,
      "compliance": compliance._LLM_PROMPT,
      "content_quality": content_quality._LLM_PROMPT,
      "seo": seo._LLM_PROMPT}
h = hashlib.sha256()
for k in sorted(ps): h.update(ps[k].encode())
print(h.hexdigest()[:16])      # phải ra 51c0cba6c91e1435
```

*(Bản 1 dùng `content_quality.SYSTEM_PROMPT` và `seo.SYSTEM_PROMPT` — hai tên đó **không còn tồn tại** sau khi chuyển rubric.)*

**Quy tắc trong thời gian khoá:** mọi thay đổi chạm vào đường chấm điểm — 4 agent, `scoring.py`, `graph.aggregator_node`, `compliance_rules.json`, `brand_rules.json`, `scoring.yaml` — đều **làm mất hiệu lực E1 và E5 đã chạy**, và phải đo lại. Sửa tài liệu, test, script gán nhãn thì không ảnh hưởng.

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

**Biến thể quan trọng - so rubric với cách hiện tại:** ✅ **đã chạy 2026-08-04**, kết quả đầy đủ ở `docs/rubrics.md` mục 9.1 và `docs/evidence/e1_rubric_v2_report.txt`.

Kết quả **âm**: rubric KHÔNG ổn định hơn thang 0-100 (σ `final_score` 0,28 → 1,43 trên 7 bài chung). Ghi lại nguyên văn đúng như đã cam kết. Chẩn đoán: rubric không tạo ra dao động mà làm dao động hiện ra - thang 0-100 tự do nuốt chỗ LLM lưỡng lự, còn rubric lượng tử hoá 0/1/2 rồi chia mẫu số nên khuếch đại lên. Điều kiện E5 vẫn đạt vì σ `final_score` = 1,33 < 2.

So sánh lại được nhờ `scripts/so_sanh_phuong_sai.py`, chạy trên **cùng bộ mẫu** - so trên tập khác nhau thì chênh lệch đến từ đổi mẫu chứ không phải đổi cách chấm.

**Quy mô:** 10 bài × 5 lần × 4 agent = 200 lần gọi LLM.

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

1. ~~**E1 phải đạt trước.** Bước nhảy 2 điểm chỉ có nghĩa nếu σ < 2.~~ ✅ **đạt (2026-08-04)** — điểm tổng σ = 1,33 sau khi Compliance chuyển sang rubric (σ = 0,28 với cách chấm cũ). **Nhưng có một lưu ý phải mang theo:** riêng Compliance đạt σ = 5,48 trên bài G-002. Điểm tổng ổn định vì trọng số làm loãng dao động đó, không phải vì nó không tồn tại — nên ngưỡng calibrate ra sẽ kém ổn định hơn với các bài mà Compliance dao động mạnh. Làm rubric Compliance trước sẽ cho ngưỡng đáng tin hơn.
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

1. **E4 chi phí + E1 độ ổn định** - chạy được ngay hôm nay, rẻ, và E1 quyết định có nên viết lại 4 prompt theo rubric hay không
2. Implement rubric (nếu E1 cho thấy cần) → chạy lại E1 để so phương sai
3. **E2 recall@k** khi dựng KB xong, trước khi nối RAG vào agent
4. Thu gold set (đang chạy song song, không phụ thuộc gì ở trên)
5. **E3 baseline** + **E5 calibration** khi có gold set
6. **E6 held-out test** sau cùng

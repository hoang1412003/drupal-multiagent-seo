# Kế hoạch thí nghiệm và đo lường

**Phiên bản:** v1 (2026-07-27)
**Trạng thái:** kế hoạch - chưa thí nghiệm nào được chạy

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
| **E2** | Retrieval lấy đúng đoạn không (recall@k) | KB đã dựng | recall@3 ≥ 0.9 (fact-check) |
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

Ba điểm chặn quan trọng:

1. **E1 chặn E5.** Nếu điểm dao động ±5 thì việc quét ngưỡng theo bước nhảy 2 điểm là vô nghĩa - mọi ngưỡng chọn ra chỉ là nhiễu.
2. **E1 cũng chặn việc implement rubric.** E1 là thí nghiệm quyết định số phận `rubrics.md`: nếu điểm 0-100 hiện tại đã ổn định bất ngờ thì luận điểm chính của rubric yếu đi, và nên biết **trước** khi viết lại 4 prompt.
3. **E2 chặn việc nối RAG vào agent** (`rag-design.md` mục 5).

**E1 và E4 chạy được ngay hôm nay** - không phụ thuộc gold set, không phụ thuộc rubric, không phụ thuộc KB. Đây là hai phép đo duy nhất trong danh sách không bị chặn bởi gì cả.

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

**Biến thể quan trọng - so rubric với cách hiện tại:** sau khi implement rubric v1, chạy lại E1 trên **cùng 10 bài đó** và so σ giữa hai cách chấm. Đây là bằng chứng thực nghiệm duy nhất cho luận điểm trung tâm của `rubrics.md` - và mục 9 của tài liệu đó đã ghi rõ rubric "chưa được chứng minh bằng số liệu là ổn định hơn". Dù kết quả ra hướng nào cũng là một kết quả nghiên cứu đáng đưa vào báo cáo.

**Quy mô:** 10 bài × 5 lần × 4 agent = 200 lần gọi LLM.

### 4.2. E2 - recall@k của retrieval

Đã đặc tả đầy đủ ở `rag-design.md` mục 5. Tóm tắt để đặt đúng vị trí trong chuỗi: ~20 cặp `(truy vấn, chunk đúng)` tự soạn, đo tỉ lệ chunk đúng nằm trong top-k, tiêu chí **recall@3 ≥ 0.9** cho KB fact-check. Không đạt thì **sửa chunking trước, đổi embedding sau**.

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

**Ước tính sơ bộ** (phải thay bằng số đo thật):

```
Một bài cẩm nang ~1.200 từ tiếng Việt
  → mỗi agent nhận ~3.000 token input (gồm system prompt)
  → 4 agent = ~12.000 token input
  → output JSON ~600 token/agent = ~2.400 token output

Chi phí/bài ≈ 12.000/1M × $1  +  2.400/1M × $5
            ≈ $0,012 + $0,012 = ~$0,025  (~650 VNĐ)
```

**Ngân sách toàn bộ chương trình thí nghiệm:**

| Phép đo | Số lần chấm bài | Chi phí ước tính |
|---|---|---|
| E1 (10 bài × 5 lần) | 50 | ~$1,25 |
| E1 biến thể (rubric) | 50 | ~$1,25 |
| E3 baseline (33 mẫu, 1 agent) | 33 | ~$0,40 |
| E5 chấm gold set (33 mẫu) | 33 | ~$0,82 |
| **Tổng** | | **dưới $5** |

Con số này quan trọng vì nó **loại bỏ "tốn kém" khỏi danh sách lý do không đo**. Toàn bộ chương trình đo lường rẻ hơn một bữa trưa.

**Một điểm dễ hiểu nhầm về E5:** quét nhiều mức ngưỡng **không tốn thêm tiền**. Chấm gold set một lần, lưu lại kết quả 4 agent, rồi quét ngưỡng bằng cách chạy lại **Aggregator** trên kết quả đã lưu - mà Aggregator là module tất định không gọi LLM (`architecture.md` mục 6). Đây chính là một lợi ích cụ thể của thiết kế Aggregator tất định, đáng nêu khi bảo vệ.

**Độ trễ cần đo riêng:** thời gian mỗi agent, thời gian toàn pipeline, và phần chồng lấn nhờ chạy song song. Con số này quyết định chu kỳ polling worker (`architecture.md` mục 9.2) - đặt 30 giây mà một bài chấm mất 40 giây thì worker sẽ chồng lệnh.

**Quy mô production (để trong báo cáo):** ước tính theo số bài VF O2O xuất bản mỗi tháng × chi phí/bài. Nếu không có con số thật thì nêu rõ là ước tính theo giả định, kèm giả định là bao nhiêu.

### 4.5. E5 - Calibration ngưỡng

Đã đặc tả đầy đủ ở `architecture.md` mục 8.2 (Recall/F1, Cohen's Kappa, quét ngưỡng theo Youden's Index). Hai điều kiện tiên quyết cần nhấn lại ở đây:

1. **E1 phải đạt trước.** Bước nhảy 2 điểm chỉ có nghĩa nếu σ < 2.
2. **Ngưỡng chốt được chỉ có hiệu lực với đúng bộ `(rubric version, prompt version, model)`** đã dùng khi calibrate. Đổi model là phải calibrate lại - mà `ANTHROPIC_MODEL` đang đọc từ biến môi trường nên có thể đổi mà không ai để ý.

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

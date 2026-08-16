# E3 — Baseline single-agent (chạy 2026-08-16)

Số liệu thô: [`e3_baseline_single.json`](e3_baseline_single.json) · Code: `scripts/eval_baseline_single.py`
Hợp đồng đo: [`evaluation-plan.md` mục 4.3](../evaluation-plan.md).

**Câu hỏi nghiên cứu:** kiến trúc 4 agent có thật sự hơn 1 agent làm tất không?
**Không có tiêu chí đạt/trượt** — đây là câu hỏi nghiên cứu, không phải cổng chất lượng.

> ## Kết luận
>
> **Hệ 4 agent thắng, nhất quán ở cả ba chế độ ngưỡng.** Và mạnh hơn thế: **tập bài sai của
> baseline là tập cha của tập bài sai của hệ 4 agent** — baseline sai thêm 4 bài, và **không
> thắng ở một bài nào**.
>
> Cái giá: hệ 4 agent tốn **+63% chi phí** và **+2,2 lượt gọi LLM/bài**.

## Thiết kế — gộp đúng phần LLM, giữ nguyên phần máy

Gộp **16 tiêu chí vốn do LLM chấm** thành một lần gọi. **17 tiêu chí đo bằng máy** (đếm ký tự,
regex, internal link) giữ **y hệt** ở cả hai hệ. Nhờ vậy biến số duy nhất là **số lần gọi LLM**,
không trộn với "máy đo hay LLM đo".

**Prompt gộp = nối nguyên văn 4 prompt hiện hành**, cố ý không viết lại — viết lại thì phép đo
thành "prompt mới viết thế nào" chứ không phải "gộp một lần gọi". Có test khoá điều này.

**Tiêm ở tầng `call_agent`, không phải `danh_gia_llm`:** mỗi agent tự hợp thức hoá output LLM
(loại trích dẫn bịa, ép enum). Tiêm ở tầng trên là bỏ qua hết khâu đó, cho baseline một lợi thế
không công bằng. Tiêm sâu hơn nên **agent chạy nguyên vẹn đường hợp thức hoá của nó**.

Không sửa một dòng nào trong đường chấm điểm — diff so với `04f10e1` vẫn rỗng, E1/E5/E6 còn hiệu lực.

## Kết quả — 4 chỉ số theo mục 4.3

### 1. Kappa với nhãn người

| Chế độ ngưỡng | 4 agent | baseline 1 gọi | Chênh |
|---|---|---|---|
| Ngưỡng đang chạy (`50/50/80`) | **0,369** | 0,270 | −0,099 |
| Ngưỡng tốt nhất của **chính mỗi hệ** | **0,406** | 0,302 | −0,104 |
| **k-fold CV** (cùng thiết kế E6, seed `20260816`) | **0,406** | 0,302 | −0,104 |

Ba chế độ cho cùng một kết luận, kể cả khi baseline được dùng ngưỡng riêng có lợi nhất cho nó.
Cả hai hệ đều chọn cùng bộ ngưỡng `veto=34, nr=50` — nên chênh lệch **không** đến từ ngưỡng.

### 2. Chất lượng theo lớp và theo bài

| | 4 agent | baseline |
|---|---|---|
| Số bài sai / 33 | **12** | 16 |
| F1 `rejected` | 0,76 | 0,74 |
| F1 `needs_revision` | **0,67** | 0,55 |
| Số bài gắn `critical` | **10** | 8 |

Nhãn người có đúng **10** bài `rejected`. Hệ 4 agent gắn `critical` cho **10** bài, baseline chỉ **8**.

**Bốn bài baseline sai thêm:** `G-007`, `P-007b`, `P-009a`, `P-010a` — ba trong bốn là mẫu
perturbation có lỗi **chèn có chủ đích**. Baseline **bỏ sót lỗi mà mình biết chắc là có**.

**Bài baseline đúng mà hệ 4 agent sai: KHÔNG CÓ BÀI NÀO.**

### 3. Chi phí

| | 4 agent | baseline | Chênh |
|---|---|---|---|
| Lượt gọi LLM / bài | 5,6 | **2,6** | −54% |
| Token vào / bài | 40.153 | **21.183** | −47% |
| Chi phí / bài | $0,0567 | **$0,0348** | **−39%** |
| Chi phí cả 33 bài | $1,87 | **$1,15** | −$0,72 |

⚠️ Baseline **không** xuống được 1 lượt gọi: CP3 (fact-check) tra KB và có hai prompt riêng nên
không gộp được. Con số đúng là **2,6 so với 5,6**, không phải "1 so với 4".

### 4. Độ trễ

| | 4 agent | baseline |
|---|---|---|
| Giây / bài (script, chạy **tuần tự**) | 34,8 | **26,9** |

⚠️ **Con số này KHÔNG nói baseline nhanh hơn trong production.** Cả hai đo trên script chạy
tuần tự. Pipeline thật (`graph.py`) fan-out **4 agent song song**, nên độ trễ production của hệ
4 agent ≈ agent **chậm nhất**, không phải tổng. Baseline chỉ có một lượt gọi lớn nên **không
song song hoá được**. Rất có thể production hệ 4 agent **nhanh hơn** baseline — muốn biết phải
đo trên pipeline thật, chưa làm.

## Vì sao baseline thua — cơ chế đọc được từ dữ liệu

Điểm trung bình từng agent:

| Agent | 4 agent | baseline | Chênh |
|---|---|---|---|
| content_quality | 78,6 | 80,7 | **+2,1** |
| compliance | 61,8 | 64,5 | **+2,7** |
| seo | 94,2 | 93,9 | −0,3 |
| brand | 84,3 | 84,1 | −0,2 |

**Baseline chấm rộng tay hơn ở đúng hai agent do LLM chi phối nhiều nhất** (CQ, Compliance), và
gần như không đổi ở hai agent chủ yếu do máy đo (SEO, Brand). Cộng với việc nó gắn `critical`
ít hơn (8 so với 10), bức tranh nhất quán:

> Nhét 16 tiêu chí thuộc 4 lĩnh vực vào một lời gọi làm LLM **tìm ra ít lỗi hơn** → điểm cao hơn
> → bài có lỗi lọt qua. Prompt chuyên biệt chỉ lo ~4 tiêu chí thì soi kỹ hơn.

Đây là **bằng chứng đo được cho luận điểm chuyên biệt hoá** mà `architecture.md` mục 4.3 trước
đây chỉ trích dẫn nghiên cứu bên ngoài.

## Giới hạn phải nêu khi báo cáo

1. **Hai hệ không tương đương hoàn toàn về cơ chế an toàn** (mục 4.3 đã lường trước). Cả hai
   dùng chung Aggregator nên veto Compliance vẫn còn, nhưng cờ `critical` của baseline do một
   lời gọi gộp sinh ra chứ không phải một agent chuyên trách.
2. **Một sai lệch cố ý ngoài "số lần gọi":** SEO khi gọi riêng dùng `boc_an_o=("body",)` để bóc
   chữ ẩn; CQ/CP thì không. Lần gọi gộp chỉ dùng được một biến thể, đã chọn theo CQ/CP. Nên SEO
   ở baseline nhìn thấy body **chưa bóc chữ ẩn**.
3. **n = 33.** Chênh lệch 4 bài trên 33 là tín hiệu rõ nhưng không phải khoảng tin cậy hẹp.
4. **Chỉ một model, một lần chạy.** Không đo lại nhiều lượt nên không có σ cho chính chênh lệch
   này — khác với E1, ở đây không biết chênh lệch 0,104 ổn định tới đâu.
5. **Độ trễ chưa đo trên pipeline thật** (xem cảnh báo ở mục 4).

## Kết luận cho báo cáo Sprint 3

Kiến trúc 4 agent **đáng giữ**, và nay có số để nói thay vì trích dẫn:

> *Gộp 4 lời gọi LLM thành một làm Kappa tụt từ 0,406 xuống 0,302 và số bài sai tăng từ 12 lên
> 16 trên 33 mẫu, trong đó baseline không thắng ở bài nào. Đổi lại nó rẻ hơn 39% và ít hơn 3
> lượt gọi mỗi bài. Với bài toán có quyền phủ quyết pháp lý, đánh đổi 39% chi phí lấy 4 bài
> phát hiện đúng là đáng.*

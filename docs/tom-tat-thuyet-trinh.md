# Tóm tắt thuyết trình — Hệ thống Multi-Agent AI kiểm duyệt nội dung Marketing

> **Hướng dẫn cho công cụ tạo slide:** File này đã chia sẵn theo slide. Mỗi mục
> `## Slide N` là một trang. Giữ nguyên các con số — chúng là kết quả đo thật,
> có file bằng chứng kèm theo. Không làm tròn, không tô hồng, không thêm số nào
> không có ở đây.
>
> Văn phong: kỹ thuật, điềm đạm, hướng tới hội đồng chấm đồ án. Ưu tiên bảng và
> sơ đồ hơn gạch đầu dòng dài.

---

## Slide 1 — Trang bìa

**Nghiên cứu và xây dựng hệ thống Multi-Agent AI hỗ trợ quy trình kiểm duyệt,
đánh giá và tối ưu hoá nội dung Marketing trước khi xuất bản trên nền tảng
Drupal CMS**

- Sinh viên thực tập: Thân Văn Hoàng
- Mentor: Đỗ Đức Cảnh
- Đơn vị: VinFast — O2O
- Sản phẩm bàn giao: Web App

---

## Slide 2 — Bài toán

**Hiện trạng:** nội dung Marketing trước khi xuất bản phải qua kiểm duyệt thủ
công. Người duyệt phải đồng thời soi bốn thứ khác nhau: chất lượng viết, SEO,
giọng thương hiệu, và tuân thủ quy định. Việc này chậm, và **kết quả phụ thuộc
người duyệt là ai**.

**Mục tiêu:** tự động hoá bước sàng lọc — bài vào trạng thái "Needs Review" thì
hệ thống tự chấm, trả báo cáo lỗi theo từng trường ngay trong giao diện soạn
thảo, để người duyệt tập trung vào phần cần phán đoán.

**Ràng buộc quan trọng nhất:** hệ thống **không được thay người quyết định**.
Nó chỉ được phép chặn hoặc cảnh báo — và mọi ngưỡng chặn phải **tính từ dữ liệu
gán nhãn thật**, không phải số áng chừng.

---

## Slide 3 — Kiến trúc tổng thể

Hai phía nối với nhau qua HTTP, không dùng chung cơ sở dữ liệu:

```
┌─────────────────┐         ┌──────────────────────────┐
│   Drupal CMS    │◄───────►│   Hệ Multi-Agent (Python) │
│                 │         │                          │
│ • Bài viết      │  JSON:API│ • api.py    nhận job     │
│ • Needs Review  │◄────────│ • worker.py chấm job     │
│ • Khối báo cáo  │  /api/v1 │ • PostgreSQL + pgvector  │
└─────────────────┘         └──────────────────────────┘
```

**Ba tiến trình phía Python:** service nhận job, worker chấm job, và các script
chạy tay (seed dữ liệu, dựng KB, chạy phép đo).

**Vì sao tách hai phía:** Drupal là client đầu tiên, không phải client duy
nhất. Hệ chấm điểm là một dịch vụ độc lập, có thể phục vụ CMS khác.

---

## Slide 4 — Bốn agent và Aggregator

| Agent | Chấm gì | Cách làm |
|---|---|---|
| **Content Quality** | cấu trúc, mạch lạc, độ đầy đủ | LLM |
| **SEO** | tiêu đề, meta, mật độ từ khoá, heading | luật + LLM |
| **Brand Voice** | giọng thương hiệu, xưng hô, thuật ngữ | **RAG** trên corpus thương hiệu |
| **Compliance** | tuân thủ quy định, đối chiếu thông số xe | **RAG + fact-check** trên KB |

**Aggregator** tổng hợp bốn kết quả thành một quyết định: `publish` /
`needs_revision` / `rejected`.

**Điểm thiết kế đáng chú ý:** Brand Voice và Compliance dùng **rubric tất
định** — cùng một đầu vào luôn cho cùng một cờ. LLM chỉ diễn giải, không tự
quyết mức phạt. Đây là lý do hệ thống có thể đo được độ ổn định.

---

## Slide 5 — Luồng chạy end-to-end

```
1. Biên tập viên đưa bài sang trạng thái "Needs Review" trong Drupal
2. Drupal bắn job sang hệ Multi-Agent (Bearer token riêng theo site)
3. Worker lấy bài đúng revision vừa lưu, chạy 4 agent song song
4. Aggregator tổng hợp → quyết định + danh sách lỗi theo từng trường
5. Ghi ngược kết quả về Drupal bằng compare-and-set (không ghi đè bản mới hơn)
6. Biên tập viên thấy báo cáo ngay trong giao diện soạn thảo
```

**Hai chi tiết kỹ thuật quan trọng:**

- **Đọc đúng revision.** Bài đã xuất bản rồi tạo bản nháp thì bản nháp
  **không phải** revision mặc định. Đọc nhầm là chấm nhầm nội dung.
- **Compare-and-set khi ghi ngược.** Nếu biên tập viên sửa bài trong lúc hệ
  thống đang chấm, kết quả cũ **không được** đè lên bản mới.

---

## Slide 6 — Đo lường: nguyên tắc

Phần này là trọng tâm của đồ án. Nguyên tắc xuyên suốt:

> **Không con số nào được báo cáo nếu không truy được về một lần chạy thật, với
> commit và phiên bản prompt đã khoá.**

Cơ chế bảo vệ đã dựng:

| Cơ chế | Chống điều gì |
|---|---|
| `prompt_version` do code tự tính | sửa prompt xong vẫn báo cáo số cũ |
| Manifest freeze + `release_sha256` | đổi dữ liệu sau khi đo |
| Ba lớp khoá đường trả phí | vô tình gọi API tốn tiền |
| Đánh dấu **hết hiệu lực** khi đường chấm đổi | dùng số cũ cho code mới |

Mọi kết quả cũ đều được giữ lại và **đánh dấu lịch sử**, không xoá — để truy
được vì sao thiết kế đổi.

---

## Slide 7 — Sáu phép đo đã chạy

| Mã | Câu hỏi | Kết quả |
|---|---|---|
| **E1** | Chấm lại nhiều lần có ra cùng quyết định không? | `decision_consistency = 0,96`, drift 0/50 ✅ |
| **E3** | Kiến trúc 4 agent có hơn một lời gọi gộp không? | **4 agent thắng**: Kappa 0,406 so với 0,302 |
| **E4** | Bằng chứng có truy nguồn đầy đủ không? | ✅ |
| **E5** | Ngưỡng quyết định tối ưu là bao nhiêu? | ⛔ **không chốt được — xem slide 8** |
| **E6** | Held-out test có lệch chọn mẫu không? | selection bias **+0,000** |
| **Test–retest nhãn** | Người gán nhãn có nhất quán với chính mình? | Kappa **1,000** |

**E3 đáng chú ý:** kiến trúc 4 agent thắng baseline một lời gọi gộp — sai thêm
4 bài và không thắng bài nào. Cái giá: **+63% chi phí**. Đây là bằng chứng
lượng hoá cho quyết định kiến trúc, không phải phỏng đoán.

---

## Slide 8 — Phát hiện quan trọng nhất: phép đo bác bỏ giả định của đề bài

**Đề bài yêu cầu:** *"có ngưỡng tính từ gold set 30–50 mẫu, không phải số áng
chừng"* — giả định hệ thống chấm điểm rồi so với một ngưỡng số.

**Đo thật cho thấy giả định đó không dùng được:**

| Phát hiện | Số liệu |
|---|---|
| Ngưỡng tốt nhất tìm được vẫn sai | `publish_min = 80` đề xuất **publish cho 9/33 bài** người gán nhãn nói cần sửa |
| Không có gì để học ngưỡng "được đăng" | gold set có **0 mẫu `publish`** |
| Kappa tụt vì chính nhánh publish | 0,406 với `publish=80`, **0,713** nếu vô hiệu hoá nhánh đó |

**Kết luận:** vấn đề không nằm ở chỗ chọn sai con số, mà ở chỗ **một ngưỡng
điểm tổng không mô tả được cách người thật ra quyết định**.

**Thiết kế đổi:** bỏ ngưỡng điểm, chuyển sang **luật theo mức tiêu chí**
(A → B → publish). Điểm tổng giữ lại nhưng chỉ còn giá trị chẩn đoán.

> Đây là kết quả nghiên cứu, không phải hạng mục dở dang: **phép đo bác bỏ giả
> định của chính kế hoạch.** Nếu chốt bừa một con số cho khớp đề bài thì đó mới
> là "số áng chừng".

---

## Slide 9 — Chính sách v2 và kết quả đo

Chính sách mới có **10 cổng**, mỗi cổng một ngưỡng calibrate từ gold set:

| ✅ ĐẠT (5) | ❌ CHƯA ĐẠT (5) |
|---|---|
| `e1_decision_consistency` = 0,96 | `gold_rejected_recall` = 0,60 (cần ≥ 0,80) |
| `gold_kappa` = **0,608** (cần ≥ 0,60) | `corrected_publish` = 19/30 |
| `gold_needs_revision_recall` = 0,957 | `paired_recovery` = 11/20 |
| `gold_false_publish` = **0/33** | `coverage_target_decision_parent` = 3/11 |
| `drift` = 0/50 | `coverage_failure` = 8 (cần 0) |

**Điều quan trọng nhất về 5 cổng đỏ:** cả năm đều **cùng một loại sai — chặn
quá tay, không cổng nào là để lọt**.

| Chỉ số | Giá trị | Ý nghĩa |
|---|---|---|
| precision của `publish` | **1,000** | mỗi lần hệ thống nói "đăng được" thì **luôn đúng** |
| `false_publish` | **0/33** | **không bài xấu nào lọt qua** |
| macro F1 | 0,738 | |

Với một hệ kiểm duyệt, sai theo hướng chặn nhầm **an toàn hơn nhiều** so với
thả lọt. Nhưng chặn quá tay làm giảm giá trị sử dụng, nên vẫn phải sửa.

---

## Slide 10 — Nguyên nhân đã truy được

Phân tích 5 cổng đỏ dẫn tới **một nguyên nhân chính**, đã ghi thành mục nợ
`B16`:

**Tiêu chí `BV3` phạt bài "lẫn hai kiểu xưng hô" — mà chính tài liệu thương
hiệu của dự án lại nói không có chuẩn xưng hô để mà nhất quán.**

| Nguồn trong repo | Nội dung |
|---|---|
| `brand_guideline.md` | *"Chưa đủ căn cứ để chốt xưng hô chuẩn"* — corpus 16 bài chia phiếu: `người dùng` 8, `bạn` 4, `khách hàng` 3, `quý khách` 1 |
| `rubrics.md` | nhưng `BV3` vẫn phạt "lẫn 2 cách" xuống mức chặn xuất bản |

Thêm một lỗi chồng lên: bộ so khớp **gộp hai khái niệm**. Câu *"**Người dùng**
nên kiểm tra hợp đồng"* bị bắt — nhưng đó là danh từ chỉ đối tượng, không phải
xưng hô với người đọc.

`BV3` là mã chặn nhiều nhất: **5/11 bài** ở bộ Corrected, trong đó có một bài
lẽ ra sạch tuyệt đối.

**Đã xác nhận cách sửa có hiệu lực:** bản sửa tiêu chí `A6` trước đó đưa số bài
bị chặn oan từ **10/18 xuống 0**.

---

## Slide 11 — Sản phẩm: giao diện

**Hai giao diện, hai đối tượng dùng:**

**1. Khối báo cáo trong Drupal** — cho biên tập viên. Hiện lỗi và rủi ro theo
từng trường, ngay trong màn hình soạn bài. Kiểm chứng qua 4 vòng sửa bằng ảnh
chụp trình duyệt thật.

**2. Console quản trị** — cho người vận hành. React 19 + TypeScript + Vite,
**8 màn hình**: Tổng quan, Jobs, Chi tiết job, Reviews, Chi tiết review, Nhật
ký, Cấu hình/KB, Kết quả đo, Kết nối, Người dùng.

**Nguyên tắc bảo mật áp dụng cho Console:**

- Phân quyền kiểm ở **server**, ẩn nút chỉ là tiện nghi
- Thao tác tốn tiền (chấm lại) có cổng xác nhận chi phí
- Mật khẩu tạm hiện đúng một lần, không vào bộ nhớ đệm
- Admin đang hoạt động cuối cùng **không thể** bị hạ quyền hay khoá

---

## Slide 12 — Chất lượng và kiểm thử

| | Số lượng |
|---|---|
| File test Python | **91** |
| Test JavaScript (Vitest) | **74** |
| Kết quả | **0 hỏng, 0 SKIP** |

Chạy tất cả bằng **một lệnh duy nhất** — kể cả bộ kiểm JS.

**Nguyên tắc đã áp dụng:** mỗi hàng rào kiểm tra đều được **thử ngược** — cố ý
làm hỏng đầu vào để xác nhận nó báo đỏ thật, rồi mới khôi phục.

Lý do: đã hai lần viết phép kiểm trông có vẻ chặt nhưng **không bao giờ đỏ**.
Một phép kiểm không bao giờ đỏ tệ hơn không có phép kiểm nào — nó tạo cảm giác
an toàn giả.

---

## Slide 13 — Triển khai

Bản demo chạy thật, không phải môi trường phát triển:

| | |
|---|---|
| Hạ tầng | AWS EC2 (Singapore) |
| Địa chỉ | `https://vf-multiagent.duckdns.org` |
| Bảo mật | HTTPS, chứng chỉ Let's Encrypt |
| Tiến trình | systemd, tự khởi động lại khi lỗi |
| Embedding | HuggingFace Space riêng (không nạp model 2 GB tại chỗ) |

Toàn bộ quy trình triển khai, cập nhật và các bẫy đã gặp được ghi lại trong
`docs/deployment-aws-demo.md` — để người tiếp nhận không phải dò lại từ đầu.

---

## Slide 14 — Còn lại và hạn chế

**Nói rõ để không ai hiểu nhầm mức độ hoàn thiện:**

| Hạng mục | Trạng thái |
|---|---|
| Sửa `BV3` (mục nợ B16) | chưa — gỡ được 2/5 cổng đỏ, không tốn chi phí |
| Đo lại bộ bốn sau khi sửa | chưa — ước ~$6–7 |
| Hoàn tất tài liệu vận hành | gần xong |
| `meta.calibrated` | vẫn `false` — **đúng sự thật**, không còn ngưỡng điểm để calibrate |
| `independent_label_reliability` | `not_demonstrated` — nhãn do một người gán |

**Hạn chế đã biết, không che giấu:**

- Gold set **33 mẫu**, do **một người** gán nhãn. Test–retest với chính người
  đó cho Kappa 1,000, nhưng **chưa chứng minh được độ tin cậy giữa nhiều người**.
- Bộ Corrected và Coverage là dữ liệu **tổng hợp** — đo khả năng phục hồi và
  cô lập, **không thay** cho đồng thuận AI–người trên bài thật.
- Bản demo là **máy demo**, không phải hạ tầng chịu tải.

---

## Slide 15 — Kết luận

**Đã làm được:**

1. Luồng end-to-end chạy thật trên Drupal, có bằng chứng
2. Báo cáo lỗi theo từng trường trong giao diện soạn thảo
3. Sáu phép đo với bằng chứng truy nguồn đầy đủ
4. Chứng minh bằng số rằng **kiến trúc 4 agent hơn một lời gọi gộp**
5. Chứng minh **không bài xấu nào lọt qua** (`false_publish = 0/33`)
6. Triển khai thật, có HTTPS

**Đóng góp đáng kể nhất về mặt nghiên cứu:**

> Phép đo **bác bỏ giả định ban đầu** rằng có thể chốt một ngưỡng điểm từ gold
> set. Thay vì chọn bừa một con số cho khớp kế hoạch, dự án đổi thiết kế theo
> đúng cái dữ liệu chỉ ra.

**Bài học kỹ thuật lớn nhất:**

> Những lỗi nguy hiểm nhất **không báo lỗi**. Hệ thống vẫn chạy, kết quả vẫn
> ra, chỉ có một cơ chế bảo vệ âm thầm ngừng hoạt động. Không bộ test nào tự
> tìm ra chúng — chỉ có thói quen dừng lại hỏi *"thay đổi này làm hỏng cái gì
> mà không kêu?"*

---

## Phụ lục — Nguồn số liệu

Mọi con số trong bài đều truy được:

| Nội dung | File bằng chứng |
|---|---|
| E1 v2 | `docs/evidence/e1_v2_2026-08-19c_report.md` |
| Gold v2 | `docs/evidence/` (đợt 2, 2026-08-19) |
| Corrected v2 | `docs/evidence/corrected_v2_2026-08-19d_report.md` |
| Coverage v2 | `docs/evidence/coverage_v2_2026-08-19d_report.md` |
| E5/E6 | `docs/evidence/e5_e6_ban4_report.md` |
| Điều tra BV3 | `docs/evidence/cp1_bv3_dieu_tra_2026-08-19.md` |
| Luồng end-to-end | `docs/evidence/tu_dong_hoa_e2e.txt` |
| Trạng thái hiện hành | `docs/technical-debt.md` mục 8.0-BIS |

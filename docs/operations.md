# Vận hành: nhật ký truy vết và vòng phản hồi người duyệt

**Phiên bản:** v1 (2026-07-27)
**Trạng thái:** mục 2 (nhật ký truy vết) **đã triển khai (2026-08-07)** — xem `architecture.md` mục 9 và `docs/evidence/tu_dong_hoa_e2e.txt`. Mục 3 (vòng phản hồi người duyệt) vẫn là thiết kế, chưa triển khai — không còn bị chặn bởi mục 2, xem mục 4

---

## 1. Hai hạng mục, một lý do chung

Hai thứ trong tài liệu này đều xuất phát từ cùng một câu hỏi: **sau khi hệ thống chạy thật, làm sao biết nó có đang chạy đúng không?**

Tất cả các phép đo trong `evaluation-plan.md` đều là ảnh chụp tại một thời điểm - đo trên gold set, tại một phiên bản, với một model. Chúng không nói được gì về hệ thống ba tháng sau, khi model đã đổi, prompt đã sửa, và loại nội dung đã trôi khỏi phân bố ban đầu.

| Hạng mục | Trả lời câu hỏi |
|---|---|
| **Nhật ký truy vết** | *"Bài này bị chặn hồi tháng trước, vì sao?"* — Drupal giữ được *điểm bao nhiêu*, nhưng không giữ *vì sao* (mục 2.1) |
| **Vòng phản hồi** | *"Hệ thống có còn khớp với phán đoán của người không?"* |

Cả hai đều rẻ nếu thiết kế từ đầu, và gần như không làm được nếu bỏ qua - vì dữ liệu đã mất.

---

## 2. Nhật ký truy vết

### 2.1. Vấn đề: mất bối cảnh chấm, không phải mất giá trị cũ

**Đính chính (2026-08-03).** Bản v1 của mục này viết rằng lần chấm sau *"ghi đè"* lần trước nên lịch sử mất hẳn. **Điều đó sai** - kiểm chứng trực tiếp trên Drupal local cho thấy Drupal bật revision trên content type Article, nên mỗi lần `write_back()` PATCH là một revision mới và giá trị cũ được giữ lại:

```sql
ddev mysql --table -e "SELECT r.entity_id AS nid, r.revision_id AS vid,
  r.field_ai_score_value AS score, FROM_UNIXTIME(nr.revision_timestamp) AS thoi_diem
  FROM node_revision__field_ai_score r
  JOIN node_revision nr ON nr.vid = r.revision_id ORDER BY r.entity_id, r.revision_id;"
```

```
nid | vid | score  | thoi_diem
  1 |   7 |  84.25 | 2026-07-27 03:37:09    <- thời stub (brand luôn = 100)
  1 |  14 |  84.25 | 2026-07-27 04:52:26
  1 |  19 | 81.125 | 2026-08-03 08:36:10    <- sau khi gỡ stub, BV6 chưa làm
  1 |  21 |  81.75 | 2026-08-03 09:09:00    <- sau khi BV6 chạy thật
```

**Vấn đề thật nằm ở chỗ khác: revision chỉ giữ 3 field AI, không giữ bối cảnh sinh ra chúng.** Cụ thể mất:

| Không được giữ | Hệ quả |
|---|---|
| Điểm + issues/flags riêng của từng agent trong 4 agent | Chỉ còn một chuỗi text đã gộp; không tách lại được agent nào chấm bao nhiêu |
| Trọng số, ngưỡng, model, phiên bản rubric lúc chấm | Con số `84.25` vô nghĩa nếu không biết nó tính bằng công thức nào - xem mục 2.3 |
| `input_tokens` / `output_tokens` | Không đối chiếu được chi phí thật với ước tính E4 |

Với một hệ thống có **rủi ro pháp lý** - nó chặn nội dung vì lý do tuân thủ luật quảng cáo - biết bài từng bị chấm bao nhiêu điểm mà không tái dựng được *vì sao* vẫn là lỗ hổng thật.

**Ảnh hưởng tới mức ưu tiên:** mục 4 xếp nhật ký truy vết là "Cao" với lý do *"dữ liệu không ghi lúc chạy là mất vĩnh viễn"*. Lý do đó không còn đúng với 3 field AI (Drupal giữ hộ), nhưng **vẫn đúng nguyên với `agent_results`, `config_meta` và `usage`** - ba thứ này không ai giữ hộ cả. Xem mục 4 đã hiệu chỉnh.

### 2.2. Ghi cái gì

Một bản ghi cho mỗi lần chấm, **append-only**, không bao giờ sửa hay xoá:

| Trường | Nội dung | Vì sao cần |
|---|---|---|
| `node_id`, `content_hash` | Bài nào, ở phiên bản nội dung nào | Phân biệt các lần chấm trên nội dung khác nhau. **Đã đổi từ `node_changed_at` sang `content_hash` lúc triển khai** — `editor-ui-design.md` mục 4.4 phát hiện `changed` của node nhảy ngay sau chính `write_back()` PATCH, nên mốc thời gian không dùng để so sánh nội dung được; hash nội dung thì không |
| `scored_at` | Thời điểm chấm | |
| `decision`, `final_score` | Kết quả | |
| `agent_results` | Điểm + issues/flags đầy đủ của cả 4 agent | Tái dựng được lý do, không chỉ kết luận |
| `veto_reason`, `note`, `missing_agents` | Đường đi đặc biệt | Phân biệt "bị chặn vì vi phạm" với "không chấm được" |
| `config_meta` | Toàn bộ khối `meta` của `scoring.yaml` lúc chấm | **Quan trọng nhất** - xem 2.3 |
| `usage` | `input_tokens`, `output_tokens` mỗi agent | Theo dõi chi phí thật, đối chiếu với ước tính E4 |

### 2.3. Vì sao `config_meta` là trường quan trọng nhất

Không có nó, một bản ghi cũ chỉ nói *"bài này bị từ chối, 42 điểm"* - và con số 42 vô nghĩa nếu không biết nó được tính bằng trọng số nào, ngưỡng nào, model nào, rubric phiên bản nào.

Có `config_meta` (`config-spec.md` mục 5), mỗi bản ghi **tự mang theo bối cảnh của chính nó**. Khi ngưỡng đổi ở lần calibrate sau, các bản ghi cũ vẫn diễn giải được thay vì thành rác.

Đây cũng là thứ cho phép trả lời câu hỏi khó nhất: *"nếu áp ngưỡng mới lên các quyết định cũ thì bao nhiêu quyết định thay đổi?"* - chạy lại Aggregator (tất định, không gọi LLM) trên `agent_results` đã lưu là ra ngay, không tốn một đồng API nào.

### 2.4. Lưu ở đâu

| Phương án | Ưu | Nhược | Đánh giá |
|---|---|---|---|
| **JSONL append-only** trong `multiagent/logs/` | Đơn giản nhất, đọc bằng pandas, không cần hạ tầng | Không truy vấn được từ Drupal | ✅ **Chọn cho phạm vi dự án** |
| Entity riêng trong Drupal | Xem được trong admin | Cần code Drupal, nặng | Ghi nhận cho production |
| Bảng riêng trong CSDL | Truy vấn tốt | Cần schema, migration | Thừa ở quy mô này |

Chọn **JSONL**: một dòng JSON mỗi lần chấm, ghi bằng `open(..., "a")`. Ở quy mô demo và gold set (vài trăm bản ghi) thì bất cứ thứ gì nặng hơn đều là over-engineering - và cùng dữ liệu đó nạp thẳng vào pandas để phân tích Sprint 3.

**Xoay vòng file:** một file mỗi tháng (`reviews-2026-07.jsonl`) để không phình vô hạn.

> **Đính chính 2026-08-07 — kết luận đã đổi từ JSONL sang bảng Postgres.** Lập luận cũ (*"bất cứ thứ gì nặng hơn đều là over-engineering"*) đúng ở thời điểm viết và **tiền đề của nó đã đổi**: lúc đó phía Multi-Agent chưa có CSDL nào, nên "bảng riêng" nghĩa là dựng thêm hạ tầng. Từ 2026-08-05 Postgres đã chạy sẵn cho kho vector, và bản triển khai tự động hoá dù sao cũng phải tạo bảng cho hàng đợi. Đây là **đổi kết luận, không phải bác bỏ lập luận**. Chi tiết: spec `2026-08-07-needs-review-automation-design.md` mục 2.1. Bảng thật đã chạy: `run_log` (`multiagent/src/audit.py`), bằng chứng chạy thật ở `docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 5.

### 2.5. Không ghi cái gì

- **Toàn văn bài viết.** Đã có trong Drupal; chép lại làm phình log và nhân bản dữ liệu. Chỉ lưu `node_id` + `content_hash`.
- **API key, thông tin xác thực.** Hiển nhiên nhưng dễ lọt qua đường log exception.
- **System prompt đầy đủ.** Chỉ lưu `prompt_version`.

---

## 3. Vòng phản hồi người duyệt

### 3.1. Vì sao cần

Calibration (E5) chốt ngưỡng dựa trên **33 mẫu tại một thời điểm**. Sau đó hệ thống chạy trên nội dung thật, và ba thứ trôi dần:

- Loại nội dung mới xuất hiện, khác phân bố gold set
- Model đổi (`ANTHROPIC_MODEL` đọc từ biến môi trường)
- Chuẩn mực nội bộ đội content thay đổi

Không có phản hồi thì không có cách nào phát hiện - hệ thống vẫn chạy, vẫn trả điểm, và không ai biết nó đã lệch.

Ngoài ra, phản hồi tích luỹ dần chính là **nguồn mẫu bổ sung cho gold set** ở lần calibrate sau, và loại mẫu quý nhất: những ca mà AI và người **bất đồng**.

### 3.2. Thu cái gì - càng ít càng tốt

Nguyên tắc: người duyệt đang làm việc khác, mọi thứ thêm vào đều là ma sát. Nếu form phản hồi mất quá 10 giây thì không ai điền, và dữ liệu thu được sẽ lệch về phía những người rảnh nhất chứ không phải những ca đáng quan tâm nhất.

Đặt ngay trong khối báo cáo ở giao diện soạn bài (`editor-ui-design.md` mục 4.1a):

```
┌─ Đánh giá AI ────────────────────┐
│ Đề xuất:  ⚠ Cần sửa              │
│ Điểm:     76.5 / 100             │
│ ...                               │
│ ─────────────────────────────────│
│ Bạn có đồng ý với đánh giá này?  │
│  ( ) Đồng ý                       │
│  ( ) Không đồng ý  → [lý do____] │
└───────────────────────────────────┘
```

Hai lựa chọn, ô lý do chỉ hiện khi chọn "Không đồng ý", và **không bắt buộc**. Bắt buộc nhập lý do sẽ khiến người ta chọn "Đồng ý" cho xong.

Ghi lại: `node_id`, `scored_at` của lần chấm được phản hồi, `agree` (bool), `reason` (text, có thể rỗng), `reviewer`, `submitted_at`.

### 3.3. Dùng phản hồi làm gì - và không làm gì

**Có làm:**

| Dùng để | Cách |
|---|---|
| Phát hiện trôi | Theo dõi tỉ lệ "không đồng ý" theo tháng. Tăng đột biến = tín hiệu điều tra |
| Tìm ca khó | Bài bị "không đồng ý" là ứng viên tốt nhất cho gold set lần sau |
| Tìm lỗi hệ thống | Nhiều phản hồi cùng nói một loại lỗi = có thể tiêu chí hoặc ngưỡng sai |

**Không làm - quan trọng hơn:**

> **Không tự động điều chỉnh ngưỡng theo phản hồi.**

Nghe hấp dẫn nhưng sai về mặt phương pháp: phản hồi thu theo kiểu tự nguyện là **mẫu thiên lệch** (người ta phản hồi khi bất đồng nhiều hơn khi đồng ý), và không mù (người duyệt **đã thấy** kết quả AI trước khi phản hồi - đúng vấn đề neo mà `annotation-guideline.md` mục 2 cấm khi gán nhãn).

Ngưỡng chỉ được đổi qua **calibration có kiểm soát trên gold set gán nhãn mù**. Phản hồi là **tín hiệu để quyết định có nên calibrate lại hay không**, không phải đầu vào trực tiếp của phép tính.

Ranh giới này đáng nêu rõ khi bảo vệ - nó cho thấy hiểu vì sao nhãn phải mù, chứ không chỉ làm theo quy trình.

### 3.4. Lưu ở đâu

Cùng cơ chế JSONL, file riêng (`feedback-2026-07.jsonl`). Khớp với bản ghi truy vết qua cặp `(node_id, scored_at)`.

Nếu phần Drupal chưa kịp, có thể thu thủ công trong giai đoạn demo (người duyệt nói, mình ghi) - dữ liệu vẫn dùng được, chỉ ít hơn.

---

## 4. Thứ tự và mức ưu tiên

| Hạng mục | Ưu tiên | Vì sao |
|---|---|---|
| Nhật ký truy vết | **✅ Đã triển khai (2026-08-07)** | Chỉ vài chục dòng code. **`agent_results` / `config_meta` / `usage` không ghi lúc chạy là mất vĩnh viễn** - không ai giữ hộ ba thứ này. Bảng thật: `run_log` (Postgres, mục 2.4), bằng chứng chạy thật `docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 5 |
| Vòng phản hồi | Trung bình | **Nay hết bị chặn**: cần khớp với bản ghi truy vết qua cặp `(node_id, scored_at)` (mục 3.4), và cặp đó **đã có sẵn** trong `run_log` từ 2026-08-07. Vẫn cần module Drupal (`vf_ai_review`) làm ô nhập phản hồi trước khi thu được dữ liệu thật - không có nó vẫn demo được |

**Hạ từ "Cao" xuống "Trung bình-cao" (2026-08-03)** sau khi mục 2.1 được đính chính: 3 field AI đã được Drupal giữ qua revision, nên rủi ro "mất trắng dữ liệu" nhỏ hơn bản v1 mô tả. Phần thật sự mất vĩnh viễn thu hẹp lại còn bối cảnh chấm. Hạng mục gấp hơn ở thời điểm đó là **UI báo cáo trong editor** - deliverable bắt buộc của đề bài; mục đó đã xong (`docs/editor-ui-design.md` mục 1), và tới lượt nhật ký truy vết được làm cùng đợt tự động hoá.

**Nhật ký truy vết nên bật trước khi chạy các thí nghiệm**, không phải sau. E1 (chấm 10 bài × 5 lần) sinh ra đúng loại dữ liệu mà log này lưu - có log sẵn thì phân tích phương sai là đọc file, không có thì phải tự chế cách lưu riêng cho thí nghiệm.

---

## 5. Ảnh hưởng lên code

**Đã triển khai (2026-08-07), khác thiết kế gốc ở cách lưu — xem mục 2.4:**

| File | Thay đổi |
|---|---|
| `src/audit.py` *(đã có)* | `ghi(...)` INSERT một dòng vào bảng Postgres `run_log` (`CREATE TABLE IF NOT EXISTS`, không xoay file theo tháng — bảng không phình theo cách JSONL phình) |
| `src/graph.py`, `src/worker.py` | Gọi `audit.ghi()` sau khi có `report`, trước khi write-back |
| `src/ai_core.py` | Trả thêm `usage`, ghi vào `run_log.usage` |
| `drupal/.../vf_ai_review` | Ô phản hồi trong khối báo cáo — **chưa làm**, thuộc mục 3 (vòng phản hồi), không thuộc phần nhật ký truy vết |
| `multiagent/scripts/test_audit.py` | Test: bản ghi đúng schema, `final_score = NULL` giữ nguyên khi Compliance lỗi, không lọt bí mật |

Không còn thư mục `multiagent/logs/` hay vấn đề `.gitignore` cho file log — dữ liệu nằm trong Postgres cùng container với `kb_chunk`.

---

## 6. Chưa chốt

| Hạng mục | Ghi chú |
|---|---|
| Thời gian giữ log | Chưa cần quyết trong phạm vi dự án; production thì gắn với chính sách lưu trữ dữ liệu |
| Ai xem được phản hồi | Hiện chưa có phân quyền; production cần |
| Hiển thị lịch sử chấm trong editor | `editor-ui-design.md` mục 9 đã ghi nhận; cần log này làm nền |
| Cảnh báo tự động khi tỉ lệ bất đồng tăng | Nice-to-have; ở quy mô hiện tại xem thủ công là đủ |

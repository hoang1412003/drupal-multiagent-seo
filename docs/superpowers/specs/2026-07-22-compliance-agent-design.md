# Thiết kế: Compliance Agent (Sprint 2 — phần 1/5)

**Ngày:** 2026-07-22
**Phạm vi:** Đây là sub-project đầu tiên trong 5 phần của Sprint 2 (theo `docs/roadmap.md`), được ưu tiên làm trước vì không phụ thuộc tài liệu bên ngoài (khác với Brand Voice Agent — đang chờ brand guideline). Thứ tự các phần còn lại: Compliance Agent (tài liệu này) → Hoàn thiện Aggregator → Gold set collection → UI báo cáo → Brand Voice Agent (RAG).

## 1. Mục tiêu

Triển khai Compliance Agent thật, thay cho stub hiện tại trong `src/graph.py` (luôn trả điểm 100, không đánh giá gì). Theo `docs/architecture.md` mục 5.4, agent này kết hợp 2 cơ chế:

1. **LLM** — đánh giá claim nhạy cảm/thổi phồng thiếu căn cứ, nguy cơ vi phạm luật quảng cáo, thông tin giá/khuyến mãi gây hiểu nhầm. Tự chấm `score` (0-100) và tự tạo `flags` với severity tùy suy luận.
2. **Rule-based (so khớp cứng)** — danh sách từ/cụm từ cấm đã biết trước, đảm bảo không bỏ sót các trường hợp đã biết chắc là vi phạm, không phụ thuộc hoàn toàn vào khả năng suy luận của LLM.

## 2. Cấu trúc file blacklist

File mới: `src/agents/compliance_rules.json`

```json
{
  "phrases": [
    {"text": "tốt nhất", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "số 1", "severity": "critical", "rule": "So sánh tuyệt đối không có căn cứ (Luật Quảng cáo)"},
    {"text": "duy nhất", "severity": "critical", "rule": "Cường điệu tuyệt đối không có căn cứ (Luật Quảng cáo)"}
  ]
}
```

- Mỗi entry có sẵn field `severity` (hiện tại luôn `"critical"`) thay vì mảng string thuần — để sau này có thể hạ mức 1 từ cụ thể xuống `low`/`medium` chỉ bằng sửa JSON, không cần sửa code Python.
- Sẽ soạn sẵn ~10-15 cụm phổ biến dựa trên Luật Quảng cáo VN làm bản nháp; người dùng review/chỉnh lại sau (không cần đúng/đủ ngay từ đầu).
- Matching: so khớp chuỗi con (substring), không phân biệt hoa/thường, quét trên `title + body` gộp lại.

## 3. Module `src/agents/compliance.py`

Theo đúng pattern của `content_quality.py`/`seo.py` (SYSTEM_PROMPT + OUTPUT_SCHEMA + hàm `run()` gọi `ai_core.call_agent()`), cộng thêm phần rule-based:

- `SYSTEM_PROMPT`: yêu cầu LLM đánh giá claim phóng đại/thông tin giá gây hiểu nhầm, tự chấm `score` (0-100), tự tạo `flags` (`severity`/`rule`/`excerpt`), trả lời bằng tiếng Việt (nhất quán với 2 agent đã có).
- `OUTPUT_SCHEMA`: `{score: int, flags: [{severity, rule, excerpt}]}` — khớp `architecture.md` mục 5.4.
- Hàm rule-based riêng (thuần Python, không gọi LLM): đọc `compliance_rules.json`, quét `title + body`, mỗi cụm khớp → 1 flag `severity: "critical"`.
- `run(title, body)`: gọi cả LLM (`call_agent`) và rule-based, **gộp `flags` của cả 2 nguồn** thành 1 danh sách, giữ nguyên `score` do LLM tự chấm (không ép/sửa số).

## 4. Quyết định thiết kế quan trọng: không ép `score` khi có rule-based match

Đã cân nhắc 2 hướng:

- **(Đã bỏ)** Ép `score < 50` khi có rule-based match, để "hợp lý hóa" quyết định rejected.
- **(Chọn)** Giữ nguyên `score` do LLM tự chấm; chỉ dựa vào flag `critical` để kích hoạt veto.

**Lý do chọn hướng 2:**

1. Logic veto trong `aggregator_node` hiện tại đã dùng `OR`: `if compliance["score"] < 50 or has_critical_flag: decision = "rejected"`. Chỉ cần rule-based tạo 1 flag critical là veto đã tự động kích hoạt đúng, **không cần ép score để veto hoạt động**.
2. Ép số sẽ làm `field_ai_score` không phản ánh đúng chất lượng thật của bài viết (dữ liệu bị "làm giả" một cách âm thầm) — ảnh hưởng nếu sau này dùng con số này để thống kê/so sánh theo thời gian.
3. Đúng tinh thần `architecture.md` mục 6.2: "Compliance có quyền phủ quyết riêng, **độc lập với điểm tổng**" — score và decision là 2 trục riêng biệt, không cần trộn lẫn.
4. Vấn đề duy nhất của hướng 2 ("điểm cao mà vẫn rejected, gây khó hiểu") được giải quyết bằng cách **giải thích rõ lý do** (mục 5) thay vì sửa số liệu.

## 5. Thay đổi trong `src/graph.py`

**`compliance_node`** — thay stub cũ bằng gọi thật, theo pattern try/except giống `content_quality_node`/`seo_node` (agent lỗi → `None`, để Aggregator xử lý fail-safe theo cơ chế đã có):

```python
def compliance_node(state: ContentReviewState) -> dict:
    try:
        result = compliance.run(state["title"], state["body"])
    except Exception:
        result = None
    return {"compliance_result": result}
```

`brand_node` giữ nguyên stub — ngoài phạm vi tài liệu này.

**`aggregator_node`** — thêm `veto_reason` vào report khi veto xảy ra do flag critical (không phải do điểm thấp):

```python
veto_reason = None
if compliance["score"] < 50 or has_critical_flag:
    decision = "rejected"
    if has_critical_flag and compliance["score"] >= 50:
        veto_reason = "Bị từ chối do vi phạm Compliance (severity: critical), độc lập với điểm tổng."
...
if veto_reason:
    report["veto_reason"] = veto_reason
```

**`write_back_node`** — in `veto_reason` (nếu có) lên đầu danh sách `field_ai_suggestions`, trước các dòng issue/flag chi tiết từng agent, để đội content thấy lý do ngay dòng đầu.

## 6. Kế hoạch kiểm thử

1. **Test rule-based riêng** (thuần Python, không cần LLM/Drupal): xác nhận cụm từ trong blacklist → sinh đúng flag `critical`, không phân biệt hoa/thường.
2. **Smoke test `compliance.run()` thật** (`scripts/smoke_test_compliance.py`, theo pattern `smoke_test_ai_core.py`): chạy với 1 đoạn chứa từ cấm + 1 đoạn sạch, xác nhận LLM + rule-based gộp flags đúng.
3. **Verify lại trên Drupal thật**: chạy lại `scripts/smoke_test_graph.py` / `scripts/run_all_samples.py` trên bài mẫu Sprint 1 *"VF3 - Chiếc xe điện tốt nhất thế giới..."* (đã tạo sẵn, cố ý chứa "tốt nhất") — xác nhận lần này `decision = rejected` thật (compliance thật + rule-based), khác với Sprint 1 (lúc đó compliance stub luôn = 100).

## 7. Ngoài phạm vi (để dành các phần sau của Sprint 2)

- Brand Voice Agent (RAG) — chờ brand guideline.
- Hoàn thiện toàn bộ logic Aggregator (trọng số/ngưỡng calibration) — sub-project riêng kế tiếp.
- Gold set collection, UI báo cáo Drupal — các sub-project riêng sau đó.
- Retry/backoff khi LLM lỗi — đã ghi nhận là hạng mục hardening chung, không thuộc yêu cầu cụ thể của Compliance Agent.
- Test tự động (pytest) — dự án hiện dùng script test thủ công nhất quán (`scripts/smoke_test_*.py`); giữ nguyên phong cách này, không thêm framework test mới trong phạm vi tài liệu này.

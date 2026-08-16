# E1 — Độ ổn định điểm, bản khoá 4 (chạy 2026-08-16)

Số liệu thô: [`e1_sau_cp4_deadline_guard.json`](e1_sau_cp4_deadline_guard.json).
Hợp đồng đo: [`evaluation-plan.md` mục 4.1](../evaluation-plan.md).

**Kết luận: σ `final_score` = 1,60 < 2 → ĐẠT. Cổng sang E5 mở.**

## Truy vết — bộ đã dùng

| Thành phần | Giá trị |
|---|---|
| HEAD thực tế | `08cebe33b1a61380a95cfa1ea8450efcfbdb3484` (nhánh `docs/test-retest-2026-08-15`) |
| Score-path snapshot | `04f10e1` — đã xác minh là tổ tiên của HEAD |
| `prompt_version` | `020738e209017213` — code tự tính, và ghi vào `_meta` của file kết quả |
| Model | `claude-haiku-4-5-20251001` |
| `meta.calibrated` | `false` tại thời điểm đo |
| Mẫu | `G-001`..`G-010`, mỗi bài 5 lượt = **50 lượt** |
| File đích | **chưa tồn tại** trước lượt chạy → không có nguy cơ resume trộn dữ liệu hai bản code |

### Diff đường chấm so với snapshot: rỗng

Đã kiểm `multiagent/src/agents/`, `graph.py`, `scoring.py`, `retrieval.py`, `kb/`,
`config/scoring.yaml` — **không file nào đổi** so với `04f10e1`.

**Một ngoại lệ đã kiểm chứng:** `multiagent/config/model_pricing.yaml` là file **mới** (P5 thêm,
không tồn tại ở `04f10e1`). Theo tiêu chí đã làm rõ ở `evaluation-plan.md` mục 3a
(2026-08-16), file này **ngoài** đường chấm vì chỉ `review_platform/admin/queries.py` và
`scripts/test_admin_dashboard.py` đọc nó, còn `config.py` hardcode đúng một đường dẫn tới
`scoring.yaml` chứ không quét thư mục. Kiểm lại bất cứ lúc nào:

```bash
grep -rn "model_pricing.yaml" multiagent/src multiagent/scripts --include=*.py | grep -v ".venv"
```

### Lỗi môi trường phát hiện ở preflight

`.env` có **BOM** ở đầu file → `python-dotenv` đọc tên biến đầu tiên thành
`﻿ANTHROPIC_API_KEY`, khiến `os.environ.get("ANTHROPIC_API_KEY")` trả `None`. Chạy
thẳng thì E1 chết ở lần gọi API đầu tiên, **sau khi** đã nạp BGE-M3. Đã gỡ BOM trước lượt
chạy; `.env` không nằm trong git nên không có commit nào cho việc này.

## Kết quả từng bài

| Bài | CQ tb (σ) | SEO tb (σ) | Brand tb (σ) | Compliance tb (σ) | Tổng tb (σ) |
|---|---|---|---|---|---|
| G-001 | 81,2 (0,00) | 95,0 (0,00) | 83,3 (0,00) | 53,3 (4,55) | 76,12 (1,36) |
| G-002 | 84,3 (3,18) | 95,0 (0,00) | 91,7 (0,00) | 100,0 (0,00) | 92,99 (0,79) |
| G-003 | 74,7 (5,37) | 96,0 (2,24) | 80,0 (0,00) | 60,0 (9,15) | 75,88 (3,83) |
| G-004 | 76,2 (5,19) | 95,0 (0,00) | 82,0 (4,47) | 63,4 (7,47) | 77,57 (2,39) |
| G-005 | 72,5 (5,55) | 100,0 (0,00) | 91,7 (0,00) | 65,0 (3,76) | 80,56 (2,09) |
| G-006 | 91,3 (3,45) | 95,0 (0,00) | 88,0 (4,47) | 43,4 (3,71) | 76,83 (1,96) |
| G-007 | 81,6 (0,94) | 95,0 (0,00) | 80,0 (0,00) | 58,3 (0,00) | 76,89 (0,23) |
| G-008 | 72,5 (5,59) | 100,0 (0,00) | 91,7 (0,00) | 65,7 (3,18) | 80,77 (0,44) |
| G-009 | 58,7 (3,45) | 90,0 (0,00) | 83,3 (0,00) | 67,1 (3,89) | 73,65 (1,56) |
| G-010 | 78,6 (0,00) | 100,0 (0,00) | 70,0 (0,00) | 48,0 (4,47) | 71,55 (1,34) |

## Chỉ số tổng hợp

| Đại lượng | σ trung bình | σ lớn nhất | Đạt < 2? |
|---|---|---|---|
| `content_quality` | 3,27 | 5,59 | ❌ |
| `seo` | **0,22** | 2,24 | ✅ |
| `brand` | 0,89 | 4,47 | ✅ |
| `compliance` | 4,02 | 9,15 | ❌ |
| **`final_score`** | **1,60** | 3,83 | ✅ **ĐẠT** |

Tỉ lệ lượt chấm ra cùng một `decision`: **92%** (trung bình theo bài của tỉ lệ lượt trùng
decision phổ biến nhất — `eval_stability.py:222`).

**Vì sao hai agent trượt mà phép đo vẫn đạt:** tiêu chí σ < 2 áp cho `final_score`, vì đó
mới là đại lượng E5 quét ngưỡng lên (`evaluation-plan.md` mục 4.1). σ của từng agent chỉ
quan trọng qua đường đóng góp vào điểm tổng.

### Đóng góp vào phương sai điểm tổng (trọng số² × σ²)

```
compliance       0,30² × 4,02²  =  1,454   67%
content_quality  0,25² × 3,27²  =  0,668   31%
brand            0,25² × 0,89²  =  0,050    2%
seo              0,20² × 0,22²  =  0,002    0%
```

Compliance vẫn là nguồn dao động chính, đúng như bản 2.

## So với bản khoá 2 — dự đoán về CP4 được xác nhận

Bản 2 (`e1_sau_rubric_4_agent.json`, 2026-08-11) đã **hết hiệu lực** làm kết quả hiện hành,
nhưng so sánh được vì cùng 10 mẫu, cùng 5 lượt, cùng phương pháp.

| Agent | Bản 2 | Bản 4 | Thay đổi |
|---|---|---|---|
| `compliance` | 4,68 | **4,02** | −0,66 |
| `content_quality` | 4,38 | **3,27** | −1,11 |
| `brand` | 1,44 | **0,89** | −0,55 |
| `seo` | 0,27 | **0,22** | −0,05 |
| **`final_score`** | 1,79 | **1,60** | **−0,19** |
| Tỉ lệ cùng decision | 88% | **92%** | +4 điểm |

`technical-debt.md` mục 8.1 đã ghi dự đoán **trước** lượt đo này:

> *"**Kỳ vọng:** σ compliance nên **giảm** so với 4,68 — CP3 bớt báo động giả thì bớt lật
> mức giữa các lượt. Giảm là bằng chứng thêm cho B14; không giảm là tín hiệu còn nguồn dao
> động khác chưa tìm ra."*

σ compliance giảm 4,68 → 4,02. **Dự đoán đúng.** Đây là bằng chứng độc lập cho chẩn đoán
B14/CP4: chốt chặn thời hạn tất định đã cắt bớt nguồn dao động thật, không phải chỉ làm
đẹp con số.

⚠️ **Không diễn giải quá:** cả bốn agent đều giảm, kể cả `seo` vốn không bị CP4 chạm tới.
Nên một phần mức giảm có thể đến từ dao động giữa hai lượt đo chứ không phải riêng CP4.
Điều khẳng định được là **giảm, đúng chiều dự đoán**; không khẳng định được toàn bộ 0,66
là công của CP4.

## E4 — chi phí và độ trễ (thu được kèm, cùng lượt chạy)

| | |
|---|---|
| Số lượt chấm | 50 |
| Số lần gọi LLM / lượt | 5,6 |
| Input token / lượt | 42.331 |
| Output token / lượt | 3.815 |
| Chi phí / lượt | **$0,0614** |
| **Chi phí toàn bộ phép đo** | **$3,07** |
| Độ trễ / lượt | 39,3 giây |

Độ trễ đo trên script chạy 4 agent **tuần tự**; pipeline thật (`graph.py`) chạy song song
nên nhanh hơn. Con số này **không** thay thế E4 đầy đủ, nhưng nó có provenance đủ (cùng
HEAD, cùng `prompt_version`, cùng model) — khác với số E4 cũ mà `technical-debt.md` mục 8.9
ghi là "thiếu provenance đầy đủ".

## Mở cổng gì

E5 được phép chạy (`technical-debt.md` mục 8.2): đo vào **file mới**, guard phải từ chối
file bản 3 trước khi gọi API, và cần xác nhận chi phí riêng ~$2.

**Phải quyết trước khi bắt đầu E5** (`evaluation-plan.md` mục 4.6): E6 dùng **k-fold** hay
**tách cứng 20%**. Với 33 mẫu, tách cứng chỉ còn ~7 mẫu để chọn ngưỡng — tài liệu khuyên
cân nhắc k-fold. Chưa quyết mà chạy E5 là tự khoá mình vào một lựa chọn thống kê chưa cân
nhắc.

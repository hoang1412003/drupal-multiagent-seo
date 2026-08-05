# Việc phải làm trước khi demo / bàn giao

**Cập nhật:** 2026-08-04

Danh sách này **không phải nợ kỹ thuật** — code không thiếu gì. Đây là những
thứ đúng khi phát triển nhưng **sai khi trình bày**, cộng vài chỗ dễ quên khi
chạy trên máy khác.

Mỗi mục ghi kèm **lệnh kiểm** để biết chắc trạng thái hiện tại, thay vì tin
vào trí nhớ.

---

## 1. Bật lại CSS/JS aggregation trong Drupal

**Trạng thái 2026-08-04: ĐANG TẮT** (`css.preprocess: false`).

**Kiểm:**

```bash
cd drupal
ddev drush config:get system.performance
```

**Bật lại:**

```bash
ddev drush config:set system.performance css.preprocess 1 -y
ddev drush config:set system.performance js.preprocess 1 -y
ddev drush cr
```

**Vì sao đang tắt:** khi làm module `vf_ai_review`, aggregation bật thì Drupal
phục vụ **bản CSS gộp đã cache**. Sửa file xong reload không thấy gì đổi, rất
dễ đi tìm lỗi trong code trong khi nguyên nhân chỉ là cache.

**Vì sao phải bật lại:** để `false` thì mỗi file CSS/JS là một request riêng,
trang admin tải chậm thấy rõ. Người xem demo thấy giật sẽ đánh giá hệ thống,
trong khi nguyên nhân chỉ là một cấu hình dev quên tắt.

⚠️ **Còn định sửa CSS của `vf_ai_review` thì để tắt cho tới khi xong**, không
thì lại rơi vào đúng cái bẫy cache ở trên.

---

## 2. Dựng lại knowledge base nếu chạy trên máy khác

`multiagent/src/kb/chroma/` **bị `.gitignore` chặn** (dòng 13) — cố ý, vì KB là
dữ liệu dẫn xuất, dựng lại được từ `specs.json` và `docs/brand/corpus/`. Commit
file nhị phân 9,3 MB vào git thì mỗi lần nạp lại KB sinh một bản mới trong
lịch sử.

**Hệ quả: máy mới clone repo về sẽ KHÔNG có KB.**

```bash
cd multiagent
.venv/Scripts/python.exe src/kb/build_kb.py
.venv/Scripts/python.exe src/kb/build_brand_kb.py
```

**Nếu quên:** hệ thống **không sập** — `retrieve()` ném exception, CP3 và BV6
trả `NA` (không phải 0), pipeline vẫn chạy với các tiêu chí còn lại. Đó là
nhánh `try/except` trong `_cp3_so_lieu()` và `_bv6_giong_van()`. Nhưng demo mà
thiếu hai tiêu chí RAG thì mất đúng phần đáng khoe nhất.

**Kiểm nhanh KB có sẵn chưa:**

```bash
.venv/Scripts/python.exe scripts/eval_retrieval.py     # phải ra recall@3 = 1.00
```

---

## 3. Nói đúng về ngưỡng: CHƯA calibrate

`multiagent/config/scoring.yaml` có `meta.calibrated: false`. Hệ thống **tự in
cảnh báo** mỗi lần chạy:

```
WARNING:root:[config] Đang dùng ngưỡng minh hoạ, chưa calibrate từ gold set.
```

Cảnh báo đó tồn tại để **không lỡ trình bày kết quả chạy bằng ngưỡng minh hoạ
như thể đã calibrate**. Khi demo, nói rõ: trọng số 0.25/0.20/0.25/0.30 và
ngưỡng 80/50 là **giá trị tạm**, calibration là việc của Sprint 3 và đang chờ
gold set được gán nhãn.

Đừng tắt cảnh báo đi cho gọn màn hình.

---

## 4. Kiểm model đang chạy khớp với model lúc đo

`ANTHROPIC_MODEL` đọc từ biến môi trường (`.env`), nên **đổi lúc nào cũng
được mà không ai để ý**. Mọi số liệu trong `docs/evidence/` đo bằng
`claude-haiku-4-5-20251001`.

```bash
cd multiagent
.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'src'); import ai_core; print(ai_core.MODEL)"
```

Khác model thì **mọi con số σ, chi phí, độ trễ trong báo cáo không còn áp
dụng** — `rubrics.md` mục 10 yêu cầu calibrate lại. `src/config.py` cũng sẽ tự
cảnh báo một khi `meta.model` đã được điền.

---

## 5. Chạy lại toàn bộ test ngay trước khi demo

```bash
cd multiagent
for f in scripts/test_*.py; do .venv/Scripts/python.exe "$f" > /dev/null || echo "FAIL $f"; done
```

27/27 bộ tính đến 2026-08-05. Test không cần API key, không cần Drupal, không
cần KB — chạy được ở bất cứ đâu, mất vài giây.

Riêng test hợp đồng phía PHP chạy trong container:

```bash
cd drupal
ddev exec php scripts/test_ai_report_renderer.php
```

---

## 6. Số liệu đã lưu sẵn, không cần chạy lại

Ba lần đo E1 tốn khoảng **$8**. Toàn bộ kết quả thô đã commit, **không phải
chạy lại để lấy số cho báo cáo**:

| File | Nội dung |
|---|---|
| `docs/evidence/e1_stability_raw.json` | thang 0-100, 7 bài × 5 lượt |
| `docs/evidence/e1_stability_rubric.json` | rubric v1, 8 bài × 5 lượt |
| `docs/evidence/e1_stability_rubric_v2.json` | rubric v2, 10 bài × 5 lượt |
| `docs/evidence/e1_rubric_v2_report.txt` | báo cáo + 2 bảng so sánh |
| `docs/evidence/cp_phan_bo_muc.txt` | phân bố mức từng tiêu chí Compliance |
| `docs/goldset/label_helper_report.txt` | mã lỗi máy kết luận được, 33 mẫu |

In lại báo cáo mà không gọi LLM:

```bash
.venv/Scripts/python.exe scripts/eval_stability.py --ket-qua e1_stability_rubric_v2.json --bao-cao
```

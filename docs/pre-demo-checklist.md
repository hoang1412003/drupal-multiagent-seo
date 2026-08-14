# Việc phải làm trước khi demo / bàn giao

**Cập nhật:** 2026-08-07

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

Từ 2026-08-05 KB nằm trong **Postgres + pgvector** (container riêng của phía
Multi-Agent), không còn là thư mục Chroma. KB vẫn là **dữ liệu dẫn xuất**,
dựng lại được từ `specs.json` và `docs/brand/corpus/` — nên nó không nằm trong
git, đúng như trước.

**Hệ quả: máy mới clone repo về sẽ KHÔNG có KB, và còn phải dựng DB trước.**

```bash
cd multiagent
docker compose up -d                              # dựng Postgres + pgvector
.venv/Scripts/python.exe src/kb/build_kb.py       # 4 chunk
.venv/Scripts/python.exe src/kb/build_brand_kb.py # 1128 chunk, mất vài phút
```

⚠️ Nếu máy đó **chưa tải BGE-M3** thì bước nạp KB cần mạng (~2GB, một lần).
Máy đã có cache rồi thì thêm `HF_HUB_OFFLINE=1` để khỏi phụ thuộc mạng —
đã gặp thật: HuggingFace ngắt kết nối giữa chừng làm script chết dù model có sẵn.

**Nếu quên** (dù là quên `docker compose up` hay quên nạp KB): hệ thống **không
sập** — `retrieve()` ném exception, CP3 và BV6 trả `NA` (không phải 0), pipeline
vẫn chạy với các tiêu chí còn lại. Đó là nhánh `try/except` trong
`_cp3_so_lieu()` và `_bv6_giong_van()`. Nhưng demo mà thiếu hai tiêu chí RAG thì
mất đúng phần đáng khoe nhất — và nó **hỏng lặng lẽ**, không có thông báo nào.

**Kiểm nhanh, theo đúng thứ tự:**

```bash
cd multiagent
docker compose ps                                   # container `vf-agent-db` phải chạy
.venv/Scripts/python.exe scripts/eval_retrieval.py  # phải ra recall@3 = 1.00
```

---

## 2b. Khởi động service và worker trước khi demo

Từ 2026-08-07, chấm điểm không còn chạy tay bằng script — Drupal tự gửi job qua service HTTP, worker tiêu thụ hàng đợi. **Thiếu bước này thì Save một bài sẽ không có gì xảy ra**, kể cả khi KB và Postgres đã dựng đúng ở mục 2.

```bash
cd multiagent
docker compose ps                                       # vf-agent-db phải Up
.venv/Scripts/python.exe -m uvicorn api:app --port 8900 --app-dir src   # cửa sổ 1
.venv/Scripts/python.exe src/worker.py                                  # cửa sổ 2
```

**Kiểm:**

```bash
curl http://127.0.0.1:8900/health
```

Kỳ vọng `{"ok": true, "queued": ..., "running": ..., "failed": ...}`. Không kết nối được (`curl: (7) Failed to connect`) nghĩa là service chưa chạy — đúng lỗi thật đã gặp khi tắt service giữa chừng lúc kiểm E2E (`docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 2).

⚠️ **`VF_SERVICE_TOKEN` phải khớp giữa hai nơi**: `.env` (phía Python, biến `VF_SERVICE_TOKEN`) và `settings.php` (phía Drupal, khoá `$settings['vf_ai_service_token']`). Hai nơi lệch nhau thì **mọi request POST từ `vf_ai_trigger` sang service đều trả 401**, và Drupal **không hiện lỗi nào cho editor** — bài vẫn được Save bình thường, chỉ là job không được tạo qua đường event. Vì vòng đối soát vẫn chạy song song (`architecture.md` mục 9.2), bài rốt cuộc vẫn được chấm trong vài phút, nên triệu chứng "token lệch" rất dễ bị hiểu nhầm thành "hệ thống chạy đúng, chỉ chậm hơn bình thường". Kiểm khi nghi ngờ: xem log Drupal (`ddev drush watchdog:show`) tìm dòng `401` từ `vf_ai_trigger`, hoặc so trực tiếp giá trị hai bên.

Thiết kế đầy đủ: `docs/superpowers/specs/2026-08-07-needs-review-automation-design.md`.

### 2c. Từ 2026-08-14: credential theo site và tài khoản machine (P4)

Drupal nay gửi job sang `/api/v1/jobs` bằng **credential riêng theo site**, không còn dùng chung một token toàn cục ở tầng ứng dụng. Trên máy mới, sau khi `migrate.py apply`, phải chạy thêm:

```powershell
Set-Location D:\drupal-multiagent-seo\multiagent
.\.venv\Scripts\python.exe scripts\site_config.py set-from-env --site drupal-vn-primary --base-url-env DRUPAL_BASE_URL --secret-ref DRUPAL
.\.venv\Scripts\python.exe scripts\site_credential.py import-env --site drupal-vn-primary --env VF_SERVICE_TOKEN
```

**Thiếu bước này thì mọi POST sang `/api/v1/jobs` trả 401** — và giống hệt cái bẫy token lệch ở trên, editor không thấy lỗi nào; bài chỉ được chấm chậm qua vòng đối soát. Kiểm nhanh: `site_credential.py list --site drupal-vn-primary` phải in ra một dòng `active`.

Phía Drupal cần role machine và một tài khoản riêng cho nó:

```powershell
Set-Location D:\drupal-multiagent-seo\drupal
ddev drush php:script scripts/configure_ai_service_role.php               # xem trước
ddev drush php:script scripts/configure_ai_service_role.php -- --apply
ddev drush php:script scripts/test_ai_service_role.php
```

⚠️ **`DRUPAL_USER` không được là `admin` (UID 1).** UID 1 bỏ qua mọi kiểm tra quyền, nên trang `/admin/connection` sẽ báo "kết nối đạt" kể cả khi role sai hoàn toàn — đúng loại xanh giả mà nút đó sinh ra để chống. Tạo một user riêng, gán **chỉ** role `ai_service`, rồi trỏ `DRUPAL_USER`/`DRUPAL_PASSWORD` sang tài khoản đó.

Platform Admin ở `http://127.0.0.1:8900/admin`, trang **Kết nối** có nút kiểm tra. Kiểm chứng và giới hạn đã biết: [`docs/evidence/platform-api-cutover-verification.txt`](evidence/platform-api-cutover-verification.txt).

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

37/37 file test tính đến lần chạy thật 2026-08-07/08 (35 file Python +
`test_ai_report_renderer.php` + `test_vf_ai_trigger.php`, xem
`docs/evidence/tu_dong_hoa_e2e.txt` tiêu chí 8). Phần lớn test không cần API
key, không cần Drupal, không cần KB — chạy được ở bất cứ đâu, mất vài giây.

⚠️ **Từ 2026-08-07, bốn bộ test (`test_job_queue`, `test_audit`, `test_worker`,
`test_api`) cần container Postgres đang chạy.** Không có nó chúng in `[SKIP]`
và thoát 0 — **`[SKIP]` không phải `[PASS]`**. Trước khi báo cáo số test xanh,
chạy `docker compose ps` xác nhận `vf-agent-db` đang chạy.

Riêng test hợp đồng phía PHP chạy trong container:

```bash
cd drupal
ddev exec php scripts/test_ai_report_renderer.php
ddev exec php scripts/test_vf_ai_trigger.php
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

⚠️ **Ngoại lệ từ 2026-08-05 — phần Brand Voice của ba file E1 đo trên code cũ.**
Nợ B7 (BV6 siết kiểm trích dẫn nguyên văn) **đổi cách chấm Brand Voice**, nên σ
Brand và điểm Brand trong các file trên không còn là số của hệ thống đang chạy.
Khi demo: hoặc chạy lại E1 rồi dùng số mới, hoặc nói rõ "số này đo trước khi
siết BV6". Ba agent còn lại không bị ảnh hưởng. Chi tiết: `technical-debt.md`
mục B7.

In lại báo cáo mà không gọi LLM:

```bash
.venv/Scripts/python.exe scripts/eval_stability.py --ket-qua e1_stability_rubric_v2.json --bao-cao
```

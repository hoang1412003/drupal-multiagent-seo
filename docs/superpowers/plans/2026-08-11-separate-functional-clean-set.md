# Separate Functional-Clean Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tách 10 mẫu corrected khỏi gold set 33 mẫu, khóa E5/extractor/E1 chống trộn hoặc ghi đè dữ liệu, và đồng bộ tài liệu Sprint 2–3.

**Architecture:** Gold calibration và functional-clean được tách bằng cả thư mục lẫn manifest. E5 lấy danh sách đầu vào từ `labels.csv` theo allowlist split; extractor dùng write guard có `--force`; E1 gắn `prompt_version` vào file resume. Ba chốt độc lập để một sai sót thao tác không làm hỏng dữ liệu hoặc phép đo.

**Tech Stack:** Python 3, CSV/JSON chuẩn, BeautifulSoup extractor hiện có, PowerShell cho thao tác file trên Windows, bộ test script tự chạy của repo.

## Global Constraints

- Gold set calibration giữ đúng 33 mẫu: 20 `gold-real`, 13 `gold-pert`.
- Functional-clean giữ đúng 10 mẫu C và tất cả có `expected_label=publish`.
- Không thay đổi nội dung byte của 10 TXT/HTML C trong lúc di chuyển.
- Không thay đổi 13 mẫu P, rubric, prompt, trọng số hoặc ngưỡng.
- Không chạy E1/E5 có phí trong kế hoạch này.
- Mọi production-code change phải theo RED → GREEN.
- Chỉ stage đúng file của từng task; giữ nguyên thay đổi không liên quan trong working tree.

---

### Task 1: Tách vật lý bộ functional-clean và khóa cấu trúc dữ liệu

**Files:**
- Create: `multiagent/scripts/test_evaluation_datasets.py`
- Create: `docs/functional-tests/clean_labels.csv`
- Move: `docs/goldset/corrections.md` → `docs/functional-tests/corrections.md`
- Move: `docs/goldset/raw/C-001.txt` … `C-010.txt` → `docs/functional-tests/clean/`
- Move: `docs/goldset/raw_html/C-001.html` … `C-010.html` → `docs/functional-tests/raw_html/`
- Modify: `docs/goldset/labels.csv`

**Interfaces:**
- Consumes: 10 dòng `C-*` hiện có trong `docs/goldset/labels.csv` và 20 file C hiện có.
- Produces: gold manifest 33 dòng; functional manifest schema `sample_id,source_url,variant,expected_label,annotator,date,guideline_version,notes`.

- [ ] **Step 1: Viết test cấu trúc dữ liệu đang mong muốn**

Tạo `test_evaluation_datasets.py` dùng `csv`, `glob`, `os`; test phải kiểm đúng các điều kiện sau:

```python
def test_gold_set_chi_co_33_mau_gp():
    rows = read_csv(GOLD_LABELS)
    check("gold có 33 mẫu", len(rows), 33)
    check("gold chỉ có G/P", all(r["sample_id"].startswith(("G-", "P-")) for r in rows), True)
    check("gold chỉ có hai split", {r["split"] for r in rows}, {"gold-real", "gold-pert"})

def test_functional_clean_co_10_mau_publish():
    rows = read_csv(CLEAN_LABELS)
    check("functional có 10 mẫu", len(rows), 10)
    check("mọi mẫu là corrected", {r["variant"] for r in rows}, {"corrected"})
    check("mọi nhãn kỳ vọng publish", {r["expected_label"] for r in rows}, {"publish"})

def test_c_duoc_tach_vat_ly_khoi_gold():
    check("gold raw không có C", glob.glob(os.path.join(GOLD_RAW, "C-*.txt")), [])
    check("gold html không có C", glob.glob(os.path.join(GOLD_HTML, "C-*.html")), [])
    check("functional clean đủ TXT", len(glob.glob(os.path.join(CLEAN_DIR, "C-*.txt"))), 10)
    check("functional clean đủ HTML", len(glob.glob(os.path.join(CLEAN_HTML, "C-*.html"))), 10)
```

Khối `__main__` phải gọi đủ ba test để `test_moi_test_deu_chay.py` kiểm được.

- [ ] **Step 2: Chạy test và xác nhận RED**

Run từ `multiagent/`:

```powershell
.\.venv\Scripts\python.exe scripts\test_evaluation_datasets.py
```

Expected: FAIL vì gold có 43 dòng, chưa có `docs/functional-tests/clean_labels.csv`, và C còn nằm dưới `docs/goldset`.

- [ ] **Step 3: Tạo manifest functional và di chuyển file an toàn**

Trước khi di chuyển, lấy SHA-256 của 20 file C. Tạo đúng ba thư mục `docs/functional-tests`, `clean`, `raw_html`; di chuyển bằng `Move-Item -LiteralPath` từng file trong PowerShell. Sau khi di chuyển, tính lại SHA-256 và assert từng hash theo basename không đổi.

`clean_labels.csv` lấy 10 trường tương ứng từ dòng C cũ, đổi schema thành:

```csv
sample_id,source_url,variant,expected_label,annotator,date,guideline_version,notes
C-001,/vn_vi/he-thong-phanh-tren-xe-o-to-dien,corrected,publish,A1,2026-08-11,v1.3,Bản functional-clean từ HTML nguồn C-001
```

Điền tương tự cho C-002…C-010 bằng đúng URL hiện có. Xóa 10 dòng C khỏi `docs/goldset/labels.csv`; không sửa 33 dòng G/P.

- [ ] **Step 4: Chạy test và xác nhận GREEN**

```powershell
.\.venv\Scripts\python.exe scripts\test_evaluation_datasets.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: cả hai exit 0; gold 33, functional 10, không còn C dưới gold.

- [ ] **Step 5: Commit task dữ liệu**

```powershell
git add -- docs/goldset/labels.csv docs/functional-tests multiagent/scripts/test_evaluation_datasets.py
git commit -m "data: tach functional clean khoi gold set"
```

---

### Task 2: E5 chỉ đọc hai split calibration

**Files:**
- Create: `multiagent/scripts/test_eval_calibration_dataset.py`
- Modify: `multiagent/scripts/eval_calibration.py`

**Interfaces:**
- Produces: `doc_nhan(labels_path: str = LABELS) -> dict[str, str]` chỉ trả nhãn của split hợp lệ.
- Produces: `gold_ids(labels_path: str = LABELS, gold_dir: str = GOLD_DIR) -> list[str]` trả ID đã sắp xếp và ném `FileNotFoundError` nếu thiếu TXT.
- Consumes: `gold_ids()` trong `cham_gold_set()`; `doc_nhan()` trong pha quét.

- [ ] **Step 1: Viết test E5 theo manifest**

Trong thư mục tạm, tạo CSV ba dòng `G-001/gold-real`, `P-001a/gold-pert`, `C-001/functional-clean`; tạo TXT chỉ cho G/P:

```python
def test_chi_lay_hai_split_gold():
    labels, raw = fixture_dataset()
    check("ID calibration", gold_ids(labels, raw), ["G-001", "P-001a"])
    check("nhãn calibration", doc_nhan(labels), {"G-001": "needs_revision", "P-001a": "rejected"})

def test_gold_id_thieu_file_phai_dung():
    labels, raw = fixture_dataset(bo_file="P-001a.txt")
    try:
        gold_ids(labels, raw)
    except FileNotFoundError as error:
        check("nêu đúng ID thiếu", "P-001a" in str(error), True)
    else:
        raise AssertionError("gold_ids phải dừng khi thiếu file")
```

- [ ] **Step 2: Chạy test và xác nhận RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
```

Expected: import hoặc call FAIL vì `gold_ids` chưa tồn tại và `doc_nhan` chưa nhận `labels_path`/lọc split.

- [ ] **Step 3: Implement allowlist tối thiểu**

Trong `eval_calibration.py`:

```python
GOLD_SPLITS = frozenset({"gold-real", "gold-pert"})

def _gold_rows(labels_path: str = LABELS) -> list[dict]:
    import csv
    with open(labels_path, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)
                if r.get("split") in GOLD_SPLITS and r.get("label", "").strip()]

def doc_nhan(labels_path: str = LABELS) -> dict[str, str]:
    return {r["sample_id"]: r["label"].strip() for r in _gold_rows(labels_path)}

def gold_ids(labels_path: str = LABELS, gold_dir: str = GOLD_DIR) -> list[str]:
    ids = sorted(r["sample_id"] for r in _gold_rows(labels_path))
    missing = [sid for sid in ids if not os.path.isfile(os.path.join(gold_dir, f"{sid}.txt"))]
    if missing:
        raise FileNotFoundError("Thieu file gold: " + ", ".join(missing))
    return ids
```

Thay phép `os.listdir(GOLD_DIR)` trong `cham_gold_set()` bằng `gold_ids()`.

- [ ] **Step 4: Chạy test GREEN và regression E5**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
.\.venv\Scripts\python.exe scripts\test_e5_khop_aggregator.py
.\.venv\Scripts\python.exe scripts\eval_calibration.py --bao-cao
```

Expected: exit 0; báo cáo offline vẫn dùng 33 nhãn và không gọi API.

- [ ] **Step 5: Commit chốt E5**

```powershell
git add -- multiagent/scripts/eval_calibration.py multiagent/scripts/test_eval_calibration_dataset.py
git commit -m "fix: gioi han E5 vao gold set 33 mau"
```

---

### Task 3: Extractor chống ghi đè bằng `--force`

**Files:**
- Modify: `multiagent/scripts/extract_gold_sample.py`
- Modify: `multiagent/scripts/test_extract_gold_sample.py`

**Interfaces:**
- Produces: `write_output(path: str, content: str, force: bool = False) -> None`.
- Changes: `process(path: str, table: dict, force: bool = False) -> bool`.
- CLI: `extract_gold_sample.py [--force] <html...>`.

- [ ] **Step 1: Viết hai test ghi đè**

```python
def test_write_output_tu_choi_ghi_de():
    path = temp_file("ban da hieu dinh")
    try:
        write_output(path, "noi dung boc lai")
    except FileExistsError:
        pass
    else:
        raise AssertionError("phải từ chối ghi đè mặc định")
    check("nội dung cũ còn nguyên", read(path), "ban da hieu dinh")

def test_write_output_force_ghi_de():
    path = temp_file("cu")
    write_output(path, "moi", force=True)
    check("force thay nội dung", read(path), "moi")
```

Thêm cả hai hàm vào khối `__main__` của file test.

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_extract_gold_sample.py
```

Expected: FAIL vì `write_output` chưa tồn tại.

- [ ] **Step 3: Implement write guard và argparse**

```python
def write_output(path: str, content: str, force: bool = False) -> None:
    if os.path.exists(path) and not force:
        raise FileExistsError(
            f"Tu choi ghi de {path}; dung --force neu chu dong tao lai")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
```

`process()` gọi `write_output(...)`; bắt riêng `FileExistsError`, in `[TU CHOI GHI DE]` rồi trả `False`. Dùng `argparse` với `parser.add_argument("--force", action="store_true")` và positional `paths` có `nargs="+"`; truyền `force=args.force` vào từng `process()`.

- [ ] **Step 4: Chạy GREEN và kiểm tra CLI không ghi đè**

```powershell
.\.venv\Scripts\python.exe scripts\test_extract_gold_sample.py
.\.venv\Scripts\python.exe scripts\extract_gold_sample.py ..\docs\goldset\raw_html\P-001a.html
```

Expected: test exit 0; lệnh CLI exit 1 với `[TU CHOI GHI DE]`; hash `docs/goldset/raw/P-001a.txt` không đổi.

- [ ] **Step 5: Commit chốt extractor**

```powershell
git add -- multiagent/scripts/extract_gold_sample.py multiagent/scripts/test_extract_gold_sample.py
git commit -m "fix: chan extractor ghi de mau da chinh"
```

---

### Task 4: E1 từ chối resume khác `prompt_version`

**Files:**
- Create: `multiagent/scripts/test_eval_stability_resume.py`
- Modify: `multiagent/scripts/eval_stability.py`

**Interfaces:**
- Consumes: `eval_calibration.prompt_version() -> str` làm nguồn phiên bản duy nhất.
- Changes: `nap_ket_qua(path: str | None = None) -> dict` xác thực metadata.
- Changes: `ghi_ket_qua(data: dict, path: str | None = None) -> None` luôn ghi `_meta.prompt_version`.

- [ ] **Step 1: Viết test resume ba trường hợp**

```python
def test_file_moi_tra_dict_rong():
    check("file chưa có", nap_ket_qua(path_chua_ton_tai()), {})

def test_file_cu_thieu_meta_bi_tu_choi():
    path = write_json({"G-001": []})
    assert_system_exit_contains(lambda: nap_ket_qua(path), "--ket-qua")

def test_file_sai_prompt_bi_tu_choi():
    path = write_json({"_meta": {"prompt_version": "sai"}, "G-001": []})
    assert_system_exit_contains(lambda: nap_ket_qua(path), "Tron hai ban")

def test_file_dung_prompt_duoc_resume():
    path = write_json({"_meta": {"prompt_version": prompt_version()}, "G-001": []})
    check("bỏ metadata khi trả dữ liệu", nap_ket_qua(path), {"G-001": []})
```

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_stability_resume.py
```

Expected: FAIL vì chữ ký hiện tại không nhận path và không kiểm metadata.

- [ ] **Step 3: Implement metadata dùng chung**

Import `prompt_version` từ `eval_calibration`. `nap_ket_qua()` đọc path truyền vào hoặc `KET_QUA`, pop `_meta`, và ném `SystemExit` nếu version thiếu/khác. `ghi_ket_qua()` ghi:

```python
payload = {"_meta": {"prompt_version": prompt_version()}, **data}
json.dump(payload, f, ensure_ascii=False, indent=2)
```

Chế độ `--bao-cao` tiếp tục gọi `nap_ket_qua()` nên cũng từ chối báo cáo trộn phiên bản.

- [ ] **Step 4: Chạy GREEN**

```powershell
.\.venv\Scripts\python.exe scripts\test_eval_stability_resume.py
.\.venv\Scripts\python.exe scripts\eval_stability.py --bao-cao --ket-qua e1_stability_raw.json
```

Expected: test exit 0; lệnh báo cáo file cũ dừng trước API với thông báo phải dùng file mới. Không chạy E1 thật.

- [ ] **Step 5: Commit chốt E1**

```powershell
git add -- multiagent/scripts/eval_stability.py multiagent/scripts/test_eval_stability_resume.py
git commit -m "fix: chan E1 resume khac prompt version"
```

---

### Task 5: Đồng bộ tài liệu và xác minh toàn bộ

**Files:**
- Modify: `README.md`
- Modify: `docs/goldset/sources.md`
- Modify: `docs/goldset/annotation-guideline.md`
- Modify: `docs/functional-tests/corrections.md`
- Modify: `docs/technical-debt.md`
- Modify: `docs/sprint2-report.md`
- Modify: `docs/evaluation-plan.md`

**Interfaces:**
- Consumes: cấu trúc dữ liệu và chốt code từ Task 1–4.
- Produces: một cách gọi thống nhất: “33 gold calibration + 10 functional-clean = evaluation suite 43 mẫu”.

- [ ] **Step 1: Cập nhật nội dung theo một nguồn sự thật**

Áp dụng đúng các câu sau ở mọi tài liệu liên quan:

```text
Gold set calibration: 33 mẫu (20 original + 13 perturbed), không có lớp publish.
Functional-clean: 10 mẫu corrected, expected publish, không tham gia E5/Kappa.
Evaluation suite: 43 mẫu, chỉ số phải báo cáo riêng theo lát dữ liệu.
```

Trong `README.md`, đổi checkbox gold set thành `[x]` và ghi `33/33`. Trong `technical-debt.md` mục 8.6, đổi “chưa làm” thành “đã dựng 10 mẫu, chưa chạy pipeline”; bổ sung cảnh báo extractor/E5 đã có test chặn. Trong `sprint2-report.md`, thêm hậu kiểm sau mục gold set thay vì sửa số lịch sử. Trong `evaluation-plan.md`, ghi E5 chỉ đọc hai split và functional-clean báo cáo `publish_rate`, `false_positive_articles`, `false_positive_issues` riêng.

- [ ] **Step 2: Chạy kiểm tra tính nhất quán dữ liệu/tài liệu**

```powershell
rg -n "gold-corrected|gold set.*43|43 mẫu.*gold|đang gán nhãn" README.md docs
.\.venv\Scripts\python.exe scripts\test_evaluation_datasets.py
```

Expected: `rg` không còn mô tả C là `gold-corrected` hoặc gold set 43; test dữ liệu exit 0. Những lần xuất hiện “43 mẫu” còn lại phải nói rõ `evaluation suite`.

- [ ] **Step 3: Chạy toàn bộ 40 test script**

Từ `multiagent/`, dùng vòng PowerShell hiện có để chạy mọi `scripts/test_*.py`, giữ output PASS/FAIL từng file.

Expected: tổng số test file là 40 (37 cũ + 3 mới), passed=40, failed=0. Test Postgres được phép tự `[SKIP]` theo quy ước hiện có nhưng file phải exit 0.

- [ ] **Step 4: Kiểm tra diff và trạng thái cuối**

```powershell
git diff --check
git status --short
```

Kiểm tra thủ công: không có thay đổi nội dung P; 10 cặp hash C trước/sau di chuyển giống nhau; không có file C dưới gold; không có file ngoài phạm vi bị stage.

- [ ] **Step 5: Commit tài liệu**

```powershell
git add -- README.md docs/goldset/sources.md docs/goldset/annotation-guideline.md docs/functional-tests/corrections.md docs/technical-debt.md docs/sprint2-report.md docs/evaluation-plan.md
git commit -m "docs: dong bo gold va functional evaluation suite"
```

- [ ] **Step 6: Bàn giao trước phép đo có phí**

Báo cáo 40/40 test, cấu trúc 33+10 và danh sách commit. Yêu cầu người dùng xác nhận riêng trước khi chạy E1 mới vào `e1_sau_b14.json` vì phép đo dự kiến tiêu khoảng 3 USD.

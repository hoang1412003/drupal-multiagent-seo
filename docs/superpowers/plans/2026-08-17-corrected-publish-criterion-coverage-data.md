# Corrected Publish & Criterion Coverage Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo, kiểm tra và commit bất biến 20 bản `GC` expected-publish cùng 11 bản `CV` một lỗi, hoàn toàn offline và có provenance/checksum đầy đủ.

**Architecture:** Một loader/validator thuần Python sở hữu schema, path containment, parent mapping và SHA-256. Nội dung được tạo theo batch nhỏ từ parent bất biến, rà bằng helper tất định cộng kiểm ngữ nghĩa v1.4, rồi manifest mới được khóa. Test thật xác nhận inventory cuối nhưng E5 v1 vẫn chỉ đọc `G/P`.

**Tech Stack:** Python 3.12 standard library, CSV, SHA-256, script test standalone, PowerShell, Git.

## Global Constraints

- Áp dụng toàn bộ Global Constraints của parent plan `2026-08-17-corrected-publish-criterion-coverage.md`.
- Pha này có chi phí API bằng 0; không import graph/agent/model trong validator.
- Không tự đổi facts hiện hành. A3/A6/chính sách phải đối chiếu nguồn chính thức tại ngày sửa; ghi URL và ngày truy cập.
- Không dùng `quet_ung_vien.py` làm bộ kết luận; nó chỉ đánh dấu chỗ cần AI/người đọc xác nhận.
- `label_helper.py` chỉ kết luận các mã tất định mà code hỗ trợ; A1–A7/B8/B11 vẫn cần đọc toàn bài.
- Mọi commit chỉ stage đúng file liệt kê trong task.

---

### Task 1: Khóa baseline nhãn AI v1.4 và provenance

**Files:**
- Modify: `docs/goldset/annotation-guideline.md`
- Create: `docs/goldset/labels-ai-v1.4.csv`
- Create: `docs/evidence/goldset-ai-relabel-v1.4.md`
- Create: `multiagent/scripts/test_goldset_ai_v14.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- Consumes: 33 file `docs/goldset/raw/G-*.txt|P-*.txt` và labels v1.3 chỉ để đối chiếu sau khóa.
- Produces: manifest candidate 33 dòng có đủ các cột `sample_id,source_url,split,variant,injected_codes,defect_codes,label,annotator,date,guideline_version,notes,provenance`, counts 23/10/0 và provenance `AI-annotated-partially-exposed`.

- [ ] **Step 1: Viết test artifact contract**

Tạo test standalone với các assertion cụ thể:

```python
rows = list(csv.DictReader(open(LABELS_AI, encoding="utf-8")))
check("33 rows", len(rows), 33)
check("20 G", sum(r["sample_id"].startswith("G-") for r in rows), 20)
check("13 P", sum(r["sample_id"].startswith("P-") for r in rows), 13)
check("label counts", Counter(r["label"] for r in rows),
      Counter({"needs_revision": 23, "rejected": 10}))
check("candidate provenance",
      {r["provenance"] for r in rows}, {"AI-annotated-partially-exposed"})
check("guideline v1.4", {r["guideline_version"] for r in rows}, {"v1.4"})
check("gold v1 unchanged", sha256(GOLD_V1),
      "ac74ee3e3f11103f8afb0223685aa3e4004dae7e8eaf3b9cd6f716bb58dfcb17")
```

SHA-256 literal trên được tính từ `docs/goldset/labels.csv` tại committed parent `b0fa1c8`; test không tính expected từ chính file runtime.

- [ ] **Step 2: Chạy test và phân loại kết quả**

Run:

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
.\.venv\Scripts\python.exe scripts\test_goldset_ai_v14.py
```

Expected: PASS toàn bộ contract. Nếu count/hash/provenance lệch, dừng và sửa artifact/evidence; không thay expected để khớp dữ liệu ngoài thiết kế.

- [ ] **Step 3: Kiểm tra guideline/evidence bằng máy**

Run:

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel
rg -n "A7|B11|trên 75|trên \*\*500 tiếng\*\*|partially exposed|23|10" docs/goldset/annotation-guideline.md docs/evidence/goldset-ai-relabel-v1.4.md
git diff --check -- docs/goldset/annotation-guideline.md docs/goldset/labels-ai-v1.4.csv docs/evidence/goldset-ai-relabel-v1.4.md multiagent/scripts/test_goldset_ai_v14.py multiagent/scripts/test_groups.json
```

Expected: tìm thấy contract v1.4/provenance; `git diff --check` không output.

- [ ] **Step 4: Commit baseline riêng**

```powershell
git add -- docs/goldset/annotation-guideline.md docs/goldset/labels-ai-v1.4.csv docs/evidence/goldset-ai-relabel-v1.4.md multiagent/scripts/test_goldset_ai_v14.py multiagent/scripts/test_groups.json
git commit -m "data: record AI v1.4 candidate labels"
```

---

### Task 2: Xây loader và integrity validator bằng TDD

**Files:**
- Create: `multiagent/scripts/functional_dataset_v2.py`
- Create: `multiagent/scripts/test_functional_dataset_v2.py`
- Modify: `multiagent/scripts/test_groups.json`

**Interfaces:**
- `sha256_file(path: Path) -> str`
- `load_manifest(path: Path, content_dir: Path, expected_variant: str) -> list[FunctionalSample]`
- `validate_inventory(repo_root: Path) -> DatasetInventory`
- CLI `validate-manifest`, `validate-inventory`, `sha256` chỉ đọc file và không gọi model.

- [ ] **Step 1: Viết RED tests cho schema/path/hash/parent**

Test dùng `tempfile.TemporaryDirectory()` và phải phủ mười case độc lập:

- duplicate `sample_id` bị từ chối;
- thiếu hoặc thừa header bị từ chối;
- path escape và content file thiếu bị từ chối;
- SHA-256 content sai bị từ chối;
- corrected không `publish` hoặc có `injected_codes` bị từ chối;
- coverage không có đúng một target trùng injected code bị từ chối;
- target A không `rejected` hoặc target B không `needs_revision` bị từ chối;
- parent SHA-256 không khớp parent hiện hữu bị từ chối;
- inventory thiếu/thừa ID so với exact 20 GC + 11 CV bị từ chối;
- ID/path giữa gold, clean, corrected và coverage giao nhau bị từ chối.

Manifest schema literal trong test:

```python
SCHEMA = [
    "sample_id", "parent_sample_id", "source_url", "variant",
    "expected_label", "target_code", "removed_codes", "injected_codes",
    "annotator", "generator_model", "guideline_version", "created_at",
    "parent_sha256", "content_sha256", "notes",
]
```

- [ ] **Step 2: Chạy RED**

```powershell
.\.venv\Scripts\python.exe scripts\test_functional_dataset_v2.py
```

Expected: FAIL vì `functional_dataset_v2` chưa tồn tại.

- [ ] **Step 3: Viết implementation tối thiểu**

Module dùng dataclass bất biến và lỗi riêng:

```python
@dataclass(frozen=True)
class FunctionalSample:
    sample_id: str
    parent_sample_id: str
    source_url: str
    variant: str
    expected_label: str
    target_code: str
    removed_codes: Sequence[str]
    injected_codes: Sequence[str]
    annotator: str
    generator_model: str
    guideline_version: str
    created_at: str
    parent_sha256: str
    content_sha256: str
    notes: str
    content_path: Path


class DatasetValidationError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetInventory:
    corrected: Sequence[FunctionalSample]
    coverage: Sequence[FunctionalSample]

    @property
    def corrected_ids(self) -> set[str]:
        return {sample.sample_id for sample in self.corrected}

    @property
    def coverage_ids(self) -> set[str]:
        return {sample.sample_id for sample in self.coverage}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
```

Path validation phải dùng `Path.resolve()` + `relative_to(allowed_root.resolve())`; không kiểm bằng prefix string. `validate_inventory()` yêu cầu exact ID sets `GC-001..GC-020` và bảng CV đã khóa trong spec, đồng thời xác nhận mọi parent/hash/source URL.

- [ ] **Step 4: Thêm CLI read-only**

CLI contract:

```powershell
.\.venv\Scripts\python.exe scripts\functional_dataset_v2.py sha256 ..\docs\goldset\raw\G-001.txt
.\.venv\Scripts\python.exe scripts\functional_dataset_v2.py validate-manifest --manifest ..\docs\functional-tests\gold-corrected-labels.csv --content-dir ..\docs\functional-tests\gold-corrected --variant corrected
.\.venv\Scripts\python.exe scripts\functional_dataset_v2.py validate-inventory
```

`validate-manifest` chấp nhận manifest partial trong lúc tạo batch nhưng vẫn kiểm mọi row hiện có. `validate-inventory` mới yêu cầu exact 20/11 và fail cho tới Task 9 hoàn tất.

- [ ] **Step 5: Chạy GREEN và meta-test**

```powershell
.\.venv\Scripts\python.exe scripts\test_functional_dataset_v2.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: PASS; test mới thuộc đúng nhóm `pure`.

- [ ] **Step 6: Commit validator**

```powershell
git add -- multiagent/scripts/functional_dataset_v2.py multiagent/scripts/test_functional_dataset_v2.py multiagent/scripts/test_groups.json
git commit -m "test: validate corrected and coverage datasets"
```

---

### Task 3: Tạo batch GC-001 đến GC-005

**Files:**
- Create: `docs/functional-tests/gold-corrected/GC-001.txt`
- Create: `docs/functional-tests/gold-corrected/GC-002.txt`
- Create: `docs/functional-tests/gold-corrected/GC-003.txt`
- Create: `docs/functional-tests/gold-corrected/GC-004.txt`
- Create: `docs/functional-tests/gold-corrected/GC-005.txt`
- Create: `docs/functional-tests/gold-corrected-labels.csv`
- Create: `docs/functional-tests/corrections-v1.4.md`

**Interfaces:** Produces corrected rows with parent `G-001..G-005`, expected `publish`, no `target_code/injected_codes`.

Expected removed codes:

```text
GC-001 <- G-001: B3;B8
GC-002 <- G-002: B8
GC-003 <- G-003: B8
GC-004 <- G-004: B3;B8
GC-005 <- G-005: B1;B2;B8;B10
```

- [ ] **Step 1:** Dùng `apply_patch` tạo GC-001 từ đủ năm field G-001, sửa meta về 140–170 ký tự và lỗi B8; đọc lại A/B toàn bài.
- [ ] **Step 2:** Dùng `apply_patch` tạo GC-002, sửa toàn bộ B8 và giữ các claim NEDC đã có đúng ngữ cảnh.
- [ ] **Step 3:** Dùng `apply_patch` tạo GC-003, sửa toàn bộ B8 trong hướng dẫn khởi động, không làm thay đổi thứ tự thao tác.
- [ ] **Step 4:** Dùng `apply_patch` tạo GC-004, sửa meta B3/B8 và giữ chủ đề đèn projector.
- [ ] **Step 5:** Dùng `apply_patch` tạo GC-005; bỏ hoặc chuẩn hóa claim B1/B2/B10 theo nguồn chính thức và sửa toàn bộ B8, không tự thêm số.
- [ ] **Step 6:** Ghi log trước--sau theo từng code, URL nguồn và ngày truy cập trong `corrections-v1.4.md`.
- [ ] **Step 7:** Chạy helper/candidate scan:

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
.\.venv\Scripts\python.exe scripts\label_helper.py ..\docs\functional-tests\gold-corrected\GC-001.txt ..\docs\functional-tests\gold-corrected\GC-002.txt ..\docs\functional-tests\gold-corrected\GC-003.txt ..\docs\functional-tests\gold-corrected\GC-004.txt ..\docs\functional-tests\gold-corrected\GC-005.txt
.\.venv\Scripts\python.exe scripts\quet_ung_vien.py ..\docs\functional-tests\gold-corrected\GC-001.txt ..\docs\functional-tests\gold-corrected\GC-002.txt ..\docs\functional-tests\gold-corrected\GC-003.txt ..\docs\functional-tests\gold-corrected\GC-004.txt ..\docs\functional-tests\gold-corrected\GC-005.txt
```

Expected: helper không chốt A/B; mọi candidate được đọc và bác/xử lý có ghi log. C4/C5 có thể tồn tại vì advisory.

- [ ] **Step 8:** Dùng CLI `sha256` lấy parent/content hashes, thêm năm row bằng `apply_patch`, rồi chạy `validate-manifest`.
- [ ] **Step 9:** Review diff chỉ batch này; xác nhận mọi row `annotator=AI-A1`, `guideline_version=v1.4`. `generator_model` dùng exact model ID do session metadata cung cấp; nếu nền tảng không công khai ID thì ghi literal `not-exposed-by-runtime`, không suy đoán tên model.
- [ ] **Step 10:** Commit:

```powershell
git add -- docs/functional-tests/gold-corrected/GC-001.txt docs/functional-tests/gold-corrected/GC-002.txt docs/functional-tests/gold-corrected/GC-003.txt docs/functional-tests/gold-corrected/GC-004.txt docs/functional-tests/gold-corrected/GC-005.txt docs/functional-tests/gold-corrected-labels.csv docs/functional-tests/corrections-v1.4.md
git commit -m "data: correct gold articles GC-001 through GC-005"
```

---

### Task 4: Tạo batch GC-006 đến GC-010

**Files:** Create `docs/functional-tests/gold-corrected/GC-006.txt` through `GC-010.txt`; modify corrected manifest/log.

**Interfaces:** Appends five corrected samples without altering Task 3 rows/hashes.

```text
GC-006 <- G-006: B1;B2;B10
GC-007 <- G-007: B1;B2;B8;B10;B11
GC-008 <- G-008: B8;B10
GC-009 <- G-009: B1;B2;B4;B8;B10;B11
GC-010 <- G-010: A1;B8
```

- [ ] **Step 1:** Tạo GC-006 bằng `apply_patch`; sửa B1/B2/B10 cho claim thời gian sạc theo nguồn chính thức.
- [ ] **Step 2:** Tạo GC-007; sửa B1/B2/B8/B10, rồi xử lý B11 bằng claim đủ thành phần hoặc bỏ claim cụ thể.
- [ ] **Step 3:** Tạo GC-008; sửa B8 và loại/nguồn hóa số liệu B10.
- [ ] **Step 4:** Tạo GC-009; sửa B1/B2/B4/B8/B10 và xử lý B11, giữ title trong ranh giới v1.4.
- [ ] **Step 5:** Tạo GC-010; loại A1 mà không thay bằng claim tuyệt đối khác và sửa toàn bộ B8.
- [ ] **Step 6:** Ghi nguồn/ngày/trước--sau cho exact five files, đặc biệt mọi claim sạc/pin/chính sách.
- [ ] **Step 7:** Chạy helper + candidate scan cho exact five files; expected không A/B sau review.
- [ ] **Step 8:** Thêm log/hashes/rows, chạy `validate-manifest`; xác nhận Task 3 hashes vẫn khớp.
- [ ] **Step 9:** Commit riêng:

```powershell
git add -- docs/functional-tests/gold-corrected/GC-006.txt docs/functional-tests/gold-corrected/GC-007.txt docs/functional-tests/gold-corrected/GC-008.txt docs/functional-tests/gold-corrected/GC-009.txt docs/functional-tests/gold-corrected/GC-010.txt docs/functional-tests/gold-corrected-labels.csv docs/functional-tests/corrections-v1.4.md
git commit -m "data: correct gold articles GC-006 through GC-010"
```

---

### Task 5: Tạo batch GC-011 đến GC-015

**Files:** Create `docs/functional-tests/gold-corrected/GC-011.txt` through `GC-015.txt`; modify corrected manifest/log.

**Interfaces:** Appends five corrected samples; GC-011 must remain over 500 tiếng with valid H2 because it is parent của CV-B9-01.

```text
GC-011 <- G-011: A1;B3;B8
GC-012 <- G-012: B8;B10;B11
GC-013 <- G-013: B1;B8;B10;B11
GC-014 <- G-014: B3;B8;B11
GC-015 <- G-015: B8;B10;B11
```

- [ ] **Step 1:** Tạo GC-011; loại A1, sửa meta B3/B8, giữ trên 500 tiếng và ít nhất một H2 để làm parent B9.
- [ ] **Step 2:** Tạo GC-012; sửa B8/B10 và xử lý B11 bằng nguồn hoặc bỏ claim cụ thể.
- [ ] **Step 3:** Tạo GC-013; sửa B1/B8/B10/B11, không copy policy từ bài khác nếu phạm vi áp dụng khác.
- [ ] **Step 4:** Tạo GC-014; sửa meta B3/B8 và B11, giữ mục đích trả lời chi phí hàng tháng.
- [ ] **Step 5:** Tạo GC-015; sửa B8/B10/B11 và giữ bài trả lời đúng câu hỏi ở title.
- [ ] **Step 6:** Ghi source/date/trước--sau; ghi số tiếng/H2 GC-011 vào log.
- [ ] **Step 7:** Chạy helper + candidate scan; đọc A5/A6/A7/B8/B11 toàn batch.
- [ ] **Step 8:** Thêm hashes/rows/log, validate manifest và commit:

```powershell
git add -- docs/functional-tests/gold-corrected/GC-011.txt docs/functional-tests/gold-corrected/GC-012.txt docs/functional-tests/gold-corrected/GC-013.txt docs/functional-tests/gold-corrected/GC-014.txt docs/functional-tests/gold-corrected/GC-015.txt docs/functional-tests/gold-corrected-labels.csv docs/functional-tests/corrections-v1.4.md
git commit -m "data: correct gold articles GC-011 through GC-015"
```

---

### Task 6: Tạo batch GC-016 đến GC-020

**Files:** Create `docs/functional-tests/gold-corrected/GC-016.txt` through `GC-020.txt`; modify corrected manifest/log.

**Interfaces:** Completes exact GC ID set; GC-016 remains over 500 tiếng with H2; GC-018/GC-019 remain clean parents for coverage.

```text
GC-016 <- G-016: B8;B10
GC-017 <- G-017: B1;B3;B4;B8
GC-018 <- G-018: B3
GC-019 <- G-019: B8
GC-020 <- G-020: A1
```

- [ ] **Step 1:** Tạo GC-016; sửa B8/B10, kiểm nguồn mọi số và giữ trên 500 tiếng + H2 cho parent B9.
- [ ] **Step 2:** Tạo GC-017; sửa B1/B3/B4/B8, giữ title/meta/url trong ranh giới v1.4.
- [ ] **Step 3:** Tạo GC-018; sửa B3 và rà sạch để làm parent A5/B7.
- [ ] **Step 4:** Tạo GC-019; sửa B8 và rà sạch để làm parent A7.
- [ ] **Step 5:** Tạo GC-020; loại A1 mà không thay bằng claim tuyệt đối khác.
- [ ] **Step 6:** Ghi source/date/trước--sau và số tiếng/H2 GC-016 vào log.
- [ ] **Step 7:** Chạy helper + candidate scan + đọc semantic full batch.
- [ ] **Step 8:** Thêm hashes/rows/log; `validate-manifest` phải báo 20 valid rows.
- [ ] **Step 9:** Commit:

```powershell
git add -- docs/functional-tests/gold-corrected/GC-016.txt docs/functional-tests/gold-corrected/GC-017.txt docs/functional-tests/gold-corrected/GC-018.txt docs/functional-tests/gold-corrected/GC-019.txt docs/functional-tests/gold-corrected/GC-020.txt docs/functional-tests/gold-corrected-labels.csv docs/functional-tests/corrections-v1.4.md
git commit -m "data: complete twenty corrected gold articles"
```

---

### Task 7: Tạo coverage A3 và A5

**Files:**
- Create: `docs/functional-tests/criterion-coverage/CV-A3-01.txt`
- Create: `docs/functional-tests/criterion-coverage/CV-A5-01.txt`
- Create: `docs/functional-tests/criterion-coverage/CV-A5-02.txt`
- Create: `docs/functional-tests/criterion-coverage-labels.csv`
- Create: `docs/functional-tests/coverage-changes-v1.4.md`

**Interfaces:**
- `CV-A3-01 <- GC-006`, expected `rejected`, target A3.
- `CV-A5-01 <- GC-003`, expected `rejected`, target A5.
- `CV-A5-02 <- GC-018`, expected `rejected`, target A5.

- [ ] **Step 1:** Tạo CV-A3-01 từ GC-006: chọn một thông số sạc có value đúng không mâu thuẫn trong nguồn VinFast, ghi value đúng/source/date, rồi chèn một value sai rõ ràng. Câu sai vẫn nêu nguồn test để không tạo B10.
- [ ] **Step 2:** Tạo CV-A5-01 từ GC-003: thay trên 50% body bằng nội dung không trả lời title, giữ title/meta/url hợp lệ và ghi tỷ lệ thay đổi.
- [ ] **Step 3:** Tạo CV-A5-02 từ GC-018 theo một nội dung lạc đề khác, cũng đo trên 50% và không tạo B3/B4/B7/B8/B9.
- [ ] **Step 4:** Rà toàn bộ A/B từng fixture; đúng một target code.
- [ ] **Step 5:** Thêm `TEST FIXTURE — KHÔNG XUẤT BẢN` vào notes manifest/log, không chèn marker này vào body nếu nó tạo mã khác.
- [ ] **Step 6:** Hash parent/content, thêm rows, chạy `validate-manifest` và commit:

```powershell
git add -- docs/functional-tests/criterion-coverage/CV-A3-01.txt docs/functional-tests/criterion-coverage/CV-A5-01.txt docs/functional-tests/criterion-coverage/CV-A5-02.txt docs/functional-tests/criterion-coverage-labels.csv docs/functional-tests/coverage-changes-v1.4.md
git commit -m "data: add isolated A3 and A5 coverage fixtures"
```

---

### Task 8: Tạo coverage A6 và A7

**Files:** Create `CV-A6-01.txt`, `CV-A6-02.txt`, `CV-A7-01.txt`, `CV-A7-02.txt`; modify coverage manifest/log.

**Interfaces:**
- `CV-A6-01 <- GC-010`, expected `rejected`, target A6.
- `CV-A6-02 <- C-008`, expected `rejected`, target A6.
- `CV-A7-01 <- C-005`, expected `rejected`, target A7.
- `CV-A7-02 <- GC-019`, expected `rejected`, target A7.

- [ ] **Step 1:** Tạo CV-A6-01 từ GC-010 bằng một hướng dẫn sạc trái an toàn đã đối chiếu tài liệu chính thức; lưu câu đúng/source/date.
- [ ] **Step 2:** Tạo CV-A6-02 từ C-008 bằng một hướng dẫn bảo dưỡng trái an toàn khác; lưu căn cứ chính thức và không seed/run qua Drupal.
- [ ] **Step 3:** Tạo CV-A7-01 từ C-005 bằng shape ẩn thứ nhất; exact evaluator input vẫn thấy văn xuôi nhưng reader semantics ẩn nó.
- [ ] **Step 4:** Tạo CV-A7-02 từ GC-019 bằng shape ẩn thứ hai; không dùng CSS/tracking/URL/marker vô nghĩa làm target.
- [ ] **Step 5:** Rà full A/B từng fixture để bảo đảm đúng một target; parent hashes khớp.
- [ ] **Step 6:** Thêm rows/hashes/log, validate và commit:

```powershell
git add -- docs/functional-tests/criterion-coverage/CV-A6-01.txt docs/functional-tests/criterion-coverage/CV-A6-02.txt docs/functional-tests/criterion-coverage/CV-A7-01.txt docs/functional-tests/criterion-coverage/CV-A7-02.txt docs/functional-tests/criterion-coverage-labels.csv docs/functional-tests/coverage-changes-v1.4.md
git commit -m "data: add isolated A6 and A7 coverage fixtures"
```

---

### Task 9: Tạo coverage B6, B7, B9 và khóa inventory

**Files:**
- Create: `CV-B6-01.txt`, `CV-B7-01.txt`, `CV-B9-01.txt`, `CV-B9-02.txt`
- Modify: coverage manifest/log
- Modify: `multiagent/scripts/test_functional_dataset_v2.py`

**Interfaces:**
- `CV-B6-01 <- C-001`, expected `needs_revision`, target B6.
- `CV-B7-01 <- GC-018`, expected `needs_revision`, target B7.
- `CV-B9-01 <- GC-011`, expected `needs_revision`, target B9.
- `CV-B9-02 <- GC-016`, expected `needs_revision`, target B9.

- [ ] **Step 1:** B6 chỉ xóa/rỗng/sai mô tả một thuộc tính `alt` trong `body`; giữ ảnh khác và mọi field khác nguyên.
- [ ] **Step 2:** B7 chỉ đổi `url_alias` thành alias trên 75 ký tự nhưng vẫn không tạo lỗi chính tả/body/title/meta. Test đếm toàn chuỗi alias và assert `len(alias) > 75`.
- [ ] **Step 3:** Tạo CV-B9-01 từ GC-011: xóa toàn bộ H2, giữ `len(strip_html(body).split()) > 500`, không để H3 được tính thay H2 và không tạo B8.
- [ ] **Step 4:** Tạo CV-B9-02 từ GC-016 theo cùng contract nhưng nội dung cha khác; rà đúng một target B9.
- [ ] **Step 5:** Thêm exact inventory assertions:

```python
check("GC IDs", inventory.corrected_ids,
      {f"GC-{i:03d}" for i in range(1, 21)})
check("CV IDs", inventory.coverage_ids, {
    "CV-A3-01", "CV-A5-01", "CV-A5-02", "CV-A6-01", "CV-A6-02",
    "CV-A7-01", "CV-A7-02", "CV-B6-01", "CV-B7-01",
    "CV-B9-01", "CV-B9-02",
})
check("coverage labels", Counter(s.expected_label for s in inventory.coverage),
      Counter({"rejected": 7, "needs_revision": 4}))
```

- [ ] **Step 6:** Chạy:

```powershell
.\.venv\Scripts\python.exe scripts\functional_dataset_v2.py validate-inventory
.\.venv\Scripts\python.exe scripts\test_functional_dataset_v2.py
.\.venv\Scripts\python.exe scripts\test_evaluation_datasets.py
.\.venv\Scripts\python.exe scripts\test_eval_calibration_dataset.py
```

Expected: 20 GC + 11 CV valid; E5 vẫn chỉ G/P; clean C vẫn đúng 10.

- [ ] **Step 7:** Commit:

```powershell
git add -- docs/functional-tests/criterion-coverage/CV-B6-01.txt docs/functional-tests/criterion-coverage/CV-B7-01.txt docs/functional-tests/criterion-coverage/CV-B9-01.txt docs/functional-tests/criterion-coverage/CV-B9-02.txt docs/functional-tests/criterion-coverage-labels.csv docs/functional-tests/coverage-changes-v1.4.md multiagent/scripts/test_functional_dataset_v2.py
git commit -m "data: complete isolated criterion coverage set"
```

---

### Task 10: Rà 10 C theo v1.4 và tạo integrity evidence

**Files:**
- Create: `docs/evidence/functional-clean-ai-review-v1.4.csv`
- Create: `docs/evidence/functional-clean-ai-review-v1.4.md`
- Create: `docs/evidence/corrected-publish-coverage-v1-integrity.md`
- Modify: `multiagent/scripts/test_evaluation_datasets.py`

**Interfaces:** Produces exact expected-publish set C 10 + GC 20 and immutable integrity evidence consumed by Evaluation Plan.

- [ ] **Step 1:** Rà C-001..C-005 bằng helper/candidate scan + đọc A5/A6/A7/B8/B11; ghi kết luận từng ID.
- [ ] **Step 2:** Rà C-006..C-010 cùng contract. Nếu bất kỳ C còn A/B v1.4, không đổi expected label im lặng: dừng task, ghi finding và yêu cầu versioned correction design.
- [ ] **Step 3:** Nếu 10/10 sạch, dùng `apply_patch` tạo evidence review mới có `sample_id,expected_label,annotator,generator_model,guideline_version,reviewed_at,content_sha256,notes`. Giữ nguyên `clean_labels.csv` v1.3, annotator A1, `corrections.md` và 10 content file để không viết lại provenance lịch sử.
- [ ] **Step 4:** Mở rộng dataset test để assert physical separation, exact IDs, 30 expected-publish và gold raw/hash bất biến. Không đổi test hiện có khóa C-001..010.
- [ ] **Step 5:** Sinh evidence từ output validator/test thực tế; ghi commit base, hashes, counts, code coverage, source-check dates và limitation synthetic/partially exposed. Không chép chữ `PASS` nếu lệnh chưa có summary.
- [ ] **Step 6:** Chạy full offline:

```powershell
Set-Location D:\drupal-multiagent-seo\.worktrees\ai-v14-relabel\multiagent
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '0'
.\.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```

Expected: manifest-discovered total, 0 fail, 0 skip. Nếu timeout không có `TOM TAT`, trạng thái là chưa xác minh; không báo pass.

- [ ] **Step 7:** Commit integrity checkpoint:

```powershell
git add -- docs/evidence/functional-clean-ai-review-v1.4.csv docs/evidence/functional-clean-ai-review-v1.4.md docs/evidence/corrected-publish-coverage-v1-integrity.md multiagent/scripts/test_evaluation_datasets.py
git commit -m "test: verify corrected publish dataset integrity"
```

---

### Task 11: Data Plan Review Gate

**Files:** Read-only review of every file created/modified in Tasks 1–10.

**Interfaces:** Produces a clean committed Data HEAD; no runtime output.

- [ ] **Step 1:** Run `git status --short`; only known unrelated work may remain, no unstaged Data file.
- [ ] **Step 2:** Run `git diff --check HEAD~1..HEAD` and validator/tests again.
- [ ] **Step 3:** Verify no `GC/CV` ID appears in `docs/goldset/labels.csv` or `docs/goldset/raw`.
- [ ] **Step 4:** Verify all manifest SHA-256 values against disk and all parent hashes against their exact source.
- [ ] **Step 5:** Review evidence wording: no “human agreement”, “natural publish”, “calibrated threshold” or “63 independent samples”.
- [ ] **Step 6:** Record exact Data HEAD in Evaluation protocol; then and only then move to Evaluation Plan.

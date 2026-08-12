# CP4 Deterministic Deadline Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tách phép kiểm thời hạn của CP4 sang code tất định để G-008/P-006a không còn bị veto oan, trong khi khuyến mại thiếu thời hạn hoặc thiếu điều kiện vẫn là lỗi A4 `critical`.

**Architecture:** LLM Compliance tiếp tục nhận diện khuyến mại cụ thể và đánh giá điều kiện áp dụng trong cùng một lần gọi hiện có. `compliance.py` giữ evidence CP4 mức 2 tạm thời, tìm dấu hiệu thời hạn trong evidence hoặc cửa sổ 240 ký tự chuẩn hóa tại những field mà evidence thật sự xuất hiện, rồi ghép hai vế thành mức CP4 cuối trước khi tính điểm và sinh flag; evidence tạm được bỏ khỏi criterion đạt để hợp đồng output không đổi.

**Tech Stack:** Python 3.11, `re`, test script thuần Python hiện có, YAML/Markdown documentation, Git.

## Global Constraints

- Không gọi Anthropic, không chạy E1 hoặc E5 trong kế hoạch này.
- Không sửa G-008, P-006a, `docs/goldset/labels.csv`, KB fact-check hoặc corpus brand.
- Không tăng số lần gọi LLM và không thay đổi JSON schema/hợp đồng output của Compliance Agent.
- CP4 không dùng mức `1`: thiếu thời hạn **hoặc** thiếu điều kiện đều là mức `0`, severity `critical`.
- Regex chỉ xác định có dấu hiệu thời hạn; LLM vẫn quyết định khuyến mại có giá trị cụ thể và điều kiện áp dụng.
- Chỉ xét thời hạn trong evidence hoặc cửa sổ 240 ký tự chuẩn hóa quanh evidence thật; không quét toàn field.
- Mọi production change phải đi qua RED → GREEN; test không được gọi API hoặc KB.

---

### Task 1: Nhận diện thời hạn trong vùng bằng chứng CP4

**Files:**
- Modify: `multiagent/scripts/test_compliance_rubric.py`
- Modify: `multiagent/src/agents/compliance.py`

**Interfaces:**
- Consumes: `evidence: str` và `text_theo_field: dict[str, str]` đã được `strip_html()`.
- Produces: `_cp4_co_thoi_han(evidence: str, text_theo_field: dict) -> bool`.
- Constant: `_CP4_CUA_SO = 240`, tính trên chuỗi đã gộp khoảng trắng và hạ chữ thường.

- [ ] **Step 1: Thêm test RED cho các định dạng thời hạn hợp lệ**

Thêm nhóm test sau vào `multiagent/scripts/test_compliance_rubric.py` và đăng ký từng hàm trong tuple `__main__`:

```python
def test_cp4_nhan_cac_dinh_dang_thoi_han_da_chot():
    cases = (
        "Áp dụng ngày 01/07/2023.",
        "Áp dụng từ 01/07 - 20/09/2023.",
        "Trước 6/4/2022, khách đặt cọc được ưu đãi.",
        "Chương trình kéo dài tới hết tháng 9.",
        "Khuyến mại trong vòng 3 tháng kể từ thời điểm kích hoạt HĐTP.",
        "Ưu đãi trong 3 tháng đầu.",
        "Áp dụng đến khi hết hàng.",
    )
    for evidence in cases:
        texts = {"title": "", "body": evidence, "meta_description": ""}
        assert compliance._cp4_co_thoi_han(evidence, texts), evidence
    print("[PASS] CP4 nhan du cac dang thoi han da chot")


def test_cp4_khong_nhan_so_lieu_khong_phai_thoi_han():
    for evidence in (
        "Gói thuê pin 350.000 đồng/tháng.",
        "Sạc trong 30 phút bằng trụ DC.",
        "Quãng đường tối đa 500 km/tháng.",
    ):
        texts = {"title": "", "body": evidence, "meta_description": ""}
        assert not compliance._cp4_co_thoi_han(evidence, texts), evidence
    print("[PASS] CP4 khong nham gia, quang duong, phut sac la thoi han")
```

Các literal kỳ vọng được suy ra trực tiếp từ spec, không dùng regex/helper production để dựng expected value.

- [ ] **Step 2: Chạy test và xác nhận RED đúng nguyên nhân**

Run:

```powershell
cd multiagent
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
```

Expected: FAIL vì `agents.compliance` chưa có `_cp4_co_thoi_han`; mọi test cũ trước điểm lỗi vẫn chạy bình thường.

- [ ] **Step 3: Thêm test RED cho cửa sổ lân cận và biên không quét toàn bài**

```python
def test_cp4_nhan_thoi_han_o_block_lien_ke_evidence():
    evidence = "Khuyến mại 199.000 đồng/tháng cho khách kích hoạt HĐTP."
    body = "Từ ngày 01/07 - 20/09/2023. " + evidence
    texts = {"title": "", "body": body, "meta_description": ""}
    assert compliance._cp4_co_thoi_han(evidence, texts)
    print("[PASS] CP4 nhan thoi han o block lien ke")


def test_cp4_khong_muon_ngay_o_xa_evidence():
    evidence = "Khuyến mại 199.000 đồng cho khách đặt cọc."
    body = "Bài cập nhật ngày 01/07/2023. " + ("x" * 300) + " " + evidence
    texts = {"title": "", "body": body, "meta_description": ""}
    assert not compliance._cp4_co_thoi_han(evidence, texts)
    print("[PASS] CP4 khong quet ngay o xa evidence")


def test_cp4_khong_muon_ngay_tu_field_khac():
    evidence = "Khuyến mại 199.000 đồng cho khách đặt cọc."
    texts = {
        "title": "Bài cập nhật ngày 01/07/2023",
        "body": evidence,
        "meta_description": "",
    }
    assert not compliance._cp4_co_thoi_han(evidence, texts)
    print("[PASS] CP4 khong muon ngay tu field khac")
```

Run lại cùng lệnh. Expected: vẫn FAIL do helper chưa tồn tại; hai test mô tả hai phía của biên 240 ký tự.

- [ ] **Step 4: Viết implementation tối thiểu cho helper**

Trong `multiagent/src/agents/compliance.py`, đặt regex/helper ngay trước khối `_LLM_PROMPT`:

```python
_CP4_CUA_SO = 240
_CP4_MOC_THOI_HAN = re.compile(
    r"(?:"
    r"\b\d{1,2}[/-]\d{1,2}\s*[-–—]\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b(?:từ(?: ngày)?|kể từ(?: ngày)?|trước|đến|tới(?: hết)?)\s+"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|"
    r"\b(?:đến|tới)\s+hết\s+tháng\s+\d{1,2}(?:/\d{4})?\b|"
    r"\btrong(?: vòng)?\s+\d+\s+(?:ngày|tháng|năm)(?:\s+đầu)?\b|"
    r"\b\d+\s+(?:ngày|tháng|năm)\s+kể từ\b|"
    r"\báp dụng\s+đến khi\s+hết hàng\b"
    r")",
    re.IGNORECASE,
)
_CP4_TACH_EVIDENCE = re.compile(r"\s+và\s+|[;\n]|(?<=[.%])\s+")


def _cp4_chuan_hoa(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _cp4_co_thoi_han(evidence: str, text_theo_field: dict) -> bool:
    """Có dấu hiệu thời hạn trong evidence hoặc sát evidence thật hay không."""
    if _CP4_MOC_THOI_HAN.search(_cp4_chuan_hoa(evidence)):
        return True

    manh = [
        _cp4_chuan_hoa(m).strip(" \"'“”…-")
        for m in _CP4_TACH_EVIDENCE.split(evidence or "")
    ]
    anchors = sorted((m for m in manh if m), key=len, reverse=True)
    if not anchors:
        return False

    for text in text_theo_field.values():
        kho = _cp4_chuan_hoa(text)
        for anchor in anchors:
            start = 0
            while True:
                vi_tri = kho.find(anchor, start)
                if vi_tri < 0:
                    break
                cua_so = kho[
                    max(0, vi_tri - _CP4_CUA_SO):
                    min(len(kho), vi_tri + len(anchor) + _CP4_CUA_SO)
                ]
                if _CP4_MOC_THOI_HAN.search(cua_so):
                    return True
                start = vi_tri + 1
    return False
```

Không đưa helper sang `text_utils.py`: regex này mang nghĩa nghiệp vụ “thời hạn khuyến mại”, không phải xử lý văn bản dùng chung.

- [ ] **Step 5: Chạy GREEN và mutation check**

Run cùng test script. Expected: tất cả test, gồm bốn test mới, PASS.

Mutation check thủ công:

- đổi `_CP4_CUA_SO` thành `1000` thì `test_cp4_khong_muon_ngay_o_xa_evidence` phải fail;
- bỏ giới hạn `field` thì `test_cp4_khong_muon_ngay_tu_field_khac` phải fail;
- bỏ nhánh `trong(?: vòng)?` thì test `trong vòng 3 tháng` phải fail;
- cho regex nhận `phút` thì test số liệu không phải thời hạn phải fail.

Hoàn nguyên mọi mutation trước khi tiếp tục.

- [ ] **Step 6: Commit Task 1**

```powershell
git add multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_rubric.py
git commit -m "test: nhan dien thoi han khuyen mai CP4"
```

---

### Task 2: Ghép kết quả điều kiện của LLM với thời hạn tất định

**Files:**
- Modify: `multiagent/scripts/test_compliance_rubric.py`
- Modify: `multiagent/src/agents/compliance.py`

**Interfaces:**
- Consumes: criterion CP4 sau `_hop_thuc_hoa()`, tạm có `occurrences=[{"field", "text"}]` cho cả mức `0`, `1`, `2`.
- Produces: `_chot_cp4(tu_llm: dict, text_theo_field: dict) -> dict` với level chỉ thuộc `{None, 0, 2}`.
- Preserves: `run(fields, ...) -> {score, flags, criteria}` và severity table hiện tại.

- [ ] **Step 1: Sửa test fake để phản ánh đầy đủ output nội bộ thật**

Trong `_llm()` của `test_compliance_rubric.py`, tính `muc_sau` trước và giữ evidence cho CP4 mức 2:

```python
def _llm(muc_theo_ma: dict, evidence: str = BODY):
    def fn(fields, text_theo_field):
        result = {}
        for ma, muc in muc_theo_ma.items():
            muc_sau = compliance._hop_thuc_hoa(ma, muc, evidence, text_theo_field)
            can_evidence = muc_sau in (0, 1) or (ma == "CP4" and muc_sau == 2)
            result[ma] = compliance._tieu_chi(
                ma,
                muc_sau,
                ([{"field": "body", "text": evidence}] if can_evidence else []),
                "ly do",
            )
        return result
    return fn
```

Đồng thời sửa `test_trich_dan_co_that_thi_giu_nguyen_muc`: đổi CP4 từ `2` sang `None` và bỏ assertion CP4 mức 2. Test đó đang dùng evidence `chạy được 420 km` để kiểm CP7; coi chính câu không phải khuyến mại này là bằng chứng CP4 đạt sẽ trái nghĩa CP4 mới. Không sửa expected của CP7.

Run test hiện tại trước khi thêm behavior mới. Expected: PASS; đây là cập nhật test double/fixture để phản ánh cấu trúc và ngữ nghĩa production sắp dùng, không phải làm yếu một assertion CP4 hợp lệ.

- [ ] **Step 2: Thêm test RED cho bảng ghép CP4**

```python
def test_cp4_du_dieu_kien_va_thoi_han_thi_muc_2():
    body = "Từ ngày 01/07 - 20/09/2023. Khuyến mại 199.000 đồng/tháng cho khách kích hoạt HĐTP."
    result = compliance.run(
        {"title": "", "body": body, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": None, "CP8": None},
                          evidence="Khuyến mại 199.000 đồng/tháng cho khách kích hoạt HĐTP."),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 2
    cp4_criterion = next(c for c in result["criteria"] if c["id"] == "CP4")
    assert cp4_criterion["occurrences"] == [], "evidence muc 2 chi duoc giu noi bo"
    assert not any(f["rule"].endswith("(CP4)") for f in result["flags"])
    print("[PASS] CP4 du dieu kien + thoi han -> muc 2")


def test_cp4_du_dieu_kien_nhung_thieu_thoi_han_thi_critical():
    evidence = "Khách hàng đặt cọc mua VF 8 được giảm ngay 3 triệu đồng."
    result = compliance.run(
        {"title": "", "body": evidence, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": None, "CP8": None},
                          evidence=evidence),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 0
    cp4 = [f for f in result["flags"] if f["rule"].endswith("(CP4)")]
    assert cp4 and cp4[0]["severity"] == "critical", result["flags"]
    assert "thời hạn" in cp4[0]["suggestion"].lower()
    print("[PASS] CP4 thieu thoi han -> muc 0 critical")


def test_cp4_co_thoi_han_nhung_thieu_dieu_kien_van_critical():
    evidence = "Giảm 3 triệu đồng đến 31/08/2024."
    result = compliance.run(
        {"title": "", "body": evidence, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 0, "CP7": None, "CP8": None},
                          evidence=evidence),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 0
    assert any(f["severity"] == "critical" and f["rule"].endswith("(CP4)")
               for f in result["flags"])
    print("[PASS] CP4 co thoi han nhung thieu dieu kien van critical")
```

Run test script. Expected: test “đủ điều kiện nhưng thiếu thời hạn” FAIL vì code hiện giữ nguyên mức 2; các test cũ phải không lỗi ngoài thay đổi kỳ vọng mới.

- [ ] **Step 3: Thêm test RED cho `NA`, evidence bịa và mức `1` ngoài rubric**

```python
def test_cp4_na_khong_bi_regex_tu_kich_hoat():
    body = "Bài viết ngày 01/07/2023 không có khuyến mại."
    result = compliance.run(
        {"title": "", "body": body, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": None, "CP7": None, "CP8": None}),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") is None
    print("[PASS] CP4 NA khong bi regex ngay thang tu kich hoat")


def test_cp4_evidence_bia_khong_duoc_dung_de_veto():
    result = compliance.run(
        {"title": "", "body": BODY_KHONG_SO, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": None, "CP8": None},
                          evidence="Khuyến mại 3 triệu đồng đến 31/08/2024."),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") is None
    assert not any(f["rule"].endswith("(CP4)") for f in result["flags"])
    print("[PASS] CP4 evidence bia -> NA, khong veto")


def test_cp4_muc_1_ngoai_rubric_duoc_chuan_hoa_ve_0():
    evidence = "Giảm 3 triệu đồng đến 31/08/2024."
    result = compliance.run(
        {"title": "", "body": evidence, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 1, "CP7": None, "CP8": None},
                          evidence=evidence),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 0
    print("[PASS] CP4 khong cho muc 1 lam mat veto A4")
```

Expected RED: test mức `1` FAIL vì code hiện giữ mức 1; test evidence bịa vẫn PASS và khóa biên an toàn cũ.

- [ ] **Step 4: Thêm test hồi quy bằng nội dung thật G-008 và P-006a**

```python
def test_cp4_g008_co_thoi_han_khong_bi_veto_oan():
    evidence = (
        "Khuyến mại 199.000 đồng/tháng không giới hạn số km trong vòng 3 tháng "
        "kể từ thời điểm kích hoạt HĐTP."
    )
    body = "Chính sách từ ngày 01/07 - 20/09/2023. " + evidence
    result = compliance.run(
        {"title": "", "body": body, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": 2, "CP8": None}, evidence),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 2
    print("[PASS] G-008 co thoi han -> CP4 khong veto oan")


def test_cp4_p006a_co_thoi_han_khong_bi_veto_oan():
    evidence = (
        "Trước 6/4/2022, khách hàng đặt cọc 2 mẫu xe VinFast VF 8 và VinFast "
        "VF 9 sẽ được nhận ưu đãi lên đến 250 triệu đồng."
    )
    result = compliance.run(
        {"title": "", "body": evidence, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": None, "CP8": None}, evidence),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP4") == 2
    print("[PASS] P-006a co thoi han -> CP4 khong veto oan")
```

Các đoạn này là literal đã đối chiếu từ fixture thật, không đọc hoặc sửa fixture khi test chạy.

- [ ] **Step 5: Implement `_chot_cp4()` và giữ evidence mức 2**

Trong `_danh_gia_llm()`, thay cách tạo `occ`:

```python
can_evidence = muc in (0, 1) or (ma == "CP4" and muc == 2)
occ = ([{"field": c["field"], "text": c["evidence"]}]
       if can_evidence else [])
```

Thêm helper:

```python
def _chot_cp4(tu_llm: dict, text_theo_field: dict) -> dict:
    """Ghép điều kiện do LLM đọc với thời hạn do code nhận diện."""
    muc = tu_llm["level"]
    if muc is None:
        return tu_llm
    if muc in (0, 1):
        # CP4 không có mức một phần: thiếu điều kiện là lỗi A4 mức 0.
        return _tieu_chi("CP4", 0, tu_llm["occurrences"], tu_llm["reason"])
    if muc != 2 or not tu_llm["occurrences"]:
        return _tieu_chi("CP4", None)

    evidence = tu_llm["occurrences"][0].get("text", "")
    if _cp4_co_thoi_han(evidence, text_theo_field):
        # Evidence mức 2 chỉ dùng nội bộ để chốt thời hạn; output đạt giữ
        # hình dạng cũ với occurrences rỗng.
        return _tieu_chi("CP4", 2)
    return _tieu_chi(
        "CP4", 0, tu_llm["occurrences"],
        "Khuyến mại đã nêu điều kiện áp dụng nhưng chưa thấy thời hạn trong "
        "đoạn khuyến mại hoặc nội dung liền kề. Bổ sung ngày bắt đầu/kết thúc "
        "hoặc thời lượng áp dụng ngay cạnh ưu đãi.",
    )
```

Trong `run()`, thay `llm["CP4"]` bằng:

```python
_chot_cp4(llm["CP4"], text_theo_field),
```

Sửa `_LLM_PROMPT` để CP4 chỉ chấm điều kiện:

```text
CP4 - Khuyến mại nêu giá trị cụ thể có đủ ĐIỀU KIỆN áp dụng hay không.
Hệ thống sẽ tự kiểm THỜI HẠN bằng code; bạn không kết luận thiếu/đủ thời hạn.
0 = có khuyến mại cụ thể nhưng thiếu điều kiện áp dụng
2 = có khuyến mại cụ thể và nêu đủ điều kiện áp dụng
NA = không có khuyến mại cụ thể của doanh nghiệp
Không dùng mức 1 cho CP4.
```

Giữ nguyên phần loại trừ lời mời chung chung và chính sách nhà nước; bỏ các câu giao LLM kiểm ngày tháng vì trách nhiệm đó đã chuyển sang code.

- [ ] **Step 6: Chạy GREEN và mutation check**

Run:

```powershell
cd multiagent
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
```

Expected: cả hai script exit 0; test registry xác nhận mọi `def test_*` mới đều nằm trong tuple `__main__`.

Mutation check:

- bỏ lời gọi `_chot_cp4()` trong `run()` thì test thiếu thời hạn phải fail;
- đổi nhánh LLM `0` thành giữ mức 2 khi có ngày thì test thiếu điều kiện phải fail;
- bỏ việc giữ evidence CP4 mức 2 thì test G-008/P-006a phải fail;
- đổi evidence bịa thành mức 0 thì test chống veto từ evidence bịa phải fail.

Hoàn nguyên mutations.

- [ ] **Step 7: Commit Task 2**

```powershell
git add multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_rubric.py
git commit -m "fix: tach thoi han va dieu kien trong CP4"
```

---

### Task 3: Khóa phiên bản prompt và đồng bộ tài liệu đo lường

**Files:**
- Modify: `docs/rubrics.md`
- Modify: `docs/technical-debt.md`
- Modify: `docs/evaluation-plan.md`
- Modify: `docs/sprint2-report.md`
- Verify only: `multiagent/scripts/eval_calibration.py`
- Verify only: `multiagent/scripts/test_eval_stability_resume.py`

**Interfaces:**
- Consumes: `eval_calibration.prompt_version() -> str`, tự băm sáu prompt hiện hành.
- Produces: tài liệu khớp code và đánh dấu E1/E5 cũ hết hiệu lực sau thay đổi CP4.

- [ ] **Step 1: Tính prompt version mới từ code, không chép theo suy đoán**

Run:

```powershell
cd multiagent
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'scripts'); import eval_calibration as e; print(e.prompt_version())"
```

Ghi lại đúng giá trị 16 ký tự do lệnh trả về. Không sửa `prompt_version()` vì nó đã bao phủ `compliance._LLM_PROMPT`; thay prompt CP4 phải tự làm hash đổi.

- [ ] **Step 2: Xác nhận chốt resume nhận version mới và từ chối version cũ**

Run:

```powershell
cd multiagent
.\.venv\Scripts\python.exe scripts\test_eval_stability_resume.py
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'scripts'); import eval_calibration as e; e.nap_ket_qua('../docs/evidence/e5_sau_sua_cp3_cp4.json')"
```

Expected: test E1 exit 0; lệnh gọi `nap_ket_qua()` dừng với thông báo `DUNG LAI` vì bản E5 cũ mang prompt version trước thay đổi CP4. Đây là lệnh chỉ đọc; không chạy `cham_gold_set()`.

- [ ] **Step 3: Cập nhật rubric và technical debt**

Trong `docs/rubrics.md`:

- đổi cột cách đo CP4 từ `LLM` thành `LLM điều kiện + regex thời hạn`;
- mô tả bảng ghép `{NA, 0, 2}` và khẳng định không dùng mức 1;
- thay mô tả “buộc LLM đọc lại thời hạn” bằng chốt tất định và dẫn spec.

Trong `docs/technical-debt.md`:

- đánh dấu mục 8.4 đã xử lý, ghi đúng thiết kế tách hai vế thay cho đề xuất cũ “thấy thời gian thì kéo lên mức 1”;
- đánh dấu mục 8.5 G-008 đã chẩn đoán: CP4 tạo cờ critical oan dù có hai dấu thời hạn;
- cập nhật snapshot commit/test count **sau** verification, không đoán trước;
- giữ các số E5 cũ như bằng chứng lịch sử nhưng ghi rõ chúng thuộc code trước chốt CP4.

- [ ] **Step 4: Cập nhật trạng thái phép đo**

Trong `docs/evaluation-plan.md` và `docs/sprint2-report.md`:

- giữ Kappa `0,713` và accuracy `0,879` như kết quả lịch sử sau B14;
- ghi rõ kết quả đó nay hết hiệu lực đối với code hiện tại vì CP4 đã đổi;
- thay prompt version cũ bằng giá trị vừa tính ở Step 1 tại phần snapshot hiện hành;
- không ghi Kappa/accuracy mới vì chưa chạy E5;
- không đổi `meta.calibrated` trong `scoring.yaml` khỏi `false`/`null`.

- [ ] **Step 5: Kiểm tra nhất quán tài liệu**

Run:

```powershell
rg -n "kéo lên mức 1|CP4.*LLM|0bdc5ab12ec65f89|E5.*0,713|G-008.*chưa biết|P-006a" docs\rubrics.md docs\technical-debt.md docs\evaluation-plan.md docs\sprint2-report.md
git diff --check
```

Expected:

- không còn câu vận hành nói CP4 chỉ do LLM chấm;
- không còn đề xuất hạ CP4 xuống mức 1;
- số `0,713` nếu còn đều được đánh dấu lịch sử/hết hiệu lực;
- hash cũ chỉ còn trong đoạn lịch sử có nhãn rõ, không được gọi là version hiện hành;
- `git diff --check` exit 0.

- [ ] **Step 6: Commit Task 3**

```powershell
git add docs/rubrics.md docs/technical-debt.md docs/evaluation-plan.md docs/sprint2-report.md
git commit -m "docs: dong bo chot tat dinh CP4"
```

---

### Task 4: Verification toàn bộ, không gọi API

**Files:**
- Verify only: `multiagent/scripts/test_*.py`
- Verify only: working tree and commits from Tasks 1-3

**Interfaces:**
- Consumes: toàn bộ code/test/docs của kế hoạch.
- Produces: bằng chứng test cục bộ và danh sách thay đổi sẵn sàng review; không tạo E1/E5 result.

- [ ] **Step 1: Chạy focused tests lần cuối**

```powershell
cd multiagent
.\.venv\Scripts\python.exe scripts\test_compliance_rubric.py
.\.venv\Scripts\python.exe scripts\test_moi_test_deu_chay.py
.\.venv\Scripts\python.exe scripts\test_eval_stability_resume.py
```

Expected: cả ba exit 0, không có request mạng.

- [ ] **Step 2: Chạy toàn bộ test scripts**

```powershell
cd multiagent
$failed = @()
Get-ChildItem scripts -Filter 'test_*.py' -File | Sort-Object Name | ForEach-Object {
    & .\.venv\Scripts\python.exe $_.FullName
    if ($LASTEXITCODE -ne 0) { $failed += $_.Name }
}
if ($failed.Count -gt 0) { throw "Failed tests: $($failed -join ', ')" }
```

Expected: mọi `test_*.py` exit 0. Lệnh này có thể dùng PostgreSQL local cho integration tests hiện có nhưng không gọi Anthropic và không chạy E1/E5.

- [ ] **Step 3: Xác minh dữ liệu đánh giá không bị sửa**

```powershell
git diff origin/main -- docs/goldset/labels.csv docs/goldset/raw docs/functional-tests multiagent/src/kb docs/brand/corpus
```

Expected: không có diff ở các đường dẫn dữ liệu/KB này.

- [ ] **Step 4: Xác minh phạm vi và lịch sử commit**

```powershell
git diff --check origin/main..HEAD
git status --short --branch
git log --oneline --decorate origin/main..HEAD
```

Expected:

- `git diff --check` sạch;
- worktree không có file chưa commit;
- chỉ có commit spec và các commit Tasks 1-3;
- không có file kết quả E1/E5 mới.

- [ ] **Step 5: Review trước khi tạo PR**

Dùng `superpowers:requesting-code-review` để kiểm tra:

- bảng ghép CP4 đúng spec;
- regex không quét toàn bài;
- G-008/P-006a không còn veto oan;
- ca thiếu điều kiện và ca thiếu thời hạn vẫn critical;
- prompt version và tài liệu đo lường đã đổi đúng;
- không có thay đổi ngoài phạm vi.

Chỉ sau khi review không còn finding quan trọng mới dùng quy trình hoàn tất nhánh/tạo PR. Không chạy E1/E5 trong bước review.

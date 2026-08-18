"""Kiem tra specs.json dung dinh dang truoc khi build KB.
Chay: .venv\\Scripts\\python.exe scripts\\test_kb_specs.py
"""
import json
import os
import sys
import tempfile
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import compliance  # noqa: E402

SPECS = os.path.join(os.path.dirname(__file__), "..", "src", "kb", "specs.json")
REQUIRED = {"model", "content_type", "langcode", "specs", "source_url", "verified"}

VALID_SAFETY_RULES = {
    "version": 1,
    "rules": [
        {
            "reference_id": "VF-SAFE-CHARGING-CABLE-001",
            "source_url": (
                "https://vinfastauto.com/vn_vi/"
                "bo-sac-di-dong-tai-nha-co-an-toan-khong"
            ),
            "accessed_at": "2026-08-17",
            "content_type": "cam_nang",
            "langcode": "vi",
            "rule": "Không kéo căng, gập, thắt, kéo hoặc dẫm lên cáp sạc.",
        },
        {
            "reference_id": "VF-SAFE-HIGH-VOLTAGE-001",
            "source_url": "https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien",
            "accessed_at": "2026-08-17",
            "content_type": "cam_nang",
            "langcode": "vi",
            "rule": (
                "Người dùng không tự tháo, sửa hoặc thay bộ phận, cáp hay "
                "đầu nối điện áp cao."
            ),
        },
    ],
}


def _load_temp_safety(data):
    with tempfile.TemporaryDirectory() as temp_dir:
        path = os.path.join(temp_dir, "safety_rules.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False)
        return compliance.load_safety_rules(path)


def _expect_safety_invalid(data, fragment):
    try:
        _load_temp_safety(data)
    except ValueError as error:
        assert fragment.casefold() in str(error).casefold(), str(error)
    else:
        raise AssertionError(f"safety rules sai phai bi tu choi: {fragment}")


def test_safety_rules_file_chinh_thuc_dung_exact_contract():
    assert compliance.load_safety_rules() == VALID_SAFETY_RULES
    print("[PASS] safety_rules.json co dung 2 reference VinFast chinh thuc")


def test_safety_rules_tu_choi_duplicate_reference_id():
    data = deepcopy(VALID_SAFETY_RULES)
    data["rules"][1]["reference_id"] = data["rules"][0]["reference_id"]
    _expect_safety_invalid(data, "duplicate reference_id")
    print("[PASS] safety source tu choi duplicate reference_id")


def test_safety_rules_tu_choi_url_khong_https():
    data = deepcopy(VALID_SAFETY_RULES)
    data["rules"][0]["source_url"] = "http://vinfastauto.com/khong-an-toan"
    _expect_safety_invalid(data, "https")
    print("[PASS] safety source tu choi URL khong HTTPS")


def test_safety_rules_tu_choi_accessed_at_thieu_hoac_sai():
    missing = deepcopy(VALID_SAFETY_RULES)
    del missing["rules"][0]["accessed_at"]
    _expect_safety_invalid(missing, "accessed_at")
    invalid = deepcopy(VALID_SAFETY_RULES)
    invalid["rules"][0]["accessed_at"] = "17/08/2026"
    _expect_safety_invalid(invalid, "accessed_at")
    print("[PASS] safety source tu choi accessed_at thieu/sai ISO")


def test_safety_rules_tu_choi_profile_sai_kieu():
    for key, value in (("content_type", 1), ("langcode", ["vi"])):
        data = deepcopy(VALID_SAFETY_RULES)
        data["rules"][0][key] = value
        _expect_safety_invalid(data, key)
    print("[PASS] safety source tu choi content_type/langcode sai kieu")


def test_safety_rules_tu_choi_rule_rong_va_version_la():
    empty = deepcopy(VALID_SAFETY_RULES)
    empty["rules"][0]["rule"] = "  "
    _expect_safety_invalid(empty, "rule")
    version = deepcopy(VALID_SAFETY_RULES)
    version["version"] = 2
    _expect_safety_invalid(version, "version")
    print("[PASS] safety source tu choi rule rong va version la")

if __name__ == "__main__":
    failed = False
    with open(SPECS, encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list) or not entries:
        print("[FAIL] specs.json phai la list khong rong")
        sys.exit(1)

    ids = set()
    for i, e in enumerate(entries):
        missing = REQUIRED - set(e)
        if missing:
            print(f"[FAIL] entry {i} thieu khoa: {missing}")
            failed = True
        if not isinstance(e.get("specs"), dict) or not e["specs"]:
            print(f"[FAIL] entry {i} 'specs' phai la dict khong rong")
            failed = True
        key = (e.get("content_type"), e.get("langcode"), e.get("model"))
        if key in ids:
            print(f"[FAIL] trung id: {key}")
            failed = True
        ids.add(key)

    for fn in (
        test_safety_rules_file_chinh_thuc_dung_exact_contract,
        test_safety_rules_tu_choi_duplicate_reference_id,
        test_safety_rules_tu_choi_url_khong_https,
        test_safety_rules_tu_choi_accessed_at_thieu_hoac_sai,
        test_safety_rules_tu_choi_profile_sai_kieu,
        test_safety_rules_tu_choi_rule_rong_va_version_la,
    ):
        try:
            fn()
        except (AssertionError, OSError, ValueError, AttributeError) as error:
            print(f"[FAIL] {fn.__name__}: {error}")
            failed = True

    print(f"[{'FAIL' if failed else 'PASS'}] {len(entries)} entry")
    sys.exit(1 if failed else 0)

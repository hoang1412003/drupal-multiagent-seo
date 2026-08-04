"""Test compliance.run() gop ket qua fact-check (CP3) dung, va khi fact_check
loi (KB chua dung) thi KHONG lam sap compliance.

Tiem danh_gia_llm/danh_gia_cp3 gia de khong goi API/KB that.
Chay: .venv\\Scripts\\python.exe scripts\\test_compliance_factcheck_merge.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import compliance

BODY = "VF 8 chạy 500km"


def _llm_toan_na(fields, text_theo_field):
    return {ma: compliance._tieu_chi(ma, None) for ma in compliance._MA_LLM}


def _muc(result, ma):
    return next(c["level"] for c in result["criteria"] if c["id"] == ma)


def test_cp3_lech_thanh_flag_critical():
    def cp3_lech(fields, **k):
        return {
            "level": 0,
            "occurrences": [{"field": "body", "text": BODY,
                             "rule": "Thông tin sai lệch so với thông số công bố chính thức"}],
            "reason": "sửa lại theo nguồn chính thức",
        }

    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm_toan_na, danh_gia_cp3=cp3_lech,
    )
    fc = [f for f in result["flags"] if "sai lệch" in f["rule"].lower()]
    assert len(fc) == 1, f"ket qua fact-check phai duoc gop, got {result['flags']}"
    assert fc[0]["severity"] == "critical", fc[0]
    print("[PASS] CP3 muc 0 -> flag critical duoc gop vao compliance")


def test_cp3_khong_tra_duoc_khong_kich_hoat_veto():
    """Diem then chot cua rubrics.md muc 6.2: muc 1 sinh flag de nguoi duyet
    biet, nhung severity la `low` nen KHONG veto."""
    def cp3_chua_tra_duoc(fields, **k):
        return {
            "level": 1,
            "occurrences": [{"field": "body", "text": BODY,
                             "rule": "Số liệu chưa kiểm chứng được bằng thông số công bố"}],
            "reason": "cần người kiểm chứng thủ công",
        }

    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm_toan_na, danh_gia_cp3=cp3_chua_tra_duoc,
    )
    assert result["flags"], "phai co flag de nguoi duyet biet"
    assert not any(f["severity"] == "critical" for f in result["flags"]), result["flags"]
    print("[PASS] CP3 muc 1 -> co flag nhung khong critical (khong veto oan)")


def test_loi_factcheck_khong_lam_sap_agent():
    def boom(fields, **k):
        raise RuntimeError("KB chua dung")

    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm_toan_na, danh_gia_cp3=boom,
    )
    assert isinstance(result["flags"], list), "loi fact-check khong duoc lam sap run()"
    assert _muc(result, "CP3") is None, "loi ha tang -> NA, khong phai muc 0"
    print("[PASS] loi fact-check -> CP3 NA, khong lam sap compliance")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_cp3_lech_thanh_flag_critical,
        test_cp3_khong_tra_duoc_khong_kich_hoat_veto,
        test_loi_factcheck_khong_lam_sap_agent,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

"""Test logic Brand Voice Agent bang rules GIA - khong doc brand_rules.json
that, khong goi LLM, khong doc KB.

Chay: .venv\\Scripts\\python.exe scripts\\test_brand_voice.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import brand_voice

RULES = {
    "model_names": ["VF 8"],
    "terms": [{"standard": "ô tô điện", "non_standard": ["xe hơi điện"],
               "docs": [7, 7], "occurrences": [156, 157], "p_value": 0.01562}],
    "excluded_terms": ["xe hơi điện cao cấp"],
    "address_form": {"standard": "bạn", "docs": [9, 10],
                     "occurrences": [120, 140], "p_value": 0.021},
    "title_case": {"standard": "SENTENCE_CASE", "docs": [15, 16], "p_value": 0.00052},
}


def _muc(ket_qua, ma):
    return next(c["level"] for c in ket_qua["criteria"] if c["id"] == ma)


def test_bv1_ba_cho_sai_muc_0():
    kq = brand_voice.run(
        {"title": "Đánh giá VF8", "body": "VF8 rất tốt. vf8 tiết kiệm.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV1") == 0, kq["criteria"]
    print("[PASS] 3 cho viet VF8 -> BV1 muc 0")


def test_bv1_mot_cho_sai_muc_1():
    kq = brand_voice.run(
        {"title": "Đánh giá xe", "body": "VF8 rất tốt.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV1") == 1, kq["criteria"]
    print("[PASS] 1 cho viet VF8 -> BV1 muc 1")


def test_bv1_viet_dung_muc_2():
    kq = brand_voice.run(
        {"title": "Đánh giá xe", "body": "VF 8 rất tốt.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV1") == 2, kq["criteria"]
    print("[PASS] viet 'VF 8' dung -> BV1 muc 2")


def test_bv1_khong_nhac_model_la_na():
    kq = brand_voice.run(
        {"title": "Hướng dẫn sạc pin", "body": "Sạc pin đúng cách.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV1") is None, kq["criteria"]
    print("[PASS] khong nhac model -> BV1 = NA (KHONG phai muc 2)")


def test_bv2_bien_the_thieu_so():
    kq = brand_voice.run(
        {"title": "Xe hơi điện", "body": "xe hơi điện tiết kiệm.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV2") == 1, kq["criteria"]
    print("[PASS] 2 cho dung bien the thieu so -> BV2 muc 1")


def test_bv7_tu_bi_loai():
    kq = brand_voice.run(
        {"title": "Đánh giá", "body": "Đây là xe hơi điện cao cấp.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV7") == 0, kq["criteria"]
    print("[PASS] dung tu bi loai -> BV7 muc 0")


def test_bv3_lan_hai_kieu_xung_ho():
    kq = brand_voice.run(
        {"title": "Hướng dẫn", "body": "bạn nên sạc. quý khách lưu ý.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV3") == 1, kq["criteria"]
    print("[PASS] lan 2 kieu xung ho -> BV3 muc 1")


def test_bv5_title_viet_hoa_toan_bo():
    kq = brand_voice.run(
        {"title": "LƯU Ý SỬ DỤNG PIN LFP", "body": "Nội dung.", "summary": ""},
        rules=RULES,
    )
    assert _muc(kq, "BV5") == 0, kq["criteria"]
    print("[PASS] title VIET HOA TOAN BO -> BV5 muc 0")


def test_bv6_khong_co_judge_la_na():
    kq = brand_voice.run(
        {"title": "Hướng dẫn", "body": "Nội dung.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV6") is None, kq["criteria"]
    assert kq["score"] is not None, "6 tieu chi con lai van phai cham duoc"
    print("[PASS] khong co judge BV6 -> NA, agent VAN tra diem")


def test_bai_rong_tra_none():
    kq = brand_voice.run({"title": "", "body": "", "summary": ""}, rules=RULES)
    assert kq is None, kq
    print("[PASS] bai rong -> run() tra None")


def test_loi_o_hai_field_sinh_hai_issue():
    kq = brand_voice.run(
        {"title": "Đánh giá VF8", "body": "VF8 tốt lắm.", "summary": ""}, rules=RULES
    )
    bv1_issues = [i for i in kq["issues"] if "BV1" in i["type"]]
    assert {i["field"] for i in bv1_issues} == {"title", "body"}, bv1_issues
    print("[PASS] loi o 2 field -> 2 issue, moi cai dung field")


def test_muc_2_va_na_khong_sinh_issue():
    kq = brand_voice.run(
        {"title": "Hướng dẫn sạc pin", "body": "bạn nên sạc ô tô điện đúng cách.",
         "summary": ""},
        rules=RULES,
    )
    assert kq["issues"] == [], kq["issues"]
    print("[PASS] khong loi -> khong sinh issue nao")


def test_tat_dinh_nam_lan():
    fields = {"title": "Đánh giá VF8", "body": "VF8 và xe hơi điện.", "summary": ""}
    diem = {brand_voice.run(fields, rules=RULES)["score"] for _ in range(5)}
    assert len(diem) == 1, diem
    print(f"[PASS] cham 5 lan ra dung mot diem: {diem.pop()}")


def test_corpus_khong_co_chuan_xung_ho_thi_bv4_na():
    """Truong hop THAT cua du an: 16 bai BRAND khong thong nhat xung ho nen
    brand_rules.json co address_form = None. BV4 phai tra NA, KHONG phai 0 -
    khong duoc phat bai viet vi corpus khong co chuan."""
    rules = dict(RULES, address_form=None)
    kq = brand_voice.run(
        {"title": "Hướng dẫn", "body": "bạn nên sạc pin.", "summary": ""}, rules=rules
    )
    assert _muc(kq, "BV4") is None, kq["criteria"]
    print("[PASS] corpus khong co chuan xung ho -> BV4 = NA")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_bv1_ba_cho_sai_muc_0,
        test_bv1_mot_cho_sai_muc_1,
        test_bv1_viet_dung_muc_2,
        test_bv1_khong_nhac_model_la_na,
        test_bv2_bien_the_thieu_so,
        test_bv7_tu_bi_loai,
        test_bv3_lan_hai_kieu_xung_ho,
        test_bv5_title_viet_hoa_toan_bo,
        test_bv6_khong_co_judge_la_na,
        test_bai_rong_tra_none,
        test_loi_o_hai_field_sinh_hai_issue,
        test_muc_2_va_na_khong_sinh_issue,
        test_tat_dinh_nam_lan,
        test_corpus_khong_co_chuan_xung_ho_thi_bv4_na,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

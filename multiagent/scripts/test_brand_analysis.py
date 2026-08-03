"""Test cac ham dem dac trung brand + kiem dinh nhi thuc.

Khong goi LLM, khong doc KB. Chay:
    .venv\\Scripts\\python.exe scripts\\test_brand_analysis.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from brand_analysis import (
    SIGNIFICANCE,
    binom_two_sided_p,
    classify_title_case,
    count_model_name_usage,
    count_variants,
)
from text_utils import strip_html


def test_strip_html_bo_the_va_thuoc_tinh():
    html = '<p>Xe <strong>ô tô điện</strong></p><img alt="xe hoi dien">'
    text = strip_html(html)
    assert "ô tô điện" in text, text
    # alt text nam trong THUOC TINH, khong duoc tinh la chu cua bai
    assert "xe hoi dien" not in text, text
    print("[PASS] strip_html bo the va khong lay thuoc tinh")


def test_count_variants_uu_tien_bien_the_dai():
    # "xe ô tô điện" CHUA "ô tô điện" - neu khong uu tien dai truoc thi
    # mot lan xuat hien bi dem cho ca hai
    counts = count_variants("xe ô tô điện rất tốt", ["ô tô điện", "xe ô tô điện"])
    assert counts == {"ô tô điện": 0, "xe ô tô điện": 1}, counts
    print("[PASS] count_variants uu tien bien the dai hon")


def test_count_variants_khong_phan_biet_hoa_thuong():
    counts = count_variants("Ô TÔ ĐIỆN và ô tô điện", ["ô tô điện"])
    assert counts == {"ô tô điện": 2}, counts
    print("[PASS] count_variants khong phan biet hoa/thuong")


def test_count_model_name_phan_biet_cach_viet():
    ok, wrong = count_model_name_usage("VF 8 chạy tốt, VF8 và vf8 cũng vậy", ["VF 8"])
    assert ok == 1, ok
    assert wrong == ["VF8", "vf8"], wrong
    print("[PASS] count_model_name phan biet 'VF 8' voi 'VF8'/'vf8'")


def test_count_model_name_khong_khop_so_dai_hon():
    ok, wrong = count_model_name_usage("mẫu VF 88 chưa ra mắt", ["VF 8"])
    assert ok == 0 and wrong == [], (ok, wrong)
    print("[PASS] count_model_name khong khop nham 'VF 88'")


def test_classify_title_case():
    assert classify_title_case("LƯU Ý SỬ DỤNG PIN LFP") == "ALL_CAPS"
    assert classify_title_case("Hướng Dẫn Sạc Pin Ô Tô Điện") == "TITLE_CASE"
    assert classify_title_case("Hướng dẫn sạc pin ô tô điện") == "SENTENCE_CASE"
    print("[PASS] classify_title_case phan 3 kieu")


def test_binom_p_values():
    # Cac gia tri nay quyet dinh nguong ">=9/10" o build_brand_guideline
    cases = {10: 0.00195, 9: 0.02148, 8: 0.10938, 7: 0.34375, 5: 1.0}
    for k, expected in cases.items():
        p = binom_two_sided_p(k, 10)
        assert abs(p - expected) < 1e-4, f"k={k}: {p} != {expected}"
    print("[PASS] binom_two_sided_p dung gia tri tra bang")


def test_binom_nguong_9_tren_10():
    # Day la ly do nguong la 9/10 chu khong phai so tu dat
    assert binom_two_sided_p(9, 10) < SIGNIFICANCE
    assert binom_two_sided_p(8, 10) > SIGNIFICANCE
    print("[PASS] 9/10 dat muc y nghia, 8/10 khong dat")


if __name__ == "__main__":
    test_strip_html_bo_the_va_thuoc_tinh()
    test_count_variants_uu_tien_bien_the_dai()
    test_count_variants_khong_phan_biet_hoa_thuong()
    test_count_model_name_phan_biet_cach_viet()
    test_count_model_name_khong_khop_so_dai_hon()
    test_classify_title_case()
    test_binom_p_values()
    test_binom_nguong_9_tren_10()
    print("OK")

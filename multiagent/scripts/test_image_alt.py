"""Test boc alt text cua MOI anh trong bai, khong chi anh dai dien.

HOI QUY cho lech co he thong da ghi o docs/evaluation-plan.md muc 4.5 dieu
kien 4: ma loi B6 (annotation-guideline v1.2) xet MOI the <img> trong body,
con he thong chi xet mot anh dai dien -> hai ben do hai tap anh khac nhau
nen Recall/F1 cua tieu chi SEO9 khong so duoc.

Bang chung do duoc 2026-07-30 tren node/7: bai co 2 anh, anh dai dien co alt
'xe vf6' va 1 anh trong body KHONG co alt - anh thieu alt lot luoi hoan toan.

Chay: .venv\\Scripts\\python.exe scripts\\test_image_alt.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from drupal_client import _alt_cua_the_img, _extract_image_alt


def _resource(alt_dai_dien=None):
    if alt_dai_dien is None:
        return {"relationships": {}}
    return {"relationships": {"field_image": {"data": {"meta": {"alt": alt_dai_dien}}}}}


def test_anh_trong_body_khong_con_lot_luoi():
    """Chinh ca node/7: anh dai dien co alt, anh trong body khong co."""
    ket = _extract_image_alt(_resource("xe vf6"), '<p>Noi dung</p><img src="a.png">')
    assert "Ảnh đại diện: xe vf6" in ket, ket
    assert "Ảnh 1 trong bài: " in ket, ket
    assert ket.rstrip().endswith("Ảnh 1 trong bài:"), f"alt phai trong: {ket!r}"
    print("[PASS] anh trong body khong con lot luoi")


def test_dem_dung_nhieu_anh():
    body = '<img alt="mot"><p>x</p><img alt="hai"><img src="b.png">'
    ket = _extract_image_alt(_resource(), body)
    assert ket.count("trong bài") == 3, ket
    assert "Ảnh 3 trong bài:" in ket and ket.rstrip().endswith("Ảnh 3 trong bài:"), ket
    print("[PASS] dem dung 3 anh, anh thu 3 thieu alt")


def test_bai_khong_co_anh_tra_chuoi_rong():
    """Chuoi rong = bai khong co anh nao -> KHONG phai loi, khac han voi
    'co anh nhung thieu alt'."""
    assert _extract_image_alt(_resource(), "<p>Chi co chu</p>") == ""
    print("[PASS] bai khong co anh -> chuoi rong")


def test_alt_rong_tinh_la_thieu():
    """alt=\"\" phai tinh la THIEU, khong phai 'co alt'."""
    ket = _extract_image_alt(_resource(), '<img alt="" src="a.png">')
    assert ket.rstrip().endswith("Ảnh 1 trong bài:"), ket
    print("[PASS] alt='' tinh la thieu alt")


def test_ba_kieu_dau_nhay():
    assert _alt_cua_the_img('<img alt="hai nhay">') == "hai nhay"
    assert _alt_cua_the_img("<img alt='mot nhay'>") == "mot nhay"
    assert _alt_cua_the_img("<img alt=khong-nhay>") == "khong-nhay"
    print("[PASS] nhan ca 3 kieu dau nhay cua thuoc tinh alt")


def test_data_alt_khong_bi_nhan_nham():
    """HOI QUY: \\b khop ngay giua dau gach va chu nen data-alt bi doc nham
    thanh alt. Sai theo huong nguy hiem - anh THIEU alt that nhung co
    data-alt se bi coi la co alt, tuc BO SOT loi B6."""
    assert _alt_cua_the_img('<img data-alt="gia" src="a.png">') == "", \
        "data-alt KHONG phai alt"
    assert _alt_cua_the_img('<img myalt="gia" src="a.png">') == ""
    print("[PASS] data-alt/myalt khong bi nhan nham thanh alt")


def test_lay_dung_alt_khi_co_nhieu_thuoc_tinh():
    assert _alt_cua_the_img('<img srcset="a.png 1x" alt="that">') == "that"
    assert _alt_cua_the_img('<img data-alt="gia" alt="that">') == "that"
    print("[PASS] lay dung thuoc tinh alt khi co nhieu thuoc tinh")


def test_giu_duoc_anh_dai_dien_khi_body_rong():
    ket = _extract_image_alt(_resource("xe vf6"), "")
    assert ket == "Ảnh đại diện: xe vf6", ket
    print("[PASS] van doc duoc anh dai dien khi body khong co anh")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_anh_trong_body_khong_con_lot_luoi,
        test_dem_dung_nhieu_anh,
        test_bai_khong_co_anh_tra_chuoi_rong,
        test_alt_rong_tinh_la_thieu,
        test_ba_kieu_dau_nhay,
        test_data_alt_khong_bi_nhan_nham,
        test_lay_dung_alt_khi_co_nhieu_thuoc_tinh,
        test_giu_duoc_anh_dai_dien_khi_body_rong,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

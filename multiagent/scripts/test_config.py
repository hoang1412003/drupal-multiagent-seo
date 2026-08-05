"""Test nap config theo (content_type, langcode).

Khong goi LLM, khong can Drupal. Chay:
    .venv\\Scripts\\python.exe scripts\\test_config.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config


def test_tra_dung_khoa():
    c = config.load("cam_nang", "vi")
    assert c["weights"]["compliance"] == 0.30, c["weights"]
    assert c["decision"]["publish_min"] == 80, c["decision"]
    print("[PASS] tra dung khoa cam_nang:vi")


def test_khoa_khong_co_thi_fallback_default():
    c = config.load("landing_page", "en")
    assert c["weights"]["compliance"] == 0.30, c["weights"]
    print("[PASS] khoa khong co -> fallback default")


def test_giu_nguyen_gia_tri_dang_hard_code():
    """Buoc 1 cua config-spec.md muc 7 la REFACTOR THUAN - hanh vi khong duoc
    doi. Test nay khoa lai dung bo so dang chay truoc khi tach config."""
    c = config.load()
    assert c["weights"] == {
        "content_quality": 0.25, "seo": 0.20, "brand": 0.25, "compliance": 0.30,
    }, c["weights"]
    assert c["decision"]["publish_min"] == 80
    assert c["decision"]["needs_revision_min"] == 50
    assert c["decision"]["compliance_veto_below"] == 50
    print("[PASS] gia tri trong config khop bo dang hard-code truoc do")


def test_trong_so_cong_lai_bang_1():
    c = config.load()
    assert abs(sum(c["weights"].values()) - 1.0) < 1e-9, sum(c["weights"].values())
    print("[PASS] tong trong so = 1.0")


def test_hai_ho_nguong_co_y_khac_nhau():
    """scoring.title_ideal (dai LY TUONG de cham diem) KHAC labelling.title_ok
    (dai 'sai ro rang' de gan nhan). Gop chung lam mot la dung dai ly tuong
    lam ranh gioi nhan -> gan nhu moi bai that deu dinh loi -> phan bo nhan
    sup do -> Kappa mat y nghia (config-spec.md muc 2)."""
    c = config.load()
    assert c["scoring"]["title_ideal"] == [50, 60], c["scoring"]
    assert c["labelling"]["title_ok"] == [40, 70], c["labelling"]
    assert c["scoring"]["title_ideal"] != c["labelling"]["title_ok"]
    print("[PASS] hai ho nguong scoring/labelling tach bach")


def test_canh_bao_khi_chua_calibrate():
    """meta.calibrated = false -> phai canh bao, de khong lo trinh bay ket qua
    chay bang nguong minh hoa nhu the da calibrate."""
    canh_bao = config.kiem_tra_meta(config.load(), model_dang_dung="claude-haiku-4-5-20251001")
    assert any("chưa calibrate" in c for c in canh_bao), canh_bao
    print("[PASS] chua calibrate -> co canh bao")


def test_canh_bao_khi_model_lech():
    """ANTHROPIC_MODEL doc tu bien moi truong nen ai do doi .env la toan bo
    nguong da calibrate mat hieu luc MA KHONG CO DAU HIEU GI (config-spec.md
    muc 5a). Day la bay im lang dung nghia."""
    c = config.load()
    c["meta"]["calibrated"] = True
    c["meta"]["model"] = "claude-sonnet-5"
    canh_bao = config.kiem_tra_meta(c, model_dang_dung="claude-haiku-4-5-20251001")
    assert any("model" in w.lower() for w in canh_bao), canh_bao
    print("[PASS] model lech voi luc calibrate -> co canh bao")


def test_khong_canh_bao_khi_moi_thu_khop():
    c = config.load()
    c["meta"]["calibrated"] = True
    c["meta"]["model"] = "claude-haiku-4-5-20251001"
    assert config.kiem_tra_meta(c, model_dang_dung="claude-haiku-4-5-20251001") == []
    print("[PASS] da calibrate + dung model -> khong canh bao")


def test_khoi_default_va_khoa_that_giong_nhau():
    """Truoc khi calibrate, 'cam_nang:vi' phai y het 'default'. Lech nhau o
    giai doan nay la dau hieu sua tay mot ben ma quen ben kia."""
    assert config.load("cam_nang", "vi") == config.load("khong_ton_tai", "xx")
    print("[PASS] khoi cam_nang:vi giong het default (chua calibrate)")


def test_cache_khong_lan_giua_hai_file():
    """`load(path=...)` phai doc dung file duoc chi.

    Ban cu cache vao mot bien global va BO QUA tham so `path`, nen lan goi thu
    hai voi file khac van tra noi dung file da nap truoc do - tham so hua mot
    dang, ham lam mot neo. Chua gay loi that vi production chi co mot file,
    nhung day dung la loai bay im lang ma du an von phong."""
    import tempfile

    thu_muc = tempfile.mkdtemp()
    khac = os.path.join(thu_muc, "scoring_khac.yaml")
    with open(khac, "w", encoding="utf-8") as f:
        f.write("default:\n  weights:\n    compliance: 0.99\n")

    config.load()                      # lam am cache bang file that
    c = config.load(path=khac)
    assert c["weights"]["compliance"] == 0.99, c["weights"]

    # va chieu nguoc lai: file that khong bi file tam de len
    assert config.load()["weights"]["compliance"] == 0.30
    print("[PASS] cache tach theo duong dan, khong lan giua hai file")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_tra_dung_khoa,
        test_khoa_khong_co_thi_fallback_default,
        test_giu_nguyen_gia_tri_dang_hard_code,
        test_trong_so_cong_lai_bang_1,
        test_hai_ho_nguong_co_y_khac_nhau,
        test_canh_bao_khi_chua_calibrate,
        test_canh_bao_khi_model_lech,
        test_khong_canh_bao_khi_moi_thu_khop,
        test_khoi_default_va_khoa_that_giong_nhau,
        test_cache_khong_lan_giua_hai_file,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

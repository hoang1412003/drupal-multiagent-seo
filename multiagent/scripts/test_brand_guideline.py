"""Test logic thong ke sinh brand guideline, dung corpus GIA.

Khong doc file that, khong goi LLM. Kiem dung 3 nhanh quyet dinh:
  - >=9/10 bai  -> sinh quy tac
  - 8/10 bai    -> KHONG sinh, vao muc "chua du can cu"
  - 0 lan xuat hien -> vao danh sach tu bi loai (BV7)
Chay: .venv\\Scripts\\python.exe scripts\\test_brand_guideline.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from build_brand_guideline import analyze_corpus

CANDIDATES = {
    "model_names": ["VF 8"],
    "term_pairs": [["ô tô điện", "xe hơi điện"]],
    "address_forms": ["bạn", "quý khách"],
}


def _corpus(so_bai_dung_chuan: int, tong: int = 10, bien_the="xe hơi điện"):
    """Sinh corpus gia: n bai dung 'o to dien', so con lai dung bien the."""
    docs = []
    for i in range(tong):
        chuan = i < so_bai_dung_chuan
        tu = "ô tô điện" if chuan else bien_the
        docs.append({
            "sample_id": f"B-{i + 1:03d}",
            "title": "Hướng dẫn sử dụng xe",
            "text": f"Khi dùng {tu} bạn nên chú ý. {tu} rất tiết kiệm.",
        })
    return docs


def test_10_tren_10_sinh_quy_tac():
    rules = analyze_corpus(_corpus(10), CANDIDATES)
    terms = {t["standard"]: t for t in rules["terms"]}
    assert "ô tô điện" in terms, rules
    assert terms["ô tô điện"]["docs"] == [10, 10], terms
    assert terms["ô tô điện"]["p_value"] < 0.05
    print("[PASS] 10/10 bai -> sinh quy tac")


def test_9_tren_10_sinh_quy_tac():
    rules = analyze_corpus(_corpus(9), CANDIDATES)
    terms = {t["standard"]: t for t in rules["terms"]}
    assert "ô tô điện" in terms, rules
    assert terms["ô tô điện"]["non_standard"] == ["xe hơi điện"], terms
    print("[PASS] 9/10 bai -> sinh quy tac")


def test_8_tren_10_khong_sinh_quy_tac():
    rules = analyze_corpus(_corpus(8), CANDIDATES)
    assert rules["terms"] == [], rules["terms"]
    chua_du = [u for u in rules["undecided"] if u["kind"] == "term"]
    assert len(chua_du) == 1, rules["undecided"]
    assert abs(chua_du[0]["p_value"] - 0.10938) < 1e-4, chua_du
    print("[PASS] 8/10 bai -> chua du can cu, KHONG sinh quy tac")


def test_bien_the_0_lan_vao_danh_sach_loai():
    # Moi bai deu dung chuan -> "xe hoi dien" xuat hien 0 lan
    rules = analyze_corpus(_corpus(10), CANDIDATES)
    assert "xe hơi điện" in rules["excluded_terms"], rules["excluded_terms"]
    print("[PASS] bien the 0 lan -> danh sach tu bi loai (BV7)")


def test_bien_the_co_xuat_hien_khong_vao_danh_sach_loai():
    rules = analyze_corpus(_corpus(9), CANDIDATES)
    assert "xe hơi điện" not in rules["excluded_terms"], rules["excluded_terms"]
    print("[PASS] bien the co xuat hien -> BV2, khong phai BV7")


def test_dem_theo_bai_va_theo_lan_tach_rieng():
    rules = analyze_corpus(_corpus(10), CANDIDATES)
    term = rules["terms"][0]
    assert term["docs"] == [10, 10], term
    # moi bai dung 2 lan -> 20 lan / 20 tong
    assert term["occurrences"] == [20, 20], term
    print("[PASS] so bai va so lan la 2 con so rieng")


def test_xung_ho_chuan_rut_duoc():
    rules = analyze_corpus(_corpus(10), CANDIDATES)
    assert rules["address_form"]["standard"] == "bạn", rules["address_form"]
    print("[PASS] rut duoc xung ho chuan")


def test_bai_khong_nhac_khong_tinh_vao_mau_so():
    """HOI QUY - loi that da gap ngay 2026-08-03.

    Bai khong nhac toi nhom khai niem thi KHONG bo phieu. Ban dau code dem
    so bai so voi TOAN corpus, nen 'xe may dien' thang tuyet doi trong 4/4
    bai co ban ve xe may (106 lan, doi thu 0 lan) van bi ket luan "chua du
    can cu" chi vi 6 bai con lai viet ve chu de khac. Im lang khong phai
    phan doi.
    """
    docs = [{"sample_id": f"B-{i:03d}", "title": "Tiêu đề bài",
             "text": "Dùng ô tô điện rất tốt. ô tô điện bền. bạn nên mua."}
            for i in range(6)]
    docs += [{"sample_id": f"B-{i:03d}", "title": "Tiêu đề bài",
              "text": "Bài này viết về chủ đề hoàn toàn khác. bạn lưu ý."}
             for i in range(6, 10)]

    rules = analyze_corpus(docs, CANDIDATES)
    terms = {t["standard"]: t for t in rules["terms"]}
    assert "ô tô điện" in terms, f"phai sinh quy tac, got undecided={rules['undecided']}"
    # mau so la 6 (so bai co nhac), KHONG phai 10
    assert terms["ô tô điện"]["docs"] == [6, 6], terms["ô tô điện"]
    print("[PASS] bai khong nhac nhom -> khong tinh vao mau so")


def test_bai_dung_ca_hai_bien_the_chi_bo_mot_phieu():
    """Bai dung ca 2 bien the van chi bo 1 phieu, cho ben dung NHIEU hon.

    Neu dem theo "co xuat hien hay khong" thi tong phieu vuot qua so bai.
    """
    docs = [{"sample_id": f"B-{i:03d}", "title": "Tiêu đề bài",
             "text": "ô tô điện tốt. ô tô điện bền. xe hơi điện cũng được. bạn xem."}
            for i in range(10)]
    rules = analyze_corpus(docs, CANDIDATES)
    term = rules["terms"][0]
    assert term["standard"] == "ô tô điện", term
    assert term["docs"] == [10, 10], term      # 10 phieu / 10 bai, khong phai 20
    print("[PASS] bai dung ca 2 bien the chi bo 1 phieu")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_10_tren_10_sinh_quy_tac,
        test_9_tren_10_sinh_quy_tac,
        test_8_tren_10_khong_sinh_quy_tac,
        test_bien_the_0_lan_vao_danh_sach_loai,
        test_bien_the_co_xuat_hien_khong_vao_danh_sach_loai,
        test_dem_theo_bai_va_theo_lan_tach_rieng,
        test_xung_ho_chuan_rut_duoc,
        test_bai_khong_nhac_khong_tinh_vao_mau_so,
        test_bai_dung_ca_hai_bien_the_chi_bo_mot_phieu,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)

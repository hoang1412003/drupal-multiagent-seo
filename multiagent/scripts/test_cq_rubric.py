"""Test rubric CQ1-CQ8 (docs/rubrics.md muc 3). KHONG goi LLM.

Nguong doc tu config/scoring.yaml chu khong viet cung trong test - doi nguong
o config thi test van dung, va khong tao ban chep thu hai cua cung con so
(bai hoc no B4).

Chay: .venv\\Scripts\\python.exe scripts\\test_cq_rubric.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config  # noqa: E402
from agents import content_quality as cq  # noqa: E402

NG = config.load()["scoring"]
_hong = False


def check(ten, thuc, mong):
    global _hong
    ok = thuc == mong
    if not ok:
        _hong = True
    print(f"[{'PASS' if ok else 'FAIL'}] {ten}")
    if not ok:
        print(f"         mong {mong!r}, thuc {thuc!r}")


def _llm_rong(fields, ttf, hoi_cq8):
    return {"loi": [], "criteria": {}}


def _chay(fields, llm=_llm_rong):
    day_du = {"title": "Tieu de mau", "body": "<p>Noi dung.</p>", "summary": ""}
    day_du.update(fields)
    return cq.run(day_du, danh_gia_llm=llm)


def _muc(kq, ma):
    return next(c["level"] for c in kq["criteria"] if c["id"] == ma)


def _cau(n_tieng):
    """Mot cau dung n_tieng tieng, ket thuc bang dau cham VA MOT DAU CACH.

    HAI dieu bat buoc, deu do quy tac cua split_sentences:

    1. Dau cach sau dau cham - khong co thi "cau mot.Cau hai" bi coi la MOT
       cau ("dinh lien, chua het cau").
    2. VIET HOA chu dau - dau cham + khoang trang + chu THUONG bi coi la viet
       tat lot luoi ("TP. hcm"), khong phai ranh gioi cau.

    Thieu mot trong hai thi n cau noi lai thanh MOT cau dai, va test do vi ly
    do khong lien quan gi den dieu no dinh kiem."""
    return "Tu " + " ".join(["tu"] * (n_tieng - 1)) + ". "


# ------------------------------------------------------------- CQ3 / CQ4

def test_cq3_cau_qua_dai():
    dai = _cau(NG["long_sentence_words"] + 5)
    ngan = _cau(5)
    check("khong cau dai -> muc 2",
          _muc(_chay({"body": f"<p>{ngan * 3}</p>"}), "CQ3"), 2)
    check("2 cau dai -> muc 1",
          _muc(_chay({"body": f"<p>{dai}{dai}{ngan}</p>"}), "CQ3"), 1)
    check("3 cau dai -> muc 0",
          _muc(_chay({"body": f"<p>{dai}{dai}{dai}</p>"}), "CQ3"), 0)
    check("cau dung bang nguong KHONG tinh la dai",
          _muc(_chay({"body": "<p>" + _cau(NG["long_sentence_words"]) * 3 + "</p>"}),
               "CQ3"), 2)


def test_cq4_doan_qua_dai():
    n = NG["long_paragraph_sentences"]
    doan_dai = "<p>" + _cau(3) * (n + 1) + "</p>"
    doan_ok = "<p>" + _cau(3) * 2 + "</p>"
    check("khong doan dai -> muc 2", _muc(_chay({"body": doan_ok * 3}), "CQ4"), 2)
    check("2 doan dai -> muc 1",
          _muc(_chay({"body": doan_dai * 2 + doan_ok}), "CQ4"), 1)
    check("3 doan dai -> muc 0", _muc(_chay({"body": doan_dai * 3}), "CQ4"), 0)


# ------------------------------------------------------------------ CQ5

def test_cq5_cau_truc_heading():
    """Bai NGAN khong co h2 -> NA, khong phai muc 0.

    Rubric chi coi thieu h2 la loi khi bai dai hon nguong. Cho muc 0 voi bai
    ngan la phat oan; cho muc 2 la cong diem mien phi."""
    dai = "<p>" + _cau(10) * (NG["heading_required_words"] // 10 + 20) + "</p>"
    check("bai dai khong h2 -> muc 0", _muc(_chay({"body": dai}), "CQ5"), 0)
    check("bai ngan khong h2 -> NA",
          _muc(_chay({"body": "<p>Ngan gon.</p>"}), "CQ5"), None)
    check("co h2 dung thu tu -> muc 2",
          _muc(_chay({"body": "<h2>Muc</h2><h3>Con</h3><p>x.</p>"}), "CQ5"), 2)
    check("h3 truoc h2 -> muc 1",
          _muc(_chay({"body": "<h3>Con</h3><h2>Muc</h2><p>x.</p>"}), "CQ5"), 1)


# ------------------------------------------------------------------ CQ8

def test_cq8_summary():
    check("summary trong -> muc 0 (may chot)",
          _muc(_chay({"summary": ""}), "CQ8"), 0)

    da_hoi = []

    def llm(fields, ttf, hoi_cq8):
        da_hoi.append(hoi_cq8)
        return {"loi": [], "criteria": {}}

    _chay({"summary": "Tom tat co noi dung."}, llm)
    check("summary co -> CO hoi LLM", da_hoi[-1], True)
    da_hoi.clear()
    _chay({"summary": ""}, llm)
    check("summary trong -> KHONG hoi LLM ve CQ8", da_hoi[-1], False)


# ------------------------------------------------------------ CQ1 / CQ2

def test_cq12_may_dem_loi_chu_khong_phai_llm_cham_muc():
    """LLM liet ke loi, MAY dem va quy muc. Nguong nam o config."""
    def llm_n_loi(n):
        def f(fields, ttf, hoi_cq8):
            return {"loi": [{"ma": "CQ1", "field": "body",
                             "evidence": "Noi dung.", "suggestion": "sua"}
                            for _ in range(n)],
                    "criteria": {}}
        return f

    check("0 loi -> muc 2", _muc(_chay({}, llm_n_loi(0)), "CQ1"), 2)
    check("2 loi -> muc 1", _muc(_chay({}, llm_n_loi(2)), "CQ1"), 1)
    check("3 loi -> muc 0", _muc(_chay({}, llm_n_loi(3)), "CQ1"), 0)


def test_cq12_loai_trich_dan_bia():
    """Loi co `evidence` khong nam nguyen van trong bai -> KHONG dem.

    Khong co buoc nay thi LLM bia ba loi la day mot bai sach xuong muc 0."""
    def llm_bia(fields, ttf, hoi_cq8):
        # `_danh_gia_llm` that moi loc trich dan; stub nay mo phong dung no
        from text_utils import trich_dan_co_that
        tho = [{"ma": "CQ1", "field": "body", "evidence": ev, "suggestion": "x"}
               for ev in ("Noi dung.", "CAU NAY KHONG CO TRONG BAI", "abc xyz")]
        return {"loi": [d for d in tho
                        if trich_dan_co_that(d["evidence"], ttf)],
                "criteria": {}}

    kq = _chay({"body": "<p>Noi dung.</p>"}, llm_bia)
    check("2/3 trich dan bia bi loai -> con 1 loi -> muc 1",
          _muc(kq, "CQ1"), 1)


# ------------------------------------------------------------ LLM hong

def test_llm_hong_cac_ma_llm_thanh_na_khong_phai_2():
    """LLM hong -> CQ1/CQ2/CQ6/CQ7 la NA, KHONG phai muc 2.

    Muc 2 se la 'khong tim thay loi chinh ta nao' trong khi thuc ra chua ai
    di tim - dung loai diem mien phi rubrics.md muc 2.2 canh bao."""
    def llm_no(fields, ttf, hoi_cq8):
        raise RuntimeError("API down")

    kq = _chay({"body": "<p>" + _cau(5) * 3 + "</p>"}, llm_no)
    check("LLM hong -> van tra ket qua", kq is not None, True)
    for ma in ("CQ1", "CQ2", "CQ6", "CQ7"):
        check(f"LLM hong -> {ma} la NA", _muc(kq, ma), None)
    check("LLM hong -> CQ3 (may) van cham", _muc(kq, "CQ3"), 2)


def test_bai_rong_tra_none():
    check("bai rong -> None",
          cq.run({"title": "", "body": "", "summary": ""},
                 danh_gia_llm=_llm_rong), None)


if __name__ == "__main__":
    test_cq3_cau_qua_dai()
    test_cq4_doan_qua_dai()
    test_cq5_cau_truc_heading()
    test_cq8_summary()
    test_cq12_may_dem_loi_chu_khong_phai_llm_cham_muc()
    test_cq12_loai_trich_dan_bia()
    test_llm_hong_cac_ma_llm_thanh_na_khong_phai_2()
    test_bai_rong_tra_none()
    sys.exit(1 if _hong else 0)

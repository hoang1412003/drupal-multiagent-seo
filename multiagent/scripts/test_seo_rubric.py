"""Test rubric SEO1-SEO10 (docs/rubrics.md muc 4). KHONG goi LLM.

Chay: .venv\\Scripts\\python.exe scripts\\test_seo_rubric.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from agents import seo  # noqa: E402

_hong = False


def check(ten, thuc, mong):
    global _hong
    ok = thuc == mong
    if not ok:
        _hong = True
    print(f"[{'PASS' if ok else 'FAIL'}] {ten}")
    if not ok:
        print(f"         mong {mong!r}, thuc {thuc!r}")


def _llm_rong(fields, can_hoi):
    """Stub: LLM khong tra ma nao -> cac ma do thanh NA."""
    return {"main_keyword": "xe dien", "criteria": {}}


# Body mac dinh khac rong: `run()` tra None khi MOI field deu rong (bai rong,
# khong co gi de cham). Test tung tieu chi thi phai co it nhat mot field co
# noi dung, khong thi ta dang test nhanh "bai rong" chu khong test tieu chi.
_BODY_MAC_DINH = "<p>Noi dung mau de bai khong rong.</p>"


def _chay(fields, llm=_llm_rong):
    day_du = {"title": "", "body": _BODY_MAC_DINH, "meta_description": "",
              "url_alias": "", "image_alt": ""}
    day_du.update(fields)
    return seo.run(day_du, danh_gia_llm=llm)


def _muc(kq, ma):
    return next(c["level"] for c in kq["criteria"] if c["id"] == ma)


# ------------------------------------------------------------------ SEO1

def test_seo1_do_dai_title():
    """Nguong tu scoring.yaml: ly tuong 50-60, chap nhan 40-70."""
    check("title 55 ky tu -> muc 2", _muc(_chay({"title": "x" * 55}), "SEO1"), 2)
    check("title 45 ky tu -> muc 1", _muc(_chay({"title": "x" * 45}), "SEO1"), 1)
    check("title 65 ky tu -> muc 1", _muc(_chay({"title": "x" * 65}), "SEO1"), 1)
    check("title 39 ky tu -> muc 0", _muc(_chay({"title": "x" * 39}), "SEO1"), 0)
    check("title 71 ky tu -> muc 0", _muc(_chay({"title": "x" * 71}), "SEO1"), 0)
    check("title trong -> muc 0", _muc(_chay({"title": ""}), "SEO1"), 0)


# ------------------------------------------------------------------ SEO3

def test_seo3_meta():
    check("meta 150 ky tu -> muc 2",
          _muc(_chay({"meta_description": "x" * 150}), "SEO3"), 2)
    check("meta 200 ky tu -> muc 1",
          _muc(_chay({"meta_description": "x" * 200}), "SEO3"), 1)
    check("meta trong -> muc 0", _muc(_chay({"meta_description": ""}), "SEO3"), 0)


# ------------------------------------------------------------------ SEO5

def test_seo5_may_chot_muc_0():
    """May ket luan duoc muc 0 (trong / con dau) -> KHONG hoi LLM."""
    check("url trong -> muc 0", _muc(_chay({"url_alias": ""}), "SEO5"), 0)
    check("url con dau tieng Viet -> muc 0",
          _muc(_chay({"url_alias": "/vn_vi/hướng-dẫn-sạc"}), "SEO5"), 0)

    da_hoi = []

    def llm(fields, can_hoi):
        da_hoi.extend(can_hoi)
        return {"main_keyword": "", "criteria": {}}

    _chay({"url_alias": "/vn_vi/huong-dan-sac"}, llm)
    check("url sach -> CO hoi LLM", "SEO5" in da_hoi, True)
    da_hoi.clear()
    _chay({"url_alias": "/vn_vi/hướng-dẫn"}, llm)
    check("url con dau -> KHONG hoi LLM", "SEO5" in da_hoi, False)


# ------------------------------------------------------------------ SEO7

def test_seo7_do_dai_body():
    """Nguong: <300 tu = muc 0, 300-599 = muc 1, >=600 = muc 2."""
    check("body 250 tu -> muc 0", _muc(_chay({"body": "tu " * 250}), "SEO7"), 0)
    check("body 400 tu -> muc 1", _muc(_chay({"body": "tu " * 400}), "SEO7"), 1)
    check("body 700 tu -> muc 2", _muc(_chay({"body": "tu " * 700}), "SEO7"), 2)


# ------------------------------------------------------------------ SEO9

def test_seo9_anh():
    """Bai KHONG co anh -> NA, khong phai muc 2.

    Cho muc 2 la cong diem mien phi cho moi bai khong co anh (rubrics.md
    muc 2.2 - dung loi da sua o BV7)."""
    check("khong co anh -> NA", _muc(_chay({"image_alt": ""}), "SEO9"), None)
    check("co anh thieu alt -> muc 0",
          _muc(_chay({"image_alt": "Anh 1 trong bai: \nAnh 2 trong bai: mo ta"}),
               "SEO9"), 0)

    da_hoi = []

    def llm(fields, can_hoi):
        da_hoi.extend(can_hoi)
        return {"main_keyword": "", "criteria": {}}

    _chay({"image_alt": "Anh 1 trong bai: mo ta ro rang"}, llm)
    check("moi anh co alt -> CO hoi LLM (alt co dung khong)",
          "SEO9" in da_hoi, True)


# ----------------------------------------------------------------- SEO10

def test_seo10_internal_link():
    ba = '<a href="/a">1</a><a href="/b">2</a><a href="/c">3</a>'
    check("3 link -> muc 2", _muc(_chay({"body": ba}), "SEO10"), 2)
    check("2 link -> muc 1",
          _muc(_chay({"body": '<a href="/a">1</a><a href="/b">2</a>'}), "SEO10"), 1)
    check("0 link -> muc 0", _muc(_chay({"body": "<p>khong link</p>"}), "SEO10"), 0)
    check("the <a> khong co href KHONG tinh",
          _muc(_chay({"body": '<a name="x">y</a>'}), "SEO10"), 0)


# ------------------------------------------------- LLM hong / vuot quyen

def test_llm_hong_van_cham_duoc_phan_may():
    """LLM loi -> cac ma no phu trach thanh NA, KHONG phai 0.

    Bon tieu chi may cham van ra diem. Day la suy giam co kiem soat -
    architecture.md muc 6.4."""
    def llm_no(fields, can_hoi):
        raise RuntimeError("API down")

    kq = _chay({"title": "x" * 55, "body": "tu " * 700,
                "meta_description": "x" * 150}, llm_no)
    check("LLM hong -> van tra ket qua", kq is not None, True)
    check("LLM hong -> SEO2 la NA", _muc(kq, "SEO2"), None)
    check("LLM hong -> SEO1 (may) van cham", _muc(kq, "SEO1"), 2)
    check("LLM hong -> SEO7 (may) van cham", _muc(kq, "SEO7"), 2)


def test_llm_hong_ghi_unavailable_cho_ma_can_llm():
    """Coverage v2 phai biet ro ma nao chua danh gia duoc."""
    def llm_no(fields, can_hoi):
        raise RuntimeError("API down")

    kq = _chay({
        "url_alias": "/vn_vi/huong-dan-sac-xe-dien",
        "image_alt": "Anh 1 trong bai: xe dien dang sac tai nha",
    }, llm_no)
    unavailable = set(kq["unavailable_checks"])
    check("LLM hong -> SEO5 unavailable", "SEO5" in unavailable, True)
    check("LLM hong -> SEO9 unavailable", "SEO9" in unavailable, True)


def test_ma_may_da_chot_khong_bi_ghi_unavailable():
    """SEO5/SEO9 do may ket luan van la assessment hop le khi LLM hong."""
    def llm_no(fields, can_hoi):
        raise RuntimeError("API down")

    kq = _chay({"url_alias": "", "image_alt": ""}, llm_no)
    unavailable = set(kq["unavailable_checks"])
    check("URL trong do may chot -> SEO5 khong unavailable",
          "SEO5" in unavailable, False)
    check("Bai khong anh do may chot NA -> SEO9 khong unavailable",
          "SEO9" in unavailable, False)


def test_llm_khong_duoc_ha_muc_0_cho_ma_may_da_chot():
    """LLM tra muc 0 cho SEO5/SEO8/SEO9 -> keo ve 1.

    May moi la ben ket luan muc 0 cho ba ma nay (trong / khong h2 / thieu
    alt). LLM khong co tham quyen do; de nguyen thi no co the ha muc mot bai
    hop le xuong 0 chi vi doc khong ky."""
    def llm(fields, can_hoi):
        return {"main_keyword": "", "criteria": {
            "SEO5": {"id": "SEO5", "level": 0, "occurrences": [], "suggestion": "x"},
        }}

    # Tiem thang vao tu_llm qua danh_gia_llm that -> dung _danh_gia_llm that
    # thi khong test duoc, nen kiem o tang thap hon: goi _danh_gia_llm voi
    # call_agent gia.
    import agents.seo as m
    that = m.call_agent
    m.call_agent = lambda p, c, s: {
        "main_keyword": "xe",
        "criteria": [{"id": "SEO5", "muc": "0", "field": "url_alias",
                      "suggestion": "x"}],
    }
    try:
        kq = m._danh_gia_llm({"url_alias": "/vn_vi/huong-dan", "body": "",
                              "title": "", "meta_description": "",
                              "image_alt": ""}, ("SEO5",))
    finally:
        m.call_agent = that
    check("LLM cham SEO5 = 0 -> keo ve 1",
          kq["criteria"]["SEO5"]["level"], 1)


def test_bai_rong_tra_none():
    """MOI field rong -> None (CHUA cham duoc), khong phai 0 diem.

    Goi thang seo.run chu khong qua _chay, vi _chay co body mac dinh."""
    rong = {"title": "", "body": "", "meta_description": "",
            "url_alias": "", "image_alt": ""}
    check("bai rong -> None", seo.run(rong, danh_gia_llm=_llm_rong), None)


if __name__ == "__main__":
    test_seo1_do_dai_title()
    test_seo3_meta()
    test_seo5_may_chot_muc_0()
    test_seo7_do_dai_body()
    test_seo9_anh()
    test_seo10_internal_link()
    test_llm_hong_van_cham_duoc_phan_may()
    test_llm_hong_ghi_unavailable_cho_ma_can_llm()
    test_ma_may_da_chot_khong_bi_ghi_unavailable()
    test_llm_khong_duoc_ha_muc_0_cho_ma_may_da_chot()
    test_bai_rong_tra_none()
    sys.exit(1 if _hong else 0)

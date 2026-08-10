"""Khoa lai: agent va script gan nhan phai do bang CUNG MOT ham.

Vi sao co file nay. Truoc 2026-08-10 ton tai HAI ban `strip_html` - mot o
`src/text_utils.py` (agent dung), mot o `scripts/label_helper.py` (gan nhan
dung). Moi ban dung mot nua:

    text_utils    giai ma thuc the HTML (&gt;)     thieu: gop ". ."
    label_helper  gop dau cham nhan doi            thieu: giai ma entity

Do duoc tren 8 bai gold set: so cau lech toi 62 cau o G-007 (266 so voi 328,
tuc 23%). Chua gay hai vi rubric CQ3/CQ4 (dem cau dai) chua ton tai - nhung
chung sap ton tai, va luc do agent se dem khac nguoi gan nhan tren cung mot
bai.

Test nay chan viec ai do vo tinh dinh nghia lai mot ban rieng lan nua.

Chay: .venv\\Scripts\\python.exe scripts\\test_text_utils_dung_chung.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import label_helper  # noqa: E402
import text_utils  # noqa: E402

_hong = False


def check(ten, thuc, mong):
    global _hong
    ok = thuc == mong
    if not ok:
        _hong = True
    print(f"[{'PASS' if ok else 'FAIL'}] {ten}")
    if not ok:
        print(f"         mong : {mong!r}")
        print(f"         thuc : {thuc!r}")


def test_dung_chung_mot_ham():
    """Manh hon so sanh dau ra: so DANH TINH doi tuong.

    So dau ra tren vai chuoi mau thi mot ban chep y het van qua duoc, roi hai
    ban troi lech dan - dung cach chung da hong lan truoc. So `is` thi dinh
    nghia lai la do ngay."""
    for ten in ("strip_html", "split_sentences", "split_paragraphs"):
        check(f"label_helper.{ten} LA text_utils.{ten}",
              getattr(label_helper, ten) is getattr(text_utils, ten), True)
    check("label_helper.has_vietnamese_diacritics LA text_utils.co_dau_tieng_viet",
          label_helper.has_vietnamese_diacritics is text_utils.co_dau_tieng_viet,
          True)


def test_strip_html_lam_ca_hai_viec():
    """Ban gop phai co CA hai hanh vi, khong phai chon mot."""
    # 1. Giai ma thuc the HTML - thieu cai nay thi doan trich bang chung hien
    #    ra dang "&gt;&gt;&gt; Tim hieu them"
    check("giai ma &gt;", ">>>" in text_utils.strip_html("<p>&gt;&gt;&gt; Xem</p>"), True)
    check("giai ma &nbsp;", "\xa0" in text_utils.strip_html("a&nbsp;b"), True)

    # 2. Gop dau cham nhan doi - cau da ket thuc bang "." nam trong <p> thi
    #    </p> -> ".\n" tao ra "..", split_sentences dem thanh cau rong thua
    check("gop '..' thanh '.'", ".." in text_utils.strip_html("<p>Cau mot.</p>"), False)

    # 3. Hai viec do cung luc tren cung mot chuoi
    ra = text_utils.strip_html("<p>Cau mot.</p><p>&gt;&gt; Cau hai.</p>")
    check("lam ca hai cung luc", ".." not in ra and ">>" in ra, True)


def test_khong_lam_doi_ket_qua_gan_nhan():
    """Gop ham KHONG duoc lam doi so cau tren van ban that.

    Ban gop = ban cu cua label_helper + giai ma entity. Giai ma entity khong
    tao ranh gioi cau moi, nen so cau phai giu nguyen. Neu test nay do, nghia
    la viec gop da am tham doi ground truth cua gold set."""
    html = ("<h2>Tieu de</h2><p>Cau mot dai dai.</p>"
            "<p>&gt;&gt;&gt; Tim hieu them: bai khac.</p>"
            "<p>TP.HCM co nhieu tram sac. Gia 3.5 trieu dong.</p>")
    cau = text_utils.split_sentences(text_utils.strip_html(html))
    # 5 cau: (1) "Tieu de." - </h2> thanh mot cau rieng, dung y do; (2) "Cau
    # mot dai dai."; (3) ">>> Tim hieu them: bai khac."; (4) "TP.HCM co nhieu
    # tram sac." - KHONG cat o "TP."; (5) "Gia 3.5 trieu dong." - KHONG cat o
    # "3.5". Entity va dau cham nhan doi khong tao them cau nao.
    check("so cau tren mau co entity + viet tat + so thap phan", len(cau), 5)


def test_tach_cau_giu_quy_tac_tieng_viet():
    check("khong cat o so thap phan",
          len(text_utils.split_sentences("Gia 3.5 trieu dong.")), 1)
    check("khong cat o viet tat TP.",
          len(text_utils.split_sentences("Tram sac o TP.HCM rat nhieu.")), 1)
    check("van cat o dau cham that",
          len(text_utils.split_sentences("Cau mot. Cau hai.")), 2)


if __name__ == "__main__":
    test_dung_chung_mot_ham()
    test_strip_html_lam_ca_hai_viec()
    test_khong_lam_doi_ket_qua_gan_nhan()
    test_tach_cau_giu_quy_tac_tieng_viet()
    sys.exit(1 if _hong else 0)

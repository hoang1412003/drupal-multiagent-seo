"""Test bo kiem thu chuc nang functional-clean (technical-debt.md muc 8.6).

Chay: .venv\\Scripts\\python.exe scripts\\test_functional_clean.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import eval_calibration as ec  # noqa: E402
from eval_functional_clean import doc_mau_sach, thong_ke  # noqa: E402

_hong = False


def check(ten, thuc, mong):
    global _hong
    if thuc != mong:
        _hong = True
        print(f"[FAIL] {ten}: mong {mong!r}, thuc {thuc!r}")
    else:
        print(f"[PASS] {ten}")


def kiem(ten, dieu_kien, chi_tiet=""):
    global _hong
    if dieu_kien:
        print(f"[PASS] {ten}")
    else:
        _hong = True
        print(f"[FAIL] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


W = {"content_quality": 0.25, "seo": 0.20, "brand": 0.25, "compliance": 0.30}
NG = {"veto": 50, "nr": 50, "publish": 80}


def bai(cq, seo_, brand, cp, critical=False, so_issue=0):
    return {
        "diem": {"content_quality": cq, "seo": seo_, "brand": brand,
                 "compliance": cp},
        "co_critical": critical,
        "chi_tiet": {"content_quality": {"issues": [{}] * so_issue},
                     "seo": {"issues": []}, "brand": {"issues": []},
                     "compliance": {"flags": []}},
    }


# --- Ba chi so bat buoc cua muc 8.6 -------------------------------------
# `publish_rate`, `false_positive_articles`, `false_positive_issues`.
# MOI bai trong bo nay deu ky vong `publish`, nen bai nao KHONG ra publish
# la mot bao dong gia o muc BAI, va moi issue tim duoc la mot bao dong gia
# o muc ISSUE. Hai muc do khac nhau: mot bai co 5 issue nho van chi la MOT
# bai bi bao sai, nhung 5 lan lam phien nguoi viet.

kq = {
    "C-001": bai(95, 95, 95, 95, so_issue=0),      # publish, sach
    "C-002": bai(95, 95, 95, 95, so_issue=3),      # publish nhung co 3 issue
    "C-003": bai(60, 60, 60, 60, so_issue=2),      # final 60 -> needs_revision
    "C-004": bai(95, 95, 95, 95, critical=True),   # critical -> rejected
}
t = thong_ke(kq, NG, W)

check("publish_rate = 2/4", round(t["publish_rate"], 3), 0.5)
check("false_positive_articles = 2 bai khong ra publish",
      t["false_positive_articles"], 2)
check("false_positive_issues dem TAT CA issue tren moi bai",
      t["false_positive_issues"], 5)
check("dem theo tung quyet dinh", t["phan_bo"],
      {"publish": 2, "needs_revision": 1, "rejected": 1})

# Bo sach hoan toan -> khong bao dong gia nao.
t0 = thong_ke({"C-001": bai(95, 95, 95, 95)}, NG, W)
check("bo sach hoan toan -> publish_rate 1.0", t0["publish_rate"], 1.0)
check("bo sach hoan toan -> 0 false positive article",
      t0["false_positive_articles"], 0)
check("bo sach hoan toan -> 0 false positive issue",
      t0["false_positive_issues"], 0)


# --- cham_mot_bai(giu_chi_tiet=True) phai GIU danh sach issue -----------
# Vi sao can: ban mac dinh chi luu `co_critical` dang boolean, nen khi
# P-006a bi gan critical o E5 thi KHONG truy duoc flag nao sinh ra no ma
# khong cham lai (~$0,06). Bo functional-clean con phai DEM issue nen cang
# khong the mat du lieu do.

class _Gia:
    def __init__(self, ket): self.ket = ket
    def run(self, fields, **kw): return self.ket


that_cq, that_seo = ec.content_quality, ec.seo
that_brand, that_cp = ec.brand_voice, ec.compliance
try:
    ec.content_quality = _Gia({"score": 80, "issues": [{"type": "CQ1"}]})
    ec.seo = _Gia({"score": 90, "issues": []})
    ec.brand_voice = _Gia({"score": 85, "issues": []})
    ec.compliance = _Gia({"score": 70, "flags": [
        {"severity": "critical", "rule": "CP1 abc"}]})

    mac_dinh = ec.cham_mot_bai({})
    chi_tiet = ec.cham_mot_bai({}, giu_chi_tiet=True)
finally:
    ec.content_quality, ec.seo = that_cq, that_seo
    ec.brand_voice, ec.compliance = that_brand, that_cp

kiem("mac dinh KHONG giu chi tiet (E5 khong doi hanh vi)",
     "chi_tiet" not in mac_dinh, str(sorted(mac_dinh)))
kiem("giu_chi_tiet=True co danh sach issue",
     chi_tiet["chi_tiet"]["content_quality"]["issues"] == [{"type": "CQ1"}])
kiem("giu_chi_tiet=True giu duoc FLAG sinh ra co_critical",
     chi_tiet["chi_tiet"]["compliance"]["flags"][0]["rule"] == "CP1 abc",
     "day chinh la thu thieu khi chan doan P-006a")
check("diem va co_critical khong doi giua hai che do",
      (mac_dinh["diem"], mac_dinh["co_critical"]),
      (chi_tiet["diem"], chi_tiet["co_critical"]))


# --- doc_mau_sach() doc dung manifest -----------------------------------
mau = doc_mau_sach()
check("doc du 10 mau functional-clean", len(mau), 10)
kiem("moi mau ky vong publish",
     all(m["expected_label"] == "publish" for m in mau))
kiem("khong mau nao trung id voi gold set",
     not (set(m["sample_id"] for m in mau) & set(ec.gold_ids())),
     "functional-clean KHONG duoc lot vao E5/Kappa")

sys.exit(1 if _hong else 0)

"""Test k-fold cross-validation cho E6 (evaluation-plan.md muc 4.6.1).

Chay: .venv\\Scripts\\python.exe scripts\\test_eval_kfold.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from eval_calibration import quet, quyet_dinh  # noqa: E402
from eval_kfold import PUBLISH_CO_DINH, chay_cv, chia_fold, chon_nguong  # noqa: E402

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


def mau_gia():
    """10 mau tu 8 nguon: hai cap dung chung nguon.

    Bat chuoc dung cau truc gold set that - P-001a/P-001b, P-004a/P-004b,
    P-007a/P-007b moi cap la hai bien the cua CUNG mot bai goc.
    """
    r = []
    for i in range(1, 7):
        r.append({"sample_id": f"G-{i:03d}", "source_url": f"bai-{i}",
                  "label": "needs_revision" if i > 2 else "rejected"})
    for ten, nguon, nhan in [("P-001a", "bai-p1", "rejected"),
                             ("P-001b", "bai-p1", "rejected"),
                             ("P-004a", "bai-p4", "needs_revision"),
                             ("P-004b", "bai-p4", "needs_revision")]:
        r.append({"sample_id": ten, "source_url": nguon, "label": nhan})
    return r


# --- RANG BUOC NHOM: hai mau cung nguon KHONG BAO GIO tach doi ------------
# Vi sao day la test dau tien: tach doi la ro ri gan-trung-lap. Mo hinh hoc
# tren P-001a roi du doan P-001b - hai bai chi khac vai cau - se cho Kappa CV
# lac quan gia, va khong co assertion nao khac bat duoc dieu do.

folds = chia_fold(mau_gia(), so_fold=5, seed=20260816)
fold_cua = {sid: i for i, f in enumerate(folds) for sid in f}

check("P-001a va P-001b cung fold",
      fold_cua["P-001a"] == fold_cua["P-001b"], True)
check("P-004a va P-004b cung fold",
      fold_cua["P-004a"] == fold_cua["P-004b"], True)


# --- PHAN TANG: moi fold phai co ti le nhan tuong duong ------------------
# Fixture mo phong DUNG cau truc gold set that: 30 nhom / 33 mau,
# 10 rejected / 23 needs_revision, trong do 3 cap cung nguon co nhan LECH
# nhau (moi cap 1 rejected + 1 needs_revision - da kiem tren labels.csv).

def mau_nhu_that():
    r = []
    for i in range(1, 21):              # 20 gold-real: 3 rejected / 17 NR
        r.append({"sample_id": f"G-{i:03d}", "source_url": f"real-{i}",
                  "label": "rejected" if i <= 3 else "needs_revision"})
    don = [("P-002a", "rejected"), ("P-003a", "rejected"),
           ("P-005a", "rejected"), ("P-006a", "rejected"),
           ("P-008a", "needs_revision"), ("P-009a", "needs_revision"),
           ("P-010a", "needs_revision")]
    for sid, nhan in don:               # 7 pert don le: 4 rejected / 3 NR
        r.append({"sample_id": sid, "source_url": f"pert-{sid}", "label": nhan})
    for n in ("001", "004", "007"):     # 3 cap nhan lech nhau
        r.append({"sample_id": f"P-{n}a", "source_url": f"pert-{n}",
                  "label": "rejected"})
        r.append({"sample_id": f"P-{n}b", "source_url": f"pert-{n}",
                  "label": "needs_revision"})
    return r


that = mau_nhu_that()
nhan_cua = {m["sample_id"]: m["label"] for m in that}
f2 = chia_fold(that, so_fold=5, seed=20260816)

so_rejected = [sum(nhan_cua[s] == "rejected" for s in f) for f in f2]
so_nr = [sum(nhan_cua[s] == "needs_revision" for s in f) for f in f2]

# 10 rejected / 5 fold = DUNG 2 moi fold, khong co du dia lam tron.
check("moi fold co dung 2 rejected", so_rejected, [2] * 5)
# 23 needs_revision / 5 fold = 4,6 -> chi duoc phep la 4 hoac 5.
kiem("moi fold co 4 hoac 5 needs_revision",
     all(n in (4, 5) for n in so_nr), f"thuc te {so_nr}")


# --- QUY TAC PHA HOA -----------------------------------------------------
# Da DANG KY TRUOC (evaluation-plan.md muc 4.6.1): trong cac to hop cung dat
# Kappa lon nhat, chon to hop gan nhat voi TRUNG VI THEO TUNG THANH PHAN cua
# tap hoa; con hoa nua thi veto nho hon, roi nr nho hon.
#
# Vi sao phai co test: voi 441 to hop tren ~26 mau moi fold, hoa gan nhu chac
# chan xay ra. Khong khoa quy tac lai thi moi lan chay co the ra mot bo nguong
# khac nhau ma khong ai biet - va do la cho de chon con so thuan loi nhat.

def hang(veto, nr, kappa):
    return {"nguong": {"veto": veto, "nr": nr, "publish": 80}, "kappa": kappa}


# Tap hoa veto = [30, 32, 34, 36, 38] -> trung vi 34. nr deu 50.
bang_hoa = [hang(v, 50, 0.800) for v in (30, 32, 34, 36, 38)]
bang_hoa.append(hang(60, 60, 0.700))          # thua kem, phai bi bo qua
check("chon to hop gan trung vi cua tap hoa",
      chon_nguong(bang_hoa), {"veto": 34, "nr": 50, "publish": 80})

# Hoa ve khoang cach: trung vi veto cua [30, 34] la 32, hai ben deu cach 2.
check("hoa khoang cach -> lay veto nho hon",
      chon_nguong([hang(30, 50, 0.9), hang(34, 50, 0.9)]),
      {"veto": 30, "nr": 50, "publish": 80})

check("khong hoa -> lay dung to hop kappa cao nhat",
      chon_nguong([hang(30, 50, 0.7), hang(40, 60, 0.9), hang(50, 50, 0.8)]),
      {"veto": 40, "nr": 60, "publish": 80})


# --- CHAY CV: chot chan RO RI la assertion quan trong nhat ---------------
# Neu code vo tinh chon nguong tren CA 33 mau roi ap len tung fold thi Kappa
# CV se bang Kappa in-sample va E6 mat sach y nghia - ma khong co dau hieu
# nao nhin thay duoc tu ben ngoai. Test duoi day tinh LAI nguong cua fold 0
# bang duong doc lap va bat no phai trung.

W = {"content_quality": 0.25, "seo": 0.20, "brand": 0.25, "compliance": 0.30}

mau_cv = mau_nhu_that()
nhan = {m["sample_id"]: m["label"] for m in mau_cv}
folds_cv = chia_fold(mau_cv, so_fold=5, seed=20260816)


def ket_qua_gia(mau, fold0):
    """Diem gia CO CHU DICH lam ro ri lo ra neu no xay ra.

    Mau `rejected` NGOAI fold 0 co compliance 40, mau `needs_revision` co 68.
    Rieng mau `rejected` TRONG fold 0 duoc dat 66 - van la rejected nhung sat
    ngay duoi 68.

    Hoc tren 4 fold con lai (khong co fold 0): moi veto trong 42..68 deu tach
    hoan hao -> plateau rong.
    Hoc tren ca 33 mau (tuc RO RI): phai day veto len 68 moi bat duoc hai mau
    66 -> chi con mot gia tri.

    Nho vay hai duong cho hai nguong KHAC NHAU, va assertion moi phan biet
    duoc. Ban dau fixture dat diem "sach" nen ca hai duong ra cung nguong va
    test van xanh voi ban da co tinh lam ro ri - da kiem bang dot bien.

    Cac agent khac de 90 de `final_score` luon >= 82, khong bao gio cham
    nguong `nr` (30..70) - moi quyet dinh rejected deu do veto, khong lan lon
    hai duong.
    """
    ra = {}
    for m in mau:
        xau = m["label"] == "rejected"
        if xau:
            cp = 66 if m["sample_id"] in fold0 else 40
        else:
            cp = 68
        ra[m["sample_id"]] = {
            "diem": {"content_quality": 90, "seo": 90, "brand": 90,
                     "compliance": cp},
            "co_critical": False,
        }
    return ra


kq = ket_qua_gia(mau_cv, set(folds_cv[0]))

cv = chay_cv(kq, nhan, mau_cv, W, so_fold=5, seed=20260816)

kiem("moi mau co dung mot du doan out-of-fold",
     sorted(cv["du_doan_oof"]) == sorted(nhan),
     f"{len(cv['du_doan_oof'])} du doan / {len(nhan)} mau")

check("co du 5 bo nguong, moi fold mot bo", len(cv["nguong_tung_fold"]), 5)

# Duong doc lap: nguong cua fold 0 phai hoc tu 4 fold con lai, KHONG co fold 0.
train0 = {s: v for s, v in kq.items() if s not in set(folds_cv[0])}
bang0 = [r for r in quet(train0, nhan, W)
         if r["nguong"]["publish"] == PUBLISH_CO_DINH]
ng_sach = chon_nguong(bang0)

# Nguong neu HOC TREN CA 33 MAU - tuc ket qua cua ban bi ro ri.
bang_ro_ri = [r for r in quet(kq, nhan, W)
              if r["nguong"]["publish"] == PUBLISH_CO_DINH]
ng_ro_ri = chon_nguong(bang_ro_ri)

# Neu hai gia tri nay bang nhau thi fixture het kha nang phan biet va moi
# assertion duoi day thanh vo nghia - phai bao loi ngay, khong duoc im lang.
kiem("fixture phan biet duoc ro ri (hai nguong phai KHAC nhau)",
     ng_sach != ng_ro_ri, f"ca hai deu la {ng_sach}")

check("nguong fold 0 hoc tu 4 fold con lai (khong ro ri)",
      cv["nguong_tung_fold"][0], ng_sach)

# Du doan cua mot mau trong fold 0 phai dung DUNG bo nguong cua fold 0.
sid0 = folds_cv[0][0]
check(f"du doan {sid0} dung nguong cua fold 0",
      cv["du_doan_oof"][sid0],
      quyet_dinh(kq[sid0]["diem"], kq[sid0]["co_critical"], W,
                 cv["nguong_tung_fold"][0]))

kiem("chay lai cung seed cho ket qua y het",
     chay_cv(kq, nhan, mau_cv, W, so_fold=5, seed=20260816) == cv)

sys.exit(1 if _hong else 0)

"""E6 - k-fold cross-validation cho nguong quyet dinh.

Thiet ke da DANG KY TRUOC ngay 2026-08-16: evaluation-plan.md muc 4.6.1.
Khong doi tham so nao trong file nay sau khi da nhin ket qua.

Vi sao k-fold chu khong tach cung: gold set chi co 33 mau. Tach cung 20%
de lai tap kiem tra 7 mau, ma o co mau do mot du doan sai lam Kappa roi tu
1,00 xuong 0,588 - phep do thanh nhi phan. Gop du doan out-of-fold cho
Kappa tren ca 33 mau, mot loi chi keo xuong 0,926.
"""
import random
import statistics
from collections import Counter

# `publish_min` KHONG tham gia calibration: gold set co 0 mau `publish` nen
# nguong nay khong xac dinh duoc (technical-debt.md muc 6 va 8.2). Giu nguyen
# gia tri minh hoa dang co trong scoring.yaml va ghi ro trong bao cao la CHUA
# calibrate. Nho vay khong gian quet la 441 to hop (veto 21 x nr 21) chu khong
# phai 7.056 - bot mot bac tu do khong co du lieu de xac dinh.
PUBLISH_CO_DINH = 80


def chia_fold(mau: list[dict], so_fold: int = 5,
              seed: int = 20260816) -> list[list[str]]:
    """Chia mau thanh `so_fold` fold: CHIA THEO NHOM `source_url`, PHAN TANG nhan.

    Don vi chia la BAI GOC chu khong phai mau: 33 mau cua gold set chi den
    tu 30 nguon doc lap (P-001a/b, P-004a/b, P-007a/b moi cap chung mot bai
    goc). Hai bien the cung nguon roi vao train/test khac nhau la ro ri
    gan-trung-lap - mo hinh hoc tren ban nay roi du doan ban kia chi khac
    vai cau, cho Kappa CV lac quan gia ma khong assertion nao bat duoc.

    Nhom KHONG dong nghia mot nhan: ca ba cap cua gold set deu co nhan lech
    nhau (P-001a rejected / P-001b needs_revision, ...). Nen phan tang phai
    lam theo BANG DEM nhan cua tung nhom, khong phai theo "nhan cua nhom".

    Tham lam co dinh: xet nhom lon truoc (kho xep hon), moi nhom vao fold lam
    tong binh phuong do lech so voi muc tieu nho nhat. Khong ngau nhien o buoc
    chon fold - chi thu tu duyet nhom la ngau nhien theo seed.
    """
    nhom: dict[str, list[dict]] = {}
    for m in mau:
        nhom.setdefault(m["source_url"], []).append(m)

    khoa = sorted(nhom)                 # sap truoc de khong phu thuoc thu tu dau vao
    random.Random(seed).shuffle(khoa)
    khoa.sort(key=lambda k: -len(nhom[k]))   # sort on dinh: giu thu tu da xao

    tong = Counter(m["label"] for m in mau)
    dem = [Counter() for _ in range(so_fold)]
    folds: list[list[str]] = [[] for _ in range(so_fold)]

    for k in khoa:
        g = Counter(m["label"] for m in nhom[k])

        def mat_can_bang(i: int) -> float:
            """Phuong sai cong don cua so luong tung nhan GIUA CAC FOLD.

            Phai do tren toan bo cac fold, khong phai do lech cua rieng fold
            i so voi muc tieu: ban chi nhin mot fold lam greedy nhoi day fold
            0 toi muc tieu roi moi sang fold sau (do duoc: nhan bi don thanh
            [5,5,0,0,0]), vi fold da co san nhan do luon "gan muc tieu hon".
            """
            gia_lap = [Counter(d) for d in dem]
            gia_lap[i] += g
            ra = 0.0
            for nhan in tong:
                v = [gia_lap[j][nhan] for j in range(so_fold)]
                tb = sum(v) / so_fold
                ra += sum((x - tb) ** 2 for x in v)
            return ra

        # Pha hoa co dinh: it mau hon truoc, roi chi so fold nho hon. Khong
        # duoc dung random o day - hai lan chay cung seed phai ra y het.
        chon = min(range(so_fold),
                   key=lambda i: (mat_can_bang(i), len(folds[i]), i))
        folds[chon].extend(m["sample_id"] for m in nhom[k])
        dem[chon] += g

    return folds


def chon_nguong(bang: list[dict]) -> dict:
    """Chon MOT bo nguong tu bang da quet, theo quy tac pha hoa dang ky truoc.

    Quy tac (evaluation-plan.md muc 4.6.1, chot TRUOC khi nhin du lieu):
    trong cac to hop cung dat Kappa lon nhat, chon to hop gan nhat (Euclid
    tren (veto, nr)) voi TRUNG VI THEO TUNG THANH PHAN cua tap hoa; con hoa
    nua thi veto nho hon, roi nr nho hon.

    Vi sao khong lay dai dien dau bang: voi 441 to hop hieu dung tren ~26 mau
    moi fold, hoa gan nhu chac chan xay ra (du an da biet veto <= 33 la mot
    plateau vi diem Compliance thap nhat la 33,3). Lay phan tu dau phu thuoc
    thu tu duyet, tuc mot bac tu do khong ai kiem soat.

    Vi sao chon giua plateau: do la diem xa bien quyet dinh nhat, nen nhieu
    cham diem it co co hoi lat nhan. E1 do duoc sigma final_score = 1,60
    trong khi buoc quet la 2 - cung co, nen khoang cach toi bien la dai luong
    dang toi da hoa. Ly do nay phat bieu duoc ma KHONG nhac toi phan bo thu
    duoc (phep thu chong bay B9, technical-debt.md).
    """
    if not bang:
        raise ValueError("bang nguong rong")

    cao_nhat = max(r["kappa"] for r in bang)
    hoa = [r for r in bang if r["kappa"] == cao_nhat]

    tv_veto = statistics.median(r["nguong"]["veto"] for r in hoa)
    tv_nr = statistics.median(r["nguong"]["nr"] for r in hoa)

    def khoang_cach(r: dict) -> float:
        g = r["nguong"]
        return (g["veto"] - tv_veto) ** 2 + (g["nr"] - tv_nr) ** 2

    return min(hoa, key=lambda r: (khoang_cach(r), r["nguong"]["veto"],
                                   r["nguong"]["nr"]))["nguong"]


def chay_cv(ket_qua: dict, nhan_that: dict, mau: list[dict], w: dict,
            so_fold: int = 5, seed: int = 20260816) -> dict:
    """k-fold CV: moi fold hoc nguong tren cac fold KHAC, du doan fold cua no.

    Tra ve du doan out-of-fold cho TUNG mau, nguong ma tung fold chon, va
    Kappa tinh tren toan bo du doan out-of-fold gop lai.

    CHOT CHAN RO RI: `train` cua fold i duoc loc bo DUNG cac mau cua fold i
    truoc khi quet nguong. Neu quet tren ca 33 mau roi ap len tung fold thi
    Kappa CV se bang Kappa in-sample va E6 mat sach y nghia - ma nhin tu ben
    ngoai khong co dau hieu gi.

    `publish` khong tham gia calibration (gold set co 0 mau `publish`), nen
    bang quet duoc loc ve dung PUBLISH_CO_DINH thay vi de no thanh mot bac tu
    do thu ba - xem evaluation-plan.md muc 4.6.1.
    """
    from eval_calibration import cohen_kappa, quet, quyet_dinh

    folds = chia_fold(mau, so_fold=so_fold, seed=seed)

    du_doan: dict[str, str] = {}
    nguong_tung_fold: list[dict] = []

    for f in folds:
        giu = set(f)
        train = {s: v for s, v in ket_qua.items() if s not in giu}
        bang = [r for r in quet(train, nhan_that, w)
                if r["nguong"]["publish"] == PUBLISH_CO_DINH]
        ng = chon_nguong(bang)
        nguong_tung_fold.append(ng)
        for s in f:
            if s in ket_qua:
                du_doan[s] = quyet_dinh(ket_qua[s]["diem"],
                                        ket_qua[s]["co_critical"], w, ng)

    ids = sorted(du_doan)
    that = [nhan_that[s] for s in ids]
    dd = [du_doan[s] for s in ids]
    return {
        "kappa_cv": cohen_kappa(that, dd),
        "accuracy": sum(t == d for t, d in zip(that, dd)) / len(ids),
        "du_doan_oof": du_doan,
        "nguong_tung_fold": nguong_tung_fold,
    }

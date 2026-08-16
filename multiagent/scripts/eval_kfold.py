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


def doc_mau(labels_path: str | None = None) -> list[dict]:
    """Doc gold set thanh dang chia_fold() can: sample_id, source_url, label.

    Dung CHUNG `_gold_rows()` cua eval_calibration chu khong tu doc CSV:
    tap mau cua k-fold phai la DUNG tap ma E5 da cham. Lech mot mau la fold
    chua mau khong co diem (hoac bo sot mau co diem), va luc do Kappa CV voi
    Kappa in-sample tinh tren hai tap khac nhau - hai con so bao cao canh
    nhau khong con so duoc voi nhau.
    """
    from eval_calibration import LABELS, _gold_rows

    return [{"sample_id": r["sample_id"], "source_url": r["source_url"],
             "label": r["label"].strip()}
            for r in _gold_rows(labels_path or LABELS)]


def in_bao_cao(kq_e5: dict, mau: list[dict], w: dict,
               so_fold: int = 5, seed: int = 20260816) -> dict:
    """In hai con so canh nhau va bo nguong cua tung fold.

    Bao cao mot minh con so in-sample la giau dung thu E6 sinh ra de do:
    khoang cach giua hai con so CHINH LA muc selection bias cua viec lay max
    tren 441 to hop (evaluation-plan.md muc 4.6.1).
    """
    from eval_calibration import cohen_kappa, f1_theo_lop, quet, quyet_dinh

    nhan = {m["sample_id"]: m["label"] for m in mau}
    ids = sorted(s for s in kq_e5 if s in nhan)
    that = [nhan[s] for s in ids]

    bang = [r for r in quet(kq_e5, nhan, w)
            if r["nguong"]["publish"] == PUBLISH_CO_DINH]
    ng_in = chon_nguong(bang)
    dd_in = [quyet_dinh(kq_e5[s]["diem"], kq_e5[s]["co_critical"], w, ng_in)
             for s in ids]
    kappa_in = cohen_kappa(that, dd_in)

    cv = chay_cv(kq_e5, nhan, mau, w, so_fold=so_fold, seed=seed)
    folds = chia_fold(mau, so_fold=so_fold, seed=seed)

    print("=" * 78)
    print(f"E6 - k-fold CROSS-VALIDATION  ({len(ids)} mau, {so_fold} fold, "
          f"seed {seed})")
    print("=" * 78)
    print("Thiet ke dang ky truoc: evaluation-plan.md muc 4.6.1\n")

    print(f"{'fold':>5}{'mau':>5}{'rej':>5}{'nr':>4}   nguong chon (veto/nr)")
    for i, f in enumerate(folds):
        c = sum(nhan[s] == "rejected" for s in f)
        g = cv["nguong_tung_fold"][i]
        print(f"{i:>5}{len(f):>5}{c:>5}{len(f)-c:>4}   "
              f"veto={g['veto']:<3} nr={g['nr']}")

    veto_set = {g["veto"] for g in cv["nguong_tung_fold"]}
    nr_set = {g["nr"] for g in cv["nguong_tung_fold"]}
    print(f"\n  Do phan tan nguong giua cac fold: veto {sorted(veto_set)}, "
          f"nr {sorted(nr_set)}")
    print("  (phan tan manh = nguong KHONG xac dinh duoc tu du lieu nay)")

    print("\n" + "-" * 78)
    print(f"  Kappa in-sample (quet tren ca {len(ids)}, lay max)  = "
          f"{kappa_in:.3f}   <- LAC QUAN")
    print(f"  Kappa CV        ({len(cv['du_doan_oof'])} du doan out-of-fold) = "
          f"{cv['kappa_cv']:.3f}   <- tong quat hoa")
    print(f"  Khoang cach = {kappa_in - cv['kappa_cv']:+.3f}  "
          f"= muc selection bias cua viec lay max tren {len(bang)} to hop")
    print("-" * 78)
    print(f"\n  Accuracy in-sample {sum(t==d for t,d in zip(that,dd_in))/len(ids):.3f}"
          f"   |   Accuracy CV {cv['accuracy']:.3f}")
    print("  F1 CV  " + "  ".join(
        f"{l}={f1_theo_lop(that, [cv['du_doan_oof'][s] for s in ids], l):.2f}"
        for l in ("rejected", "needs_revision", "publish")))

    print(f"\n  Nguong in-sample (KHONG phai thu dem dung ngay): {ng_in}")
    print("  publish_min khong calibrate duoc (0 mau publish), giu nguyen "
          f"{PUBLISH_CO_DINH} va ghi ro la CHUA calibrate.")

    return {
        "so_fold": so_fold, "seed": seed,
        "kappa_in_sample": kappa_in,
        "kappa_cv": cv["kappa_cv"],
        "selection_bias": kappa_in - cv["kappa_cv"],
        "accuracy_cv": cv["accuracy"],
        "nguong_in_sample": ng_in,
        "nguong_tung_fold": cv["nguong_tung_fold"],
        "fold": {str(i): sorted(f) for i, f in enumerate(folds)},
        "du_doan_oof": cv["du_doan_oof"],
    }


if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src"))

    import config
    from eval_calibration import REPO, nap_ket_qua

    ap = argparse.ArgumentParser()
    ap.add_argument("--ket-qua", required=True,
                    help="file ket qua PHA 1 cua E5 (trong docs/evidence/)")
    ap.add_argument("--ra", default="e6_kfold.json")
    a = ap.parse_args()

    path = (a.ket_qua if os.path.isabs(a.ket_qua)
            else os.path.join(REPO, "docs", "evidence", a.ket_qua))

    tom_tat = in_bao_cao(nap_ket_qua(path), doc_mau(), config.load()["weights"])

    ra = os.path.join(REPO, "docs", "evidence", a.ra)
    with open(ra, "w", encoding="utf-8") as f:
        json.dump(tom_tat, f, ensure_ascii=False, indent=1)
    print(f"\nKet qua -> {ra}")

"""Bo kiem thu CHUC NANG tren bai sach (technical-debt.md muc 8.6).

Tra loi cau hoi ma gold set KHONG tra loi duoc: "AI co bao loi gia tren bai
sach khong?" - vi gold calibration co 0 mau `publish` (muc 6).

⚠️ BO NAY TACH BIET VOI GOLD SET. No kiem CO CHE, khong do MUC DONG THUAN:
khong tinh Kappa, khong tham gia calibration, khong duoc them vao labels.csv.
Do la ly do duy nhat khien thao tac "sua bai cho sach" hop le o day trong khi
muc 6 da BAC BO dung thao tac do voi gold set.

Chay (tu multiagent/):
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\eval_functional_clean.py
    ... --bao-cao     chi tinh lai chi so tren ket qua da co, KHONG goi LLM
"""
import csv
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(REPO, "docs", "functional-tests")
MANIFEST = os.path.join(THU_MUC, "clean_labels.csv")
BAI_DIR = os.path.join(THU_MUC, "clean")

# Nhung khoa chua danh sach loi trong ket qua agent. content_quality/seo/
# brand dung "issues", compliance dung "flags" - giong graph.ISSUE_LIST_KEYS.
KHOA_LOI = ("issues", "flags")


def doc_mau_sach(manifest: str = MANIFEST) -> list[dict]:
    with open(manifest, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("sample_id")]


def dem_loi(muc: dict) -> int:
    """Tong so issue/flag ma 4 agent bao tren MOT bai."""
    tong = 0
    for r in (muc.get("chi_tiet") or {}).values():
        if not isinstance(r, dict):
            continue
        for k in KHOA_LOI:
            tong += len(r.get(k) or [])
    return tong


def thong_ke(ket_qua: dict, nguong: dict, w: dict) -> dict:
    """Ba chi so bat buoc cua muc 8.6, bao cao RIENG voi gold set.

    Moi bai trong bo nay ky vong `publish`, nen:
      - `false_positive_articles` = so bai KHONG ra publish (bao dong gia
        o muc BAI - anh huong quyet dinh xuat ban)
      - `false_positive_issues`   = tong so issue tren MOI bai (bao dong gia
        o muc ISSUE - so lan lam phien nguoi viet)

    Hai muc do KHAC nhau va phai bao rieng: mot bai co 5 issue nho van chi
    la MOT bai bi chan, nhung la 5 lan nguoi viet phai doc va bac bo.
    """
    from eval_calibration import quyet_dinh

    ids = sorted(ket_qua)
    dd = {s: quyet_dinh(ket_qua[s]["diem"], ket_qua[s]["co_critical"], w,
                        nguong) for s in ids}
    so_publish = sum(1 for s in ids if dd[s] == "publish")
    phan_bo = {}
    for s in ids:
        phan_bo[dd[s]] = phan_bo.get(dd[s], 0) + 1
    return {
        "so_bai": len(ids),
        "publish_rate": so_publish / len(ids) if ids else 0.0,
        "false_positive_articles": len(ids) - so_publish,
        "false_positive_issues": sum(dem_loi(ket_qua[s]) for s in ids),
        "phan_bo": phan_bo,
        "du_doan": dd,
        "loi_theo_bai": {s: dem_loi(ket_qua[s]) for s in ids},
    }


def doc_bai_sach(sid: str) -> dict:
    from eval_calibration import _extract_image_alt
    from label_helper import parse_sample

    f = parse_sample(os.path.join(BAI_DIR, f"{sid}.txt"))
    body = f.get("body", "") or ""
    return {"title": f.get("title", "") or "", "body": body,
            "summary": f.get("summary", "") or "",
            "meta_description": f.get("meta_description", "") or "",
            "url_alias": f.get("url_alias", "") or "",
            "image_alt": _extract_image_alt({"relationships": {}}, body)}


def cham(path: str) -> dict:
    """Cham cac bai chua co trong file ket qua, luu sau moi bai (resumable).

    Dung chung `cham_mot_bai()` voi E5 chu khong chep lai vong lap 4 agent:
    chep la tao ban thu hai se troi lech khi them agent thu 5.
    """
    from eval_calibration import cham_mot_bai, nap_ket_qua, prompt_version

    pv = prompt_version()
    da_co = nap_ket_qua(path) if os.path.isfile(path) else {}
    mau = doc_mau_sach()
    for i, m in enumerate(mau, 1):
        sid = m["sample_id"]
        if sid in da_co:
            continue
        print(f"  [{i}/{len(mau)}] {sid} ...", flush=True)
        da_co[sid] = cham_mot_bai(doc_bai_sach(sid), giu_chi_tiet=True)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"prompt_version": pv}, **da_co}, f,
                      ensure_ascii=False, indent=1)
    return da_co


def in_bao_cao(ket_qua: dict, nguong: dict, w: dict) -> dict:
    t = thong_ke(ket_qua, nguong, w)
    print("=" * 78)
    print(f"BO KIEM THU CHUC NANG - BAI SACH  ({t['so_bai']} mau, ky vong publish)")
    print("=" * 78)
    print(f"Nguong dung: {nguong}\n")
    print(f"{'bai':8s}{'du doan':18s}{'so issue AI bao':>16s}")
    for s in sorted(t["du_doan"]):
        print(f"{s:8s}{t['du_doan'][s]:18s}{t['loi_theo_bai'][s]:>16d}")
    print("\n" + "-" * 78)
    print(f"  publish_rate             {t['publish_rate']:.3f}  "
          f"({t['so_bai'] - t['false_positive_articles']}/{t['so_bai']})")
    print(f"  false_positive_articles  {t['false_positive_articles']}"
          f"   (bai bi chan oan)")
    print(f"  false_positive_issues    {t['false_positive_issues']}"
          f"   (lan lam phien nguoi viet)")
    print(f"  phan bo quyet dinh       {t['phan_bo']}")
    print("-" * 78)
    print("\n⚠️  Bo nay KHONG tinh Kappa va KHONG tham gia calibration.")
    print("   Bao cao rieng, khong gop voi so lieu gold set.")
    return t


if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src"))

    import config

    ap = argparse.ArgumentParser()
    ap.add_argument("--ket-qua", default="functional_clean_ban4.json")
    ap.add_argument("--bao-cao", action="store_true",
                    help="chi tinh lai chi so, KHONG goi LLM")
    a = ap.parse_args()

    path = (a.ket_qua if os.path.isabs(a.ket_qua)
            else os.path.join(REPO, "docs", "evidence", a.ket_qua))

    if a.bao_cao:
        from eval_calibration import nap_ket_qua
        kq = nap_ket_qua(path)
    else:
        print("PHA 1 - cham bo bai sach (ton tien API, resumable)\n")
        kq = cham(path)
        tin = sum(u["input_tokens"] for v in kq.values() for u in v["usage"])
        tout = sum(u["output_tokens"] for v in kq.values() for u in v["usage"])
        print(f"\n  {len(kq)} bai | {tin:,} token vao, {tout:,} ra | "
              f"~${tin/1e6*1.0 + tout/1e6*5.0:.2f}\n")

    khoi = config.load()
    t = in_bao_cao(kq, {"veto": khoi["decision"]["compliance_veto_below"],
                        "nr": khoi["decision"]["needs_revision_min"],
                        "publish": khoi["decision"]["publish_min"]},
                   khoi["weights"])

    ra = os.path.join(REPO, "docs", "evidence", "functional_clean_chi_so.json")
    with open(ra, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=1)
    print(f"\nChi so -> {ra}")

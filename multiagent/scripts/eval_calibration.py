"""E5 - Calibration nguong quyet dinh tu gold set.

Giao thuc: architecture.md muc 8.2, evaluation-plan.md muc 4.5.

HAI PHA, tach roi vi ly do chi phi:

  PHA 1  cham 33 bai gold set MOT LAN, luu diem 4 agent  -> ~$2
  PHA 2  quet nguong tren ket qua da luu                 -> $0

Pha 2 mien phi vi Aggregator la HAM THUAN, khong goi LLM (architecture.md muc
6). Do chinh la loi ich cu the cua quyet dinh thiet ke do, dang neu khi bao ve.

Chay (tu multiagent/):
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\eval_calibration.py
    ... --bao-cao        chi quet nguong tren ket qua da co, KHONG goi LLM
"""
import argparse
import itertools
import json
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import ai_core
import config
from agents import brand_voice, compliance, content_quality, seo
from drupal_client import _extract_image_alt
from label_helper import parse_sample

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(_HERE, "..", ".."))
GOLD_DIR = os.path.join(REPO, "docs", "goldset", "raw")
LABELS = os.path.join(REPO, "docs", "goldset", "labels.csv")
KET_QUA = os.path.join(REPO, "docs", "evidence", "e5_sau_sua_cp3_cp4.json")

NHAN = ("rejected", "needs_revision", "publish")


def prompt_version() -> str:
    """Hash bo prompt dang dung. Phai phu CA fact_check, khong chi 4 agent.

    Cong thuc cu (evaluation-plan.md muc 3a ban 1-2) chi bam 4 system prompt,
    bo sot hai prompt cua CP3 nam trong fact_check.py - dung cho la noi B14
    duoc sua. Bo sot nghia la ban khoa co the khang dinh "cung mot bo" trong
    khi hanh vi cham diem da khac han.
    """
    import hashlib
    from agents import fact_check
    ps = {"brand_voice_bv6": brand_voice._BV6_PROMPT,
          "compliance": compliance._LLM_PROMPT,
          "content_quality": content_quality._LLM_PROMPT,
          "seo": seo._LLM_PROMPT,
          "fact_check_compare": fact_check._COMPARE_PROMPT,
          "fact_check_extract": fact_check._EXTRACT_PROMPT}
    h = hashlib.sha256()
    for k in sorted(ps):
        h.update(ps[k].encode())
    return h.hexdigest()[:16]


# ----------------------------------------------------------- PHA 1: cham

def doc_bai(sid: str) -> dict:
    f = parse_sample(os.path.join(GOLD_DIR, f"{sid}.txt"))
    body = f.get("body", "") or ""
    return {
        "title": f.get("title", "") or "",
        "body": body,
        "summary": f.get("summary", "") or "",
        "meta_description": f.get("meta_description", "") or "",
        "url_alias": f.get("url_alias", "") or "",
        "image_alt": _extract_image_alt({"relationships": {}}, body),
    }


def cham_mot_bai(fields: dict) -> dict:
    """4 agent -> diem + co flag critical khong.

    Luu ca `co_critical` vi quyet dinh phu thuoc no doc lap voi diem - khong
    luu thi pha 2 khong tai lap duoc quyen phu quyet.
    """
    ai_core.USAGE_LOG.clear()
    diem, co_critical = {}, False
    for ten, ham in (("content_quality", content_quality.run), ("seo", seo.run),
                     ("brand", brand_voice.run), ("compliance", compliance.run)):
        try:
            r = ham(fields)
        except Exception as e:
            print(f"      !! {ten}: {type(e).__name__}: {str(e)[:60]}")
            r = None
        diem[ten] = r["score"] if r else None
        if ten == "compliance" and r:
            co_critical = any(f.get("severity") == "critical"
                              for f in r.get("flags", []))
    return {"diem": diem, "co_critical": co_critical,
            "usage": list(ai_core.USAGE_LOG)}


def cham_gold_set(ket_qua_path: str) -> dict:
    """Cham cac bai chua co trong file ket qua, luu sau moi bai (resumable).

    Resume la thu tiet kiem tien that (chay lai tu dau ~$1,9) NHUNG cung la
    mot cai bay: neu code cham diem doi giua chung, file se tron diem cua hai
    ban code khac nhau ma khong ai nhin ra. Da xay ra that - lan chay E5 dau
    tien tim ra B14, sua xong thi file cu thanh vo nghia.

    Nen ghi `prompt_version` vao file va TU CHOI resume khi no lech.
    """
    pv = prompt_version()
    da_co, meta = {}, {}
    if os.path.isfile(ket_qua_path):
        with open(ket_qua_path, encoding="utf-8") as f:
            cu = json.load(f)
        meta = cu.pop("_meta", {})
        pv_cu = meta.get("prompt_version")
        if pv_cu and pv_cu != pv:
            raise SystemExit(
                f"\nDUNG LAI: {os.path.basename(ket_qua_path)} cham bang prompt "
                f"{pv_cu}, code hien tai la {pv}.\n"
                f"Tron hai ban se cho ket qua vo nghia. Chon mot:\n"
                f"  - doi ten file cu roi chay lai tu dau (~$1,9), hoac\n"
                f"  - --ket-qua <ten file moi>\n")
        da_co = cu

    ids = sorted(x[:-4] for x in os.listdir(GOLD_DIR) if x.endswith(".txt"))
    for i, sid in enumerate(ids, 1):
        if sid in da_co:
            continue
        print(f"  [{i}/{len(ids)}] {sid} ...", flush=True)
        da_co[sid] = cham_mot_bai(doc_bai(sid))
        os.makedirs(os.path.dirname(ket_qua_path), exist_ok=True)
        with open(ket_qua_path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"prompt_version": pv}, **da_co},
                      f, ensure_ascii=False, indent=1)
    return da_co


# ------------------------------------------------------- PHA 2: quet nguong

def quyet_dinh(diem: dict, co_critical: bool, w: dict, ng: dict) -> str:
    """Ban sao logic graph.aggregator_node, tham so hoa nguong.

    Chep lai thay vi goi thang aggregator_node vi ham do doc nguong tu config
    - quet nguong thi phai truyen vao duoc. `test_e5_khop_aggregator` khoa lai
    rang hai ban cho cung ket qua o nguong mac dinh.
    """
    if diem.get("compliance") is None:
        return "needs_revision"          # fail-safe, architecture.md muc 6.4
    co = {k: v for k, v in diem.items() if v is not None}
    final = sum(w[k] * v for k, v in co.items()) / sum(w[k] for k in co)
    if diem["compliance"] < ng["veto"] or co_critical:
        return "rejected"
    if final >= ng["publish"]:
        return "publish"
    if final >= ng["nr"]:
        return "needs_revision"
    return "rejected"


def cohen_kappa(a: list, b: list) -> float:
    """Cohen's Kappa cho 2 danh sach nhan cung do dai."""
    n = len(a)
    if n == 0:
        return 0.0
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def f1_theo_lop(that: list, du_doan: list, lop: str) -> float:
    tp = sum(t == lop and d == lop for t, d in zip(that, du_doan))
    fp = sum(t != lop and d == lop for t, d in zip(that, du_doan))
    fn = sum(t == lop and d != lop for t, d in zip(that, du_doan))
    if tp == 0:
        return 0.0
    p, r = tp / (tp + fp), tp / (tp + fn)
    return 2 * p * r / (p + r)


def doc_nhan() -> dict:
    import csv
    with open(LABELS, encoding="utf-8") as f:
        return {r["sample_id"]: r["label"].strip()
                for r in csv.DictReader(f) if r["label"].strip()}


def quet(ket_qua: dict, nhan_that: dict, w: dict) -> list:
    """Quet moi to hop nguong. Tra list ket qua da sap theo Kappa giam dan.

    Buoc nhay 2 diem theo architecture.md muc 8.2 - hop le vi E1 do duoc
    sigma final_score = 1,79 < 2 (evaluation-plan.md muc 4.1).
    """
    ids = [s for s in ket_qua if s in nhan_that]
    that = [nhan_that[s] for s in ids]
    ra = []
    for veto in range(30, 71, 2):
        for nr in range(30, 71, 2):
            for pub in range(70, 101, 2):
                if not (nr <= pub):
                    continue
                ng = {"veto": veto, "nr": nr, "publish": pub}
                dd = [quyet_dinh(ket_qua[s]["diem"], ket_qua[s]["co_critical"],
                                 w, ng) for s in ids]
                ra.append({
                    "nguong": ng,
                    "kappa": cohen_kappa(that, dd),
                    "accuracy": sum(t == d for t, d in zip(that, dd)) / len(ids),
                    "f1": {l: f1_theo_lop(that, dd, l) for l in NHAN},
                    "phan_bo": dict(Counter(dd)),
                })
    ra.sort(key=lambda x: (-x["kappa"], -x["accuracy"]))
    return ra


def in_bao_cao(ket_qua: dict, nhan_that: dict, w: dict, ng_hien_tai: dict):
    ids = [s for s in ket_qua if s in nhan_that]
    that = [nhan_that[s] for s in ids]
    print("=" * 78)
    print(f"E5 - CALIBRATION NGUONG   ({len(ids)} mau co nhan)")
    print("=" * 78)
    print("Phan bo nhan nguoi:", dict(Counter(that)))

    hien = quyet_dinh, None
    dd0 = [quyet_dinh(ket_qua[s]["diem"], ket_qua[s]["co_critical"], w,
                      ng_hien_tai) for s in ids]
    print(f"\n--- NGUONG HIEN TAI (chua calibrate): {ng_hien_tai} ---")
    print(f"  Kappa    {cohen_kappa(that, dd0):.3f}")
    print(f"  Accuracy {sum(t==d for t,d in zip(that,dd0))/len(ids):.3f}")
    print(f"  F1       " + "  ".join(f"{l}={f1_theo_lop(that,dd0,l):.2f}" for l in NHAN))
    print(f"  Du doan  {dict(Counter(dd0))}")

    bang = quet(ket_qua, nhan_that, w)
    print(f"\n--- QUET {len(bang)} TO HOP NGUONG, 10 bo tot nhat ---")
    print(f"{'veto':>5}{'nr':>5}{'pub':>5}{'kappa':>8}{'acc':>7}   F1 (rej/nr/pub)   du doan")
    for r in bang[:10]:
        g = r["nguong"]
        f1 = r["f1"]
        print(f"{g['veto']:>5}{g['nr']:>5}{g['publish']:>5}{r['kappa']:>8.3f}"
              f"{r['accuracy']:>7.3f}   "
              f"{f1['rejected']:.2f}/{f1['needs_revision']:.2f}/{f1['publish']:.2f}"
              f"      {r['phan_bo']}")
    return bang


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bao-cao", action="store_true",
                    help="chi quet nguong tren ket qua da co, KHONG goi LLM")
    ap.add_argument("--ket-qua", default=KET_QUA)
    a = ap.parse_args()

    path = (a.ket_qua if os.path.isabs(a.ket_qua)
            else os.path.join(REPO, "docs", "evidence", a.ket_qua))

    if a.bao_cao:
        with open(path, encoding="utf-8") as f:
            kq = json.load(f)
        meta = kq.pop("_meta", {})       # khong phai mot bai, dung de lan vao
        pv = prompt_version()
        if meta.get("prompt_version") not in (None, pv):
            print(f"!! CANH BAO: ket qua cham bang prompt "
                  f"{meta['prompt_version']}, code hien tai {pv}. "
                  f"Nguong quet ra chi ap dung cho ban CU.\n")
    else:
        t0 = time.monotonic()
        print("PHA 1 - cham gold set (ton tien API, resumable)\n")
        kq = cham_gold_set(path)
        tok_in = sum(u["input_tokens"] for v in kq.values() for u in v["usage"])
        tok_out = sum(u["output_tokens"] for v in kq.values() for u in v["usage"])
        print(f"\n  {len(kq)} bai | {tok_in:,} token vao, {tok_out:,} ra | "
              f"~${tok_in/1e6*1.0 + tok_out/1e6*5.0:.2f} | "
              f"{time.monotonic()-t0:.0f}s\n")

    khoi = config.load()
    bang = in_bao_cao(kq, doc_nhan(), khoi["weights"],
                      {"veto": khoi["decision"]["compliance_veto_below"],
                       "nr": khoi["decision"]["needs_revision_min"],
                       "publish": khoi["decision"]["publish_min"]})
    out = os.path.join(REPO, "docs", "evidence", "e5_quet_nguong.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bang[:50], f, ensure_ascii=False, indent=1)
    print(f"\n50 bo tot nhat -> {out}")

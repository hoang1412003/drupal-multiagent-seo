"""E1 - do do on dinh diem qua nhieu lan cham, va E4 - chi phi/do tre.

Cau hoi E1 tra loi: cham lai CUNG mot bai nhieu lan thi diem lech bao nhieu?

Vi sao quan trong: architecture.md muc 8.2 du kien calibrate nguong bang cach
quet tu 70 den 90 theo BUOC NHAY 2 DIEM. Neu diem dao dong lon hon 2 thi moi
nguong chon ra chi la nhieu - giong nhu do chieu cao bang thuoc sai so +-3cm
roi tranh luan nguong nen la 170 hay 172.

Tieu chi dat: sigma < 2 (evaluation-plan.md muc 4.1).

CHAY THANG TREN FILE, KHONG QUA DRUPAL. Ly do:
  - Fetch va Write-back la hai node TAT DINH, khong gay dao dong; toan bo dao
    dong den tu cac lan goi LLM, ma phan do giong het o ca hai duong.
  - 7 node trong Drupal co bai chi 8 tu ('test') va 12 tu ('Bao duong xe') -
    4 agent gan nhu khong co gi de lam, do tren do khong noi len dieu gi.
  - Cham 50 luot qua pipeline se ghi de 35 lan vao Drupal, xoa mat ket qua
    hien co va sinh 35 revision rac.
GIOI HAN phai neu khi bao cao: phep do nay khong bao gom dao dong cua
Fetch/Write-back. Hai node do tat dinh nen khong co gi de dao dong, nhung
day van la mot pham vi hep hon "toan pipeline".

Ket qua ghi TANG DAN vao docs/evidence/e1_stability_raw.json sau moi luot,
va script BO QUA cac luot da chay - dut giua chung thi chay lai la tiep tuc,
khong mat cong da lam.

Chay (tu multiagent/):
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\eval_stability.py
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\eval_stability.py --bao-cao
        (chi in bao cao tu ket qua da co, khong goi LLM)
    ... --ket-qua e1_stability_rubric.json
        (ghi sang file khac, de do lai sau khi doi cach cham ma KHONG de len
         so do cu - phep so sanh phuong sai o evaluation-plan.md muc 9 can
         giu duoc ca hai ban tren CUNG bo mau)
"""
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import ai_core
from agents import brand_voice, compliance, content_quality, seo
from graph import aggregator_node

from drupal_client import _extract_image_alt
from eval_calibration import prompt_version
from label_helper import parse_sample

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
GOLD_DIR = os.path.join(REPO_ROOT, "docs", "goldset", "raw")
KET_QUA = os.path.join(REPO_ROOT, "docs", "evidence", "e1_stability_raw.json")

# 10 bai dau cua tap GOLD. Chon tat dinh, khong boc ngau nhien, de chay lai
# cho ra cung tap mau. Dung bai gold set o day KHONG gay ro ri du lieu: E1 do
# do on dinh cua PHEP CHAM, khong dung nhan nao ca.
SAMPLES = [f"G-{i:03d}" for i in range(1, 11)]
SO_LAN = 5

# Gia Haiku 4.5, USD tren 1 trieu token (docs/evaluation-plan.md muc 4.4).
GIA_INPUT = 1.00
GIA_OUTPUT = 5.00

NGUONG_SIGMA = 2.0        # evaluation-plan.md muc 4.1


def doc_bai(sample_id: str) -> dict:
    """Doc mot bai gold set -> dict fields dung dang 4 agent nhan vao."""
    fields = parse_sample(os.path.join(GOLD_DIR, f"{sample_id}.txt"))
    return {
        "title": fields.get("title", ""),
        "body": fields.get("body", ""),
        "summary": fields.get("summary", ""),
        "meta_description": fields.get("meta_description", ""),
        "url_alias": fields.get("url_alias", ""),
        # Boc alt cua MOI anh trong body, DUNG ham ma production dung
        # (drupal_client._extract_image_alt). Truoc 2026-08-10 cho o day la
        # chuoi rong, nen SEO9 luon thanh NA va E1 do mot pipeline KHAC
        # production. Cac bai gold set khong co field anh dai dien rieng -
        # moi anh nam trong body (spec 2026-07-29 muc 3.3) - nen truyen
        # resource rong va de ham tu boc tu body.
        "image_alt": _extract_image_alt({"relationships": {}},
                                        fields.get("body", "")),
    }


def cham_mot_luot(fields: dict) -> dict:
    """Goi 4 agent + Aggregator mot lan. Tra ve diem tung agent + tong.

    Agent loi -> None, giong het cach graph.py xu ly, de Aggregator chay
    nhanh fail-safe thay vi lam sap ca phep do.
    """
    ai_core.USAGE_LOG.clear()
    bat_dau = time.time()

    ket = {}
    for ten, ham in (
        ("content_quality", content_quality.run),
        ("seo", seo.run),
        ("brand", brand_voice.run),
        ("compliance", compliance.run),
    ):
        try:
            ket[ten] = ham(fields)
        except Exception as loi:
            print(f"      [loi] {ten}: {type(loi).__name__}: {loi}")
            ket[ten] = None

    state = {
        "node_id": "e1",
        "content_quality_result": ket["content_quality"],
        "seo_result": ket["seo"],
        "brand_result": ket["brand"],
        "compliance_result": ket["compliance"],
    }
    tong_hop = aggregator_node(state)
    giay = time.time() - bat_dau

    usage = list(ai_core.USAGE_LOG)
    return {
        "diem": {k: (v["score"] if isinstance(v, dict) else None) for k, v in ket.items()},
        "final_score": tong_hop["final_score"],
        "decision": tong_hop["decision"],
        "so_lan_goi_llm": len(usage),
        "input_tokens": sum(u["input_tokens"] for u in usage),
        "output_tokens": sum(u["output_tokens"] for u in usage),
        "giay": round(giay, 1),
    }


def nap_ket_qua(path: str | None = None) -> dict:
    path = path or KET_QUA
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        meta = data.pop("_meta", {})
        prompt_cu = meta.get("prompt_version")
        if prompt_cu != prompt_version():
            raise SystemExit(
                f"\nDUNG LAI: {os.path.basename(path)} khong dung prompt version "
                f"hien tai.\nTron hai ban se cho ket qua vo nghia. Chon mot:\n"
                f"  - doi ten file cu roi chay lai tu dau, hoac\n"
                f"  - --ket-qua <ten file moi>\n")
        return data
    return {}


def ghi_ket_qua(data: dict, path: str | None = None) -> None:
    path = path or KET_QUA
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {**data, "_meta": {"prompt_version": prompt_version()}}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def chay_do() -> dict:
    data = nap_ket_qua()
    for sample_id in SAMPLES:
        path = os.path.join(GOLD_DIR, f"{sample_id}.txt")
        if not os.path.isfile(path):
            print(f"{sample_id}: khong tim thay file, bo qua")
            continue
        fields = doc_bai(sample_id)
        data.setdefault(sample_id, [])
        for lan in range(len(data[sample_id]), SO_LAN):
            print(f"{sample_id} lan {lan + 1}/{SO_LAN} ...", flush=True)
            data[sample_id].append(cham_mot_luot(fields))
            ghi_ket_qua(data)       # ghi sau MOI luot de dut giua chung khong mat
    return data


def _sigma(xs: list) -> "float | None":
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


def in_bao_cao(data: dict) -> None:
    ten_agent = ["content_quality", "seo", "brand", "compliance"]

    print()
    print("=" * 76)
    print("E1 - DO ON DINH DIEM")
    print("=" * 76)
    print(f"{'Bai':<8}{'CQ':<14}{'SEO':<14}{'Brand':<14}{'Compliance':<14}{'Tong'}")
    print(f"{'':8}{'tb (sigma)':<14}{'tb (sigma)':<14}{'tb (sigma)':<14}{'tb (sigma)':<14}{'tb (sigma)'}")
    print("-" * 76)

    sigma_theo_agent = {a: [] for a in ten_agent}
    sigma_tong, quyet_dinh_dong_nhat = [], []

    for sample_id, cac_luot in sorted(data.items()):
        if not cac_luot:
            continue
        dong = f"{sample_id:<8}"
        for a in ten_agent:
            xs = [l["diem"][a] for l in cac_luot]
            tb = statistics.mean([x for x in xs if x is not None]) if any(x is not None for x in xs) else None
            sd = _sigma(xs)
            if sd is not None:
                sigma_theo_agent[a].append(sd)
            dong += f"{(f'{tb:.1f} ({sd:.2f})' if tb is not None and sd is not None else '-'):<14}"
        # Loc None truoc khi tinh: mot luot co the khong co final_score (agent
        # Compliance loi -> Aggregator tra None theo fail-safe muc 6.4), va
        # ca bai co the khong con luot nao dung duoc.
        fs = [l["final_score"] for l in cac_luot if l["final_score"] is not None]
        sd_tong = _sigma(fs)
        if sd_tong is not None:
            sigma_tong.append(sd_tong)
        if fs:
            tb_tong = statistics.mean(fs)
            dong += f"{tb_tong:.2f} ({sd_tong:.2f})" if sd_tong is not None else f"{tb_tong:.2f} (-)"
        else:
            dong += "-"
        print(dong)

        qd = [l["decision"] for l in cac_luot if l["decision"] is not None]
        if qd:
            quyet_dinh_dong_nhat.append(qd.count(max(set(qd), key=qd.count)) / len(qd))

    print("-" * 76)
    print()
    print("SIGMA TRUNG BINH THEO AGENT (nguong dat: < 2.0)")
    for a in ten_agent:
        ds = sigma_theo_agent[a]
        if not ds:
            print(f"  {a:<18} (khong du du lieu)")
            continue
        tb = statistics.mean(ds)
        print(f"  {a:<18} {tb:.2f}   max {max(ds):.2f}   {'DAT' if tb < NGUONG_SIGMA else 'KHONG DAT'}")

    if sigma_tong:
        tb = statistics.mean(sigma_tong)
        print()
        print(f"  {'final_score':<18} {tb:.2f}   max {max(sigma_tong):.2f}   "
              f"{'DAT' if tb < NGUONG_SIGMA else 'KHONG DAT'}")

    if quyet_dinh_dong_nhat:
        print()
        print(f"  Ti le lan cham ra CUNG mot decision: {statistics.mean(quyet_dinh_dong_nhat):.0%}")

    # --- E4 -----------------------------------------------------------
    moi_luot = [l for ds in data.values() for l in ds]
    if not moi_luot:
        return
    tin = sum(l["input_tokens"] for l in moi_luot)
    tout = sum(l["output_tokens"] for l in moi_luot)
    chi_phi = tin / 1e6 * GIA_INPUT + tout / 1e6 * GIA_OUTPUT

    print()
    print("=" * 76)
    print("E4 - CHI PHI VA DO TRE")
    print("=" * 76)
    print(f"  So luot cham            : {len(moi_luot)}")
    print(f"  So lan goi LLM / luot   : {statistics.mean([l['so_lan_goi_llm'] for l in moi_luot]):.1f}")
    print(f"  Input token / luot      : {tin / len(moi_luot):,.0f}")
    print(f"  Output token / luot     : {tout / len(moi_luot):,.0f}")
    print(f"  Chi phi / luot          : ${chi_phi / len(moi_luot):.4f}")
    print(f"  Chi phi toan bo phep do : ${chi_phi:.2f}")
    print(f"  Do tre / luot           : {statistics.mean([l['giay'] for l in moi_luot]):.1f} giay")
    print()
    print("  Luu y: do tre do la 4 agent chay TUAN TU trong script nay.")
    print("  Pipeline that (graph.py) chay 4 agent SONG SONG nen nhanh hon.")


if __name__ == "__main__":
    if "--ket-qua" in sys.argv:
        KET_QUA = os.path.join(REPO_ROOT, "docs", "evidence",
                               sys.argv[sys.argv.index("--ket-qua") + 1])
    if "--bao-cao" in sys.argv:
        in_bao_cao(nap_ket_qua())
    else:
        in_bao_cao(chay_do())
        print()
        print(f"Ket qua tho: {KET_QUA}")

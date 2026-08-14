"""Chay mot nhom test offline, bao cao that tha.

Vi sao can: truoc day moi nguoi tu go tung file, nen "chay het test" nghia la
khac nhau voi moi nguoi va khong ai biet co file nao bi bo quen. Runner nay
doi chieu manifest voi thu muc that va BAO LOI neu lech - khong file nao duoc
im lang bo qua.

Ba nguyen tac bao cao:
1. `[SKIP]` KHONG phai `[PASS]`. Test skip vi thieu dich vu se lam job that bai
   theo chinh sach, khong bao xanh gia.
2. Khong bao gio chay script goi API tra phi (`eval_*`, `smoke_test_*`, ...).
3. Xoa ANTHROPIC_API_KEY khoi moi truong con: chay nham cung khong tieu duoc tien.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe scripts\\run_test_group.py pure
    .venv\\Scripts\\python.exe scripts\\run_test_group.py postgres
    .venv\\Scripts\\python.exe scripts\\run_test_group.py all-offline
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


SCRIPTS = Path(__file__).resolve().parent
MULTIAGENT = SCRIPTS.parent
MANIFEST = SCRIPTS / "test_groups.json"
TIMEOUT_GIAY = 300

# Script goi API tra phi hoac chay pipeline that - TUYET DOI khong dua vao
# runner tu dong.
CAM_CHAY = ("eval_", "smoke_test_", "run_all_samples", "seed_")


class ManifestError(RuntimeError):
    pass


def doc_manifest(duong_dan: Path = MANIFEST) -> dict:
    return json.loads(duong_dan.read_text(encoding="utf-8"))


def kiem_manifest(manifest: dict, thu_muc: Path = SCRIPTS) -> None:
    """Manifest phai phu DUNG va DU cac file test co that."""
    khai_bao = []
    for ten_nhom, nhom in manifest["nhom"].items():
        khai_bao.extend(nhom["files"])

    # Kiem script tra phi TRUOC TIEN. Neu de sau, mot ten nhu `eval_stability.py`
    # se bi bao "file khong ton tai" (vi glob chi quet `test_*.py`) va thong
    # bao do che mat van de that: co nguoi dang dinh cho script tra phi chay
    # tu dong.
    tra_phi = [ten for ten in khai_bao if ten.startswith(CAM_CHAY)]
    if tra_phi:
        raise ManifestError(f"script tra phi khong duoc vao nhom: {sorted(tra_phi)}")

    trung = {ten for ten in khai_bao if khai_bao.count(ten) > 1}
    if trung:
        raise ManifestError(f"file khai bao o nhieu nhom: {sorted(trung)}")

    tren_dia = {p.name for p in thu_muc.glob("test_*.py")}
    khai_bao_set = set(khai_bao)

    thieu = tren_dia - khai_bao_set
    if thieu:
        raise ManifestError(
            f"co file test chua duoc xep nhom: {sorted(thieu)}. "
            "Them vao test_groups.json, dung de no bi bo quen."
        )
    thua = khai_bao_set - tren_dia
    if thua:
        raise ManifestError(f"manifest khai bao file khong ton tai: {sorted(thua)}")


def moi_truong_con() -> dict:
    moi_truong = dict(os.environ)
    moi_truong["HF_HUB_OFFLINE"] = "1"
    moi_truong["VF_ALLOW_PAID_EVAL"] = "0"
    moi_truong["PYTHONIOENCODING"] = "utf-8"
    # Xoa han key: chay nham mot script tra phi cung khong tieu duoc tien.
    moi_truong.pop("ANTHROPIC_API_KEY", None)
    return moi_truong


def chay_mot_file(ten: str) -> dict:
    bat_dau = time.monotonic()
    try:
        ket_qua = subprocess.run(
            [sys.executable, str(SCRIPTS / ten)],
            cwd=str(MULTIAGENT),
            env=moi_truong_con(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_GIAY,
        )
        dau_ra = (ket_qua.stdout or "") + (ket_qua.stderr or "")
        ma = ket_qua.returncode
        het_gio = False
    except subprocess.TimeoutExpired:
        dau_ra, ma, het_gio = "", 1, True

    return {
        "file": ten,
        "exit": ma,
        "giay": round(time.monotonic() - bat_dau, 2),
        "het_gio": het_gio,
        # Chi dem dong BAT DAU bang nhan, khong dem chuoi con o giua dong: mot
        # test hop le co the NHAC toi "[SKIP]" trong chinh thong bao [PASS] cua
        # no, va dem chuoi con se bao nham la co test bi bo qua.
        "so_skip": _dem_nhan(dau_ra, "[SKIP]"),
        "so_fail": _dem_nhan(dau_ra, "[FAIL]"),
        "dau_ra": dau_ra,
    }


def _dem_nhan(dau_ra: str, nhan: str) -> int:
    return sum(1 for dong in dau_ra.splitlines() if dong.lstrip().startswith(nhan))


def chay_nhom(ten_nhom: str, manifest: dict) -> list:
    return [chay_mot_file(ten) for ten in manifest["nhom"][ten_nhom]["files"]]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Chay mot nhom test offline")
    parser.add_argument("nhom", choices=["pure", "postgres", "all-offline"])
    parser.add_argument(
        "--cho-phep-skip",
        action="store_true",
        help="Coi [SKIP] la chap nhan duoc. CI KHONG duoc dung co nay.",
    )
    args = parser.parse_args(argv)

    manifest = doc_manifest()
    try:
        kiem_manifest(manifest)
    except ManifestError as exc:
        print(f"[LOI MANIFEST] {exc}", file=sys.stderr)
        return 2

    ten_nhom = ["pure", "postgres"] if args.nhom == "all-offline" else [args.nhom]
    ket_qua = []
    for nhom in ten_nhom:
        print(f"\n=== NHOM {nhom} ({len(manifest['nhom'][nhom]['files'])} file) ===")
        for item in chay_nhom(nhom, manifest):
            ket_qua.append({**item, "nhom": nhom})
            nhan = "OK  "
            if item["exit"] != 0 or item["het_gio"]:
                nhan = "FAIL"
            elif item["so_skip"]:
                nhan = "SKIP"
            print(f"  [{nhan}] {item['file']:<45} {item['giay']:>6.2f}s")
            if nhan == "FAIL":
                for dong in item["dau_ra"].splitlines():
                    if "[FAIL]" in dong or "Error" in dong:
                        print(f"         {dong}")

    hong = [r for r in ket_qua if r["exit"] != 0 or r["het_gio"]]
    bo_qua = [r for r in ket_qua if r["so_skip"] and r["exit"] == 0]

    print("\n=== TOM TAT ===")
    print(f"  tong: {len(ket_qua)}   hong: {len(hong)}   co [SKIP]: {len(bo_qua)}")
    for r in hong:
        ly_do = "het gio" if r["het_gio"] else f"exit {r['exit']}"
        print(f"  HONG {r['file']} ({ly_do})")
    for r in bo_qua:
        print(f"  SKIP {r['file']} - [SKIP] KHONG phai [PASS]")

    # JSON summary: chi lenh/thoi gian/trang thai, khong dump moi truong.
    tom_tat = {
        "nhom": args.nhom,
        "tong": len(ket_qua),
        "hong": len(hong),
        "co_skip": len(bo_qua),
        "chi_tiet": [
            {k: r[k] for k in ("nhom", "file", "exit", "giay", "so_skip", "so_fail")}
            for r in ket_qua
        ],
    }
    (MULTIAGENT / "test_group_summary.json").write_text(
        json.dumps(tom_tat, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if hong:
        return 1
    if bo_qua and not args.cho_phep_skip:
        print("\n[LOI] co test bi SKIP. Thieu dich vu thi phai sua moi truong, "
              "khong duoc coi la dat.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

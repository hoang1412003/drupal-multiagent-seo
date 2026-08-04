"""So sanh phuong sai diem giua HAI cach cham, tren CUNG bo mau.

Day la phep do cuoi cung con de trong o docs/rubrics.md muc 9: "Rubric co
that su on dinh hon thang 0-100 khong". Rubric duoc thiet ke theo LAP LUAN;
truoc script nay chua co so lieu nao chung minh no tot hon.

Doc hai file ket qua tho do scripts/eval_stability.py sinh ra, chi so sanh
tren cac bai VA cac agent co du du lieu o CA HAI file - so tren tap khac nhau
thi chenh lech do doi mau chu khong phai do doi cach cham.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe scripts\\so_sanh_phuong_sai.py \\
        e1_stability_raw.json e1_stability_rubric.json
"""
import json
import os
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
EVIDENCE = os.path.normpath(os.path.join(_HERE, "..", "..", "docs", "evidence"))

AGENTS = ["content_quality", "seo", "brand", "compliance"]


def nap(ten: str) -> dict:
    with open(os.path.join(EVIDENCE, ten), encoding="utf-8") as f:
        return json.load(f)


def _sigma(xs: list):
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


def _diem(luot: list, agent: str) -> list:
    return [l["diem"][agent] for l in luot]


def in_bang(cu: dict, moi: dict, ten_cu: str, ten_moi: str) -> None:
    chung = sorted(set(cu) & set(moi))
    if not chung:
        print("Khong co bai nao co o ca hai file - khong so sanh duoc.")
        return

    print(f"Cu : {ten_cu}")
    print(f"Moi: {ten_moi}")
    print(f"Bai co o ca hai file: {len(chung)} ({', '.join(chung)})")
    print()

    for agent in AGENTS:
        sig_cu, sig_moi, doi_diem = [], [], []
        for bai in chung:
            a, b = _sigma(_diem(cu[bai], agent)), _sigma(_diem(moi[bai], agent))
            if a is None or b is None:
                continue
            sig_cu.append(a)
            sig_moi.append(b)
            tb_cu = statistics.mean([x for x in _diem(cu[bai], agent) if x is not None])
            tb_moi = statistics.mean([x for x in _diem(moi[bai], agent) if x is not None])
            doi_diem.append(tb_moi - tb_cu)
        if not sig_cu:
            print(f"{agent:<18} (khong du du lieu o ca hai file)")
            continue
        tb_cu_s, tb_moi_s = statistics.mean(sig_cu), statistics.mean(sig_moi)
        huong = "GIAM" if tb_moi_s < tb_cu_s else ("TANG" if tb_moi_s > tb_cu_s else "=")
        print(f"{agent:<18} sigma {tb_cu_s:5.2f} -> {tb_moi_s:5.2f}  {huong:<5} "
              f"(max {max(sig_cu):.2f} -> {max(sig_moi):.2f}; "
              f"diem trung binh doi {statistics.mean(doi_diem):+.1f})")

    # final_score
    sig_cu, sig_moi = [], []
    for bai in chung:
        a = _sigma([l["final_score"] for l in cu[bai]])
        b = _sigma([l["final_score"] for l in moi[bai]])
        if a is not None and b is not None:
            sig_cu.append(a)
            sig_moi.append(b)
    if sig_cu:
        print()
        tb_cu_s, tb_moi_s = statistics.mean(sig_cu), statistics.mean(sig_moi)
        huong = "GIAM" if tb_moi_s < tb_cu_s else ("TANG" if tb_moi_s > tb_cu_s else "=")
        print(f"{'final_score':<18} sigma {tb_cu_s:5.2f} -> {tb_moi_s:5.2f}  {huong:<5} "
              f"(max {max(sig_cu):.2f} -> {max(sig_moi):.2f})")

    print()
    print("Luu y khi doc: sigma nho hon KHONG tu dong nghia la tot hon. Mot bo")
    print("tieu chi luon tra cung mot muc sai cung se co sigma = 0. Phep do nay")
    print("chi tra loi 'co tai lap duoc khong', khong tra loi 'co dung khong' -")
    print("cau hoi do thuoc ve E5 va can gold set da gan nhan.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    in_bang(nap(sys.argv[1]), nap(sys.argv[2]), sys.argv[1], sys.argv[2])

"""E2 cho KB brand: truy xuat co lay dung doan CUNG CHU DE khong.

Vi sao KHONG dung recall@k kieu fact-check: fact-check co dung mot chunk dung
(thong so VF 8), con KB brand thi nhieu doan cung chu de deu hop le - khong
ton tai "mot dap an dung" (spec muc 6.4).

Cach do: lay title 20 bai GOLD lam truy van (da biet thuoc nhom chu de nao),
dem ti le doan trong top-3 den tu bai BRAND CUNG nhom. Ground truth lay san
tu docs/brand/corpus_index.csv va bang GOLD_TOPICS duoi day - khong phai soan
20 cap bang tay.

Moc so sanh: neu truy xuat vo dinh huong thi ti le se xap xi ti trong SO
CHUNK cua nhom do trong KB (khong phai ti trong so bai - cac bai dai gop
nhieu chunk hon). Cao hon han moc do nghia la truy xuat that su bam chu de.

Dung title bai GOLD lam truy van KHONG gay ro ri du lieu: chi muon tieu de de
do chat luong truy xuat, khong rut quy tac brand nao tu chung.

GIOI HAN CUA PHEP DO - con so thu duoc la CHAN DUOI, khong phai ti le that.
Ground truth chi cho MOT nhom chu de moi bai, trong khi nhieu bai thuoc ve
hai nhom. Kiem chung tren ket qua chay ngay 2026-08-03:

  G-002 "cham soc xe dien VF e34"  nhan lai_xe_an_toan, retrieval tra ve
        bao_duong_chi_phi -> tinh la TRUOT, nhung "cham soc xe" DUNG la
        bao duong; retrieval moi la ben dung.
  G-018 "tim tram sac bang App"    nhan tram_sac, retrieval tra ve ung_dung
        (dung cac doan noi ve "tim kiem tram sac bang app") -> tinh la
        TRUOT, nhung bai nay thuoc ca hai nhom.

KHONG sua nhan de "chua" cac ca nay: sua nhan sau khi da nhin ket qua la tu
tao thien vi. De nguyen va bao cao con so bi danh gia thap - lech ve huong
an toan.

Chay (tu multiagent/): .venv\\Scripts\\python.exe scripts\\eval_brand_retrieval.py
"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import db

from retrieval import COLLECTION_BRAND, retrieve

from label_helper import parse_sample

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
GOLD_DIR = os.path.join(REPO_ROOT, "docs", "goldset", "raw")

# Nhom chu de cua tung bai GOLD, chep tu docs/goldset/sources.md muc 1.1-1.5
# (cung he nhan voi docs/brand/corpus_index.csv).
GOLD_TOPICS = {
    "G-001": "lai_xe_an_toan", "G-002": "lai_xe_an_toan",
    "G-003": "lai_xe_an_toan", "G-004": "lai_xe_an_toan",
    "G-005": "sac_pin", "G-006": "sac_pin", "G-007": "sac_pin",
    "G-008": "sac_pin", "G-009": "sac_pin", "G-010": "sac_pin",
    "G-011": "bao_duong_chi_phi", "G-012": "bao_duong_chi_phi",
    "G-013": "bao_duong_chi_phi", "G-014": "bao_duong_chi_phi",
    "G-015": "bao_duong_chi_phi", "G-016": "bao_duong_chi_phi",
    "G-017": "tram_sac", "G-018": "tram_sac",
    "G-019": "ung_dung", "G-020": "ung_dung",
}
TOP_K = 3


def ti_trong_chunk() -> dict[str, float]:
    """Ti le SO CHUNK cua tung nhom = moc ngau nhien cua nhom do.

    Tinh theo chunk chu khong theo bai: mot bai dai gop hang tram chunk nen
    xac suat boc trung nhom cua no cao hon han, dung ti trong so bai lam moc
    se so lech.

    Tu 2026-08-05 dem bang GROUP BY thay vi keo toan bo metadata ve Python roi
    dem tay - mot vi du nho cua viec doi sang Postgres.
    """
    with db.get_conn().cursor() as cur:
        cur.execute(
            f"SELECT meta->>'topic_group', count(*) FROM {db.TEN_BANG} "
            "WHERE collection = %s GROUP BY 1",
            (COLLECTION_BRAND,),
        )
        dem = dict(cur.fetchall())
    tong = sum(dem.values())
    return {g: n / tong for g, n in dem.items()}


if __name__ == "__main__":
    moc = ti_trong_chunk()
    tong_trung, tong_doan, dong = 0, 0, []

    for sample_id, chu_de in sorted(GOLD_TOPICS.items()):
        path = os.path.join(GOLD_DIR, f"{sample_id}.txt")
        if not os.path.isfile(path):
            continue
        title = parse_sample(path).get("title", "")
        if not title:
            continue

        hits = retrieve(title, "cam_nang", "vi", top_k=TOP_K,
                        collection_name=COLLECTION_BRAND)
        trung = sum(1 for h in hits if h.get("topic_group") == chu_de)
        tong_trung += trung
        tong_doan += len(hits)
        dong.append((sample_id, chu_de, trung, len(hits), moc.get(chu_de, 0.0)))

    print(f"{'Bai':<8}{'Nhom chu de':<20}{'Trung/top-3':<14}{'Moc ngau nhien'}")
    print("-" * 62)
    for sample_id, chu_de, trung, n, m in dong:
        print(f"{sample_id:<8}{chu_de:<20}{trung}/{n:<12}{m:.0%}")

    if tong_doan:
        ti_le = tong_trung / tong_doan
        # Moc ngau nhien cua ca bo = trung binh co trong so theo so truy van
        moc_tb = sum(r[4] for r in dong) / len(dong)
        print("-" * 62)
        print(f"Ti le doan cung chu de   : {ti_le:.1%}  ({tong_trung}/{tong_doan})")
        print(f"Moc ngau nhien trung binh: {moc_tb:.1%}")
        print(f"Cao hon moc              : {ti_le / moc_tb:.1f} lan" if moc_tb else "")
        print(f"Ket luan: {'DAT' if ti_le > moc_tb * 1.5 else 'CAN XEM LAI'}")

        print()
        print("Chi tiet theo nhom chu de:")
        theo_nhom = collections.defaultdict(lambda: [0, 0])
        for _, chu_de, trung, n, _m in dong:
            theo_nhom[chu_de][0] += trung
            theo_nhom[chu_de][1] += n
        for chu_de, (t, n) in sorted(theo_nhom.items()):
            print(f"  {chu_de:<20} {t}/{n} = {t / n:.0%}   (moc {moc.get(chu_de, 0):.0%})")

        print()
        print("LUU Y: con so tren la CHAN DUOI. Ground truth chi cho mot nhom chu de")
        print("moi bai, nen bai thuoc hai nhom bi tinh la truot du retrieval tra ve")
        print("dung noi dung. Xem docstring dau file de biet vi du cu the.")

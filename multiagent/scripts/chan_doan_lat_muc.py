"""Chẩn đoán: tiêu chí nào của Compliance LẬT MỨC giữa các lần chấm?

VÌ SAO TỒN TẠI. E1 rubric v2 đo σ Compliance = 4,18 (docs/technical-debt.md
mục A1) nhưng không nói được σ đó từ tiêu chí nào ra. Hai file bằng chứng đã
có, mỗi file thiếu đúng một nửa:

  e1_stability_rubric_v2.json  chạy lặp 5 lượt  nhưng chỉ lưu điểm THEO AGENT
  cp_phan_bo_muc.txt           có mức từng tiêu chí  nhưng chạy 1 lượt/bài,
                               và đo trên rubric v1 - trước khi CP5/CP6/CP8
                               giao câu hỏi "có áp dụng không" cho máy

Ghép lại không được, nên phải đo lại: chạy LẶP và ghi mức TỪNG tiêu chí mỗi
lượt.

Ngoài ra ghi nhật ký mỗi lần `_hop_thuc_hoa` GHI ĐÈ mức LLM vừa chấm. Đó là
chỗ technical-debt.md B5 nghi ngờ: CP8 chấm mức 0/1 mà không trích dẫn được
nguyên văn thì bị đẩy lên mức 2 - điểm tối đa. Nhìn `criteria` ở đầu ra KHÔNG
phát hiện được chuyện này: khi mức bị đẩy lên 2 thì `occurrences` cũng rỗng
theo, nên đầu ra trông y hệt một bài thật sự đạt.

Kết quả ghi tăng dần vào docs/evidence/ và script bỏ qua lượt đã chạy - đứt
giữa chừng thì chạy lại là tiếp tục. Không phải cẩn thận thừa: E1 đã dính
đúng chuyện API hết hạn mức giữa chừng.

Hai bản đã đo, giữ cả hai để so được trước/sau khi sửa nợ B5 + phép kiểm
trích dẫn nhiều mảnh (docs/technical-debt.md B5):
    cp_lat_muc_truoc_sua.json    cp_lat_muc_sau_sua.json

Chạy (từ multiagent/):
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\chan_doan_lat_muc.py
    ... scripts\\chan_doan_lat_muc.py --thu       (1 lượt/1 bài, kiểm script)
    ... --ket-qua <ten.json>                      (chọn file, mặc định raw)
    ... --bao-cao --ket-qua <ten.json>            (in lại, KHÔNG gọi LLM)
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

import ai_core
from agents import compliance
from eval_stability import GIA_INPUT, GIA_OUTPUT
from label_helper import parse_sample

_HERE = os.path.dirname(os.path.abspath(__file__))
GOLD_DIR = os.path.normpath(os.path.join(_HERE, "..", "..", "docs", "goldset", "raw"))
_EVIDENCE = os.path.normpath(os.path.join(_HERE, "..", "..", "docs", "evidence"))


def duong_dan_ket_qua() -> str:
    """`--ket-qua <ten>` để giữ được cả bản TRƯỚC và SAU khi sửa làm bằng
    chứng, thay vì bản sau ghi đè mất bản trước (đặt tên theo eval_stability)."""
    if "--ket-qua" in sys.argv:
        return os.path.join(_EVIDENCE, sys.argv[sys.argv.index("--ket-qua") + 1])
    return os.path.join(_EVIDENCE, "cp_lat_muc_raw.json")

# Bốn bài có σ Compliance lớn nhất trong docs/evidence/e1_stability_rubric_v2
# .json: 12,50 / 11,31 / 4,52 / 4,12. Chọn theo SỐ ĐO chứ không chọn bừa -
# 4/10 bài trong E1 có σ = 0,00, đo trên chúng thì chắc chắn không thấy gì.
BAI = ["G-004", "G-003", "G-008", "G-001"]
SO_LUOT = 5

MA = ["CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8"]

_nhat_ky: list = []


def gan_theo_doi() -> None:
    """Bọc `_hop_thuc_hoa` để ghi lại mọi lần nó ghi đè mức LLM chấm."""
    goc = compliance._hop_thuc_hoa

    def boc(ma, muc, evidence, text_theo_field):
        sau = goc(ma, muc, evidence, text_theo_field)
        if sau != muc:
            _nhat_ky.append(
                {
                    "ma": ma,
                    "muc_llm": muc,
                    "muc_sau": sau,
                    "trich_dan_khop": compliance._trich_dan_co_that(
                        evidence, text_theo_field
                    ),
                    # 300 chứ không phải 120: cắt ngắn làm mảnh cuối đứt giữa
                    # chừng, nên chạy lại phép kiểm trích dẫn trên dữ liệu đã
                    # lưu sẽ ra kết quả bi quan hơn thực tế.
                    "evidence": (evidence or "")[:300],
                }
            )
        return sau

    compliance._hop_thuc_hoa = boc


def doc_bai(sid: str) -> dict:
    f = parse_sample(os.path.join(GOLD_DIR, f"{sid}.txt"))
    return {
        "title": f.get("title", ""),
        "body": f.get("body", ""),
        "meta_description": f.get("meta_description", ""),
    }


def chay_mot_luot(fields: dict) -> dict:
    _nhat_ky.clear()
    moc = len(ai_core.USAGE_LOG)
    ket_qua = compliance.run(fields)
    usage = ai_core.USAGE_LOG[moc:]

    if ket_qua is None:
        # None = CHƯA chấm được (LLM hỏng, bài rỗng). Giữ lại chứ không bỏ:
        # một lượt None lẫn giữa các lượt có điểm cũng là một dạng bất định.
        muc, diem = {}, None
    else:
        muc = {c["id"]: c["level"] for c in ket_qua["criteria"]}
        diem = ket_qua["score"]

    return {
        "diem": diem,
        "muc": {k: ("NA" if v is None else v) for k, v in muc.items()},
        "ghi_de": list(_nhat_ky),
        "input_tokens": sum(u["input_tokens"] for u in usage),
        "output_tokens": sum(u["output_tokens"] for u in usage),
    }


def nap() -> dict:
    if os.path.exists(duong_dan_ket_qua()):
        with open(duong_dan_ket_qua(), encoding="utf-8") as f:
            return json.load(f)
    return {}


def luu(data: dict) -> None:
    with open(duong_dan_ket_qua(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def do(bai: list, so_luot: int) -> dict:
    data = nap()
    for sid in bai:
        fields = doc_bai(sid)
        data.setdefault(sid, [])
        while len(data[sid]) < so_luot:
            print(f"  {sid} luot {len(data[sid]) + 1}/{so_luot} ...", flush=True)
            data[sid].append(chay_mot_luot(fields))
            luu(data)      # ghi sau MỖI lượt, không đợi xong hết
    return data


def bao_cao(data: dict) -> None:
    print("\nCHAN DOAN: TIEU CHI NAO LAT MUC GIUA CAC LAN CHAM")
    print(f"Model     : {ai_core.MODEL}, temperature=0")
    print(f"Nguon bai : {GOLD_DIR}")
    print("-" * 78)
    print(f"{'Bai':7} {'sigma':>6} {'diem qua cac luot':26} Tieu chi LAT")
    print("-" * 78)

    lat_tong: dict = {}
    for sid, luot in data.items():
        diem = [l["diem"] for l in luot if l["diem"] is not None]
        sig = statistics.pstdev(diem) if len(diem) > 1 else 0.0
        lat = []
        for ma in MA:
            gia_tri = {l["muc"].get(ma, "?") for l in luot}
            if len(gia_tri) > 1:
                lat.append(f"{ma}{sorted(gia_tri, key=str)}")
                lat_tong[ma] = lat_tong.get(ma, 0) + 1
        print(f"{sid:7} {sig:6.2f} {str(sorted(set(diem))):26} "
              f"{'  '.join(lat) if lat else '(khong lat)'}")

    print("-" * 78)
    print("SO BAI CO TIEU CHI DO LAT MUC:")
    for ma in MA:
        if lat_tong.get(ma):
            print(f"  {ma}: {lat_tong[ma]}/{len(data)} bai")
    if not lat_tong:
        print("  (khong tieu chi nao lat)")

    # --- nhật ký ghi đè: phần trả lời trực tiếp cho B5 ---------------------
    print("\nNHAT KY _hop_thuc_hoa GHI DE MUC LLM CHAM (gia thuyet B5):")
    tong = {}
    for sid, luot in data.items():
        for l in luot:
            for g in l["ghi_de"]:
                khoa = (g["ma"], g["muc_llm"], g["muc_sau"])
                tong[khoa] = tong.get(khoa, 0) + 1
    if not tong:
        print("  (khong lan nao) -> gia thuyet B5 KHONG duoc du lieu ung ho")
    else:
        for (ma, truoc, sau), n in sorted(tong.items(), key=lambda x: -x[1]):
            print(f"  {ma}: LLM cham {truoc} -> bi doi thanh {sau}   ({n} lan)")

    tin = sum(l["input_tokens"] for luot in data.values() for l in luot)
    tout = sum(l["output_tokens"] for luot in data.values() for l in luot)
    print(f"\nTong: {sum(len(v) for v in data.values())} luot, "
          f"{tin} token vao / {tout} token ra, "
          f"~${tin / 1e6 * GIA_INPUT + tout / 1e6 * GIA_OUTPUT:.3f}")


if __name__ == "__main__":
    if "--bao-cao" in sys.argv:
        bao_cao(nap())
        sys.exit(0)

    gan_theo_doi()
    if "--thu" in sys.argv:
        # Kiểm script chạy được trước khi tiêu tiền cho cả bộ.
        print(json.dumps(chay_mot_luot(doc_bai(BAI[0])), ensure_ascii=False, indent=1))
        sys.exit(0)

    bao_cao(do(BAI, SO_LUOT))

"""Quét ứng viên mã lỗi để rút ngắn phiên gán nhãn gold set.

Bổ sung cho `label_helper.py`, KHÔNG thay thế: file kia tính các mã máy kết
luận được chắc chắn (B3, B4, B6, B7, B9 + C4, C5); file này đánh dấu **chỗ
cần người xem** cho các mã còn lại, để người gán xác nhận/bác bỏ thay vì đọc
2000 từ đi tìm.

RANH GIỚI TUYỆT ĐỐI: script này CHỈ đánh dấu vị trí, KHÔNG kết luận mã lỗi.
Mọi dòng nó in ra đều là "chỗ cần xem", người đọc mới là bên quyết định. Lý
do không để script kết luận: các cụm này phụ thuộc ngữ cảnh nặng - "cách tốt
nhất để khắc phục sự cố" không phải claim quảng cáo, còn "công nghệ pin tốt
nhất thị trường" thì có.

VÌ SAO MẪU Ở ĐÂY TỰ VIẾT, KHÔNG IMPORT compliance_rules.json / brand_rules.json:
dùng chính danh sách của AI để đi tìm nhãn thì chỗ nào danh sách đó thiếu,
ground truth cũng thiếu y hệt - và lúc đó không bao giờ đo được lỗ hổng của
nó. Nợ B8 (hai cụm `critical` chết vì `\\b`) là bằng chứng danh sách đó sai
được. Nên mẫu ở đây viết độc lập và CỐ Ý RỘNG HƠN: thà người gán bác bỏ vài
chỗ thừa còn hơn không bao giờ nhìn thấy chỗ thiếu.

Đo được trên 33 mẫu (2026-08-10): blacklist CP1 của AI sinh flag `critical`
cho 14/33 bài, trong đó chỉ 3 bài là claim quảng cáo thật - phần còn lại là
"tốt nhất"/"duy nhất" dùng hợp lệ. Đó chính là thứ mẫu độc lập ở đây phải
tránh chép lại.

Cách chạy (từ multiagent/):
    .venv\\Scripts\\python.exe scripts\\quet_ung_vien.py ..\\docs\\goldset\\raw\\*.txt
"""
import csv
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from label_helper import analyze, parse_sample, split_sentences, strip_html

_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "goldset", "labels.csv",
)

# --- Mẫu tự viết, độc lập với rule của AI, cố ý rộng ------------------------

# A1 - claim tuyệt đối/so sánh nhất (Luật Quảng cáo 2012). Rộng hơn blacklist
# của AI: có thêm "hàng đầu", "nhất Việt Nam", "dẫn đầu" - guideline mục 4.1
# liệt kê chúng trong định nghĩa A1 nhưng compliance_rules.json KHÔNG có.
A1 = ["số 1", "số một", "tốt nhất", "duy nhất", "hàng đầu", "nhất việt nam",
      "đứng đầu", "dẫn đầu", "vượt trội nhất", "tuyệt đối", "top 1",
      "không đối thủ", "cam kết 100%", "hiệu quả 100%", "tối ưu nhất",
      "hiện đại nhất", "an toàn nhất", "rẻ nhất", "mạnh nhất", "bền nhất",
      "nhanh nhất", "lớn nhất", "hoàn hảo", "vô địch", "chưa từng có",
      "đẳng cấp nhất", "đi xa nhất", "pin trâu nhất"]

# A2 - so sánh trực tiếp với đối thủ cụ thể (Luật Cạnh tranh 2018)
A2 = ["tesla", "byd", "toyota", "honda", "yamaha", "pega", "yadea", "hyundai",
      "kia", "mercedes", "bmw", "wuling", "nissan", "ford", "mazda", "suzuki",
      "piaggio", "sym", "vespa", "grab", "xanh sm"]

# A4 - khuyến mại (Luật Thương mại). Chỉ là lỗi khi NÊU GIÁ TRỊ CỤ THỂ mà
# thiếu thời hạn/điều kiện - nên script chỉ đánh dấu chỗ nhắc tới ưu đãi.
A4 = ["khuyến mại", "khuyến mãi", "ưu đãi", "giảm ngay", "giảm giá", "tặng",
      "miễn phí", "quà tặng", "chiết khấu", "trợ giá", "voucher"]

# B5 - sai thuật ngữ/tên model so với chuẩn brand
B5 = ["vf8", "vf9", "vf5", "vf6", "vf7", "vfe34", "xe hơi điện", "ôtô điện",
      "ô-tô điện", "xe ô tô điện chạy pin"]

# Chuẩn đo phải có cạnh claim quãng đường (B1)
_CHUAN_DO = re.compile(r"NEDC|WLTP|EPA|CLTC|điều kiện lý tưởng|tham khảo",
                       re.IGNORECASE)
# Dấu hiệu đủ điều kiện của claim thời gian sạc (B2)
_TRU_SAC = re.compile(r"\bAC\b|\bDC\b|\d+\s*kW|trụ sạc|bộ sạc|sạc nhanh",
                      re.IGNORECASE)
_DAI_PHAN_TRAM = re.compile(r"\d+\s*%\s*(?:-|đến|tới)\s*\d+\s*%")

# Nhận diện câu ĐÁNG XÉT. Cắt câu bằng label_helper.split_sentences() chứ
# KHÔNG bằng `[^.]*` - mẫu đó cắt nhầm ở dấu thập phân ("1.500 đồng" thành hai
# mảnh) và ở viết tắt, cho ra ngữ cảnh cụt không đọc được.
_CO_KM = re.compile(r"\b\d[\d.,]*\s*km\b", re.IGNORECASE)
_CO_THOI_GIAN_SAC = re.compile(r"\b\d[\d.,]*\s*(?:phút|giờ|tiếng)\b", re.IGNORECASE)
_CO_PHAN_TRAM = re.compile(r"\b\d[\d.,]*\s*%")
_CO_NGUON = re.compile(
    r"theo |nguồn|báo cáo|thống kê|công bố|khảo sát|nghiên cứu", re.IGNORECASE
)
# CHỈ đơn vị có trong KB thông số (src/kb/specs.json) - A3 là "số liệu lệch
# thông số công bố", nên "11 lần", "3 chỗ" là nhiễu chứ không phải ứng viên.
_SO_CO_DON_VI = re.compile(
    r"\b\d[\d.,]*\s*(?:km|kWh|kW|phút|giờ|triệu|tỷ)\b", re.IGNORECASE
)


def _quet_cum(text: str, cum_list: list, rong: int = 55) -> list:
    """Mọi lần khớp của từng cụm, kèm ngữ cảnh hai bên."""
    ra, thap = [], text.lower()
    for cum in cum_list:
        for m in re.finditer(re.escape(cum), thap):
            d, c = max(0, m.start() - rong), min(len(text), m.end() + rong)
            ra.append((cum, " ".join(text[d:c].split())))
    return ra


def _cau_thieu(cau_list: list, dang_xet, du_dieu_kien) -> list:
    """Câu `dang_xet` mà KHÔNG `du_dieu_kien` -> đáng ngờ, cần người xem."""
    return [" ".join(c.split()) for c in cau_list
            if dang_xet(c) and not du_dieu_kien(c)]


def ung_vien(fields: dict) -> dict:
    """Trả dict mã -> danh sách chỗ cần người xem. KHÔNG kết luận mã lỗi."""
    text = " ".join([
        fields.get("title", "") or "",
        fields.get("meta_description", "") or "",
        fields.get("summary", "") or "",
        strip_html(fields.get("body", "") or ""),
    ])

    ra = {}
    for ma, ds in (("A1", A1), ("A2", A2), ("A4", A4), ("B5", B5)):
        hits = _quet_cum(text, ds)
        if hits:
            ra[ma] = [f'"{cum}" -> ...{nc}...' for cum, nc in hits]

    cau = split_sentences(text)

    thieu_chuan = _cau_thieu(cau, _CO_KM.search, _CHUAN_DO.search)
    if thieu_chuan:
        ra["B1"] = thieu_chuan

    thieu_dk = _cau_thieu(
        cau,
        lambda c: "sạc" in c.lower() and _CO_THOI_GIAN_SAC.search(c),
        lambda c: _TRU_SAC.search(c) and _DAI_PHAN_TRAM.search(c),
    )
    if thieu_dk:
        ra["B2"] = thieu_dk

    thieu_nguon = _cau_thieu(cau, _CO_PHAN_TRAM.search, _CO_NGUON.search)
    if thieu_nguon:
        ra["B10"] = thieu_nguon

    so = sorted(set(m.group(0) for m in _SO_CO_DON_VI.finditer(text)))
    if so:
        ra["A3"] = [", ".join(so)]

    return ra


_GIAI_THICH = {
    "A1": "Claim tuyệt đối? CHỈ tính khi khẳng định sản phẩm hơn hẳn/nhất. "
          "'cách tốt nhất để...' KHÔNG phải A1",
    "A2": "Có so sánh VinFast HƠN HẲN đối thủ này không? Chỉ nhắc tên -> không phải A2",
    "A3": "Đối chiếu các số này với src/kb/specs.json. Chỉ SAI SỐ mới là A3",
    "A4": "Có nêu GIÁ TRỊ CỤ THỂ mà thiếu thời hạn/điều kiện không?",
    "B1": "Câu có km nhưng không thấy chuẩn đo (NEDC/WLTP/EPA/CLTC)",
    "B2": "Câu có thời gian sạc nhưng thiếu loại trụ hoặc dải %",
    "B5": "Sai chuẩn tên model/thuật ngữ? ('VF8' phải là 'VF 8')",
    "B10": "Số liệu % không thấy nguồn gần đó",
}

_KHONG_QUET_DUOC = (
    "A5 lạc đề >50%  - đọc title rồi lướt các H2: body có trả lời đúng không?\n"
    "  A6 mất an toàn  - chỉ xét bài hướng dẫn thao tác sạc/pin\n"
    "  B8 chính tả     - mã DUY NHẤT phải đọc thật. Ghi SỐ LỖI vào notes"
)


def _nhom_cua(sid: str, injected: str, co_ma_may: bool) -> tuple:
    """Bài này thuộc nhóm việc nào -> quyết định phải đọc tới đâu."""
    if injected:
        if any(c.strip().startswith("A") for c in injected.split(";")):
            return ("XONG", "nhãn = rejected (chèn mã A). KHÔNG cần đọc.")
        return ("XONG", "nhãn = needs_revision (chèn mã B). KHÔNG cần đọc.")
    if co_ma_may:
        return ("CHỈ QUÉT A", "đã chắc >= needs_revision. Chỉ cần biết có mã A hay không.")
    return ("QUÉT ĐẦY ĐỦ", "chưa có mã nào -> phải phân biệt publish / needs_revision.")


def _injected_theo_sample() -> dict:
    try:
        with open(_CSV, encoding="utf-8") as f:
            return {r["sample_id"]: (r["injected_codes"] or "").strip()
                    for r in csv.DictReader(f)}
    except OSError:
        return {}


def report(path: str, injected_map: dict) -> None:
    sid = os.path.basename(path).replace(".txt", "")
    fields = parse_sample(path)
    _, codes, c_codes = analyze(fields)
    nhom, vi_sao = _nhom_cua(sid, injected_map.get(sid, ""), bool(codes))

    print("=" * 74)
    print(f"{sid}   [{nhom}]")
    print("=" * 74)
    print(f"  {vi_sao}")

    if codes:
        print("\n[MÁY ĐÃ CHỐT - ĐỔI NHÃN]")
        print("\n".join(f"  {c}" for c in codes))
    if c_codes:
        print("\n[NHÓM C - chép vào notes, KHÔNG đổi nhãn]")
        print("\n".join(f"  {c}" for c in c_codes))

    if nhom == "XONG":
        print()
        return

    kq = ung_vien(fields)
    can_xem = [m for m in ("A1", "A2", "A3", "A4") if m in kq]
    if nhom == "QUÉT ĐẦY ĐỦ":
        can_xem += [m for m in ("B1", "B2", "B5", "B10") if m in kq]

    print("\n[CHỖ CẦN NGƯỜI XÁC NHẬN - script KHÔNG kết luận]")
    if not can_xem:
        print("  (không có chỗ nào đáng ngờ)")
    for ma in can_xem:
        print(f"\n  {ma}: {_GIAI_THICH[ma]}")
        for dong in kq[ma][:8]:
            print(f"     - {dong[:200]}")
        if len(kq[ma]) > 8:
            print(f"     (+{len(kq[ma]) - 8} chỗ nữa)")

    print(f"\n[KHÔNG QUÉT ĐƯỢC - tự đọc]\n  {_KHONG_QUET_DUOC}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(sorted(glob.glob(arg)) or [arg])
    thieu = [p for p in paths if not os.path.isfile(p)]
    if thieu:
        print(f"Không tìm thấy file: {', '.join(thieu)}")
        sys.exit(1)

    injected_map = _injected_theo_sample()
    for p in paths:
        report(p, injected_map)

"""Phần "đo bằng máy" của rubric Compliance (docs/rubrics.md mục 2.4).

Tách khỏi `agents/compliance.py` theo đúng cách `brand_analysis.py` tách khỏi
`agents/brand_voice.py`: phần đếm được bằng regex nằm riêng, agent chỉ còn
việc ghép mức.

VÌ SAO TỒN TẠI (số đo, không phải sở thích kiến trúc): E1 ngày 2026-08-04 đo
Compliance σ = 6.47, trượt ngưỡng 2.0. Chẩn đoán ở docs/evidence/
cp_phan_bo_muc.txt: mẫu số trung bình chỉ 3.25/8 tiêu chí, và chỗ dao động là
CP5/CP6/CP8 - ba tiêu chí mà câu hỏi "bài có bàn tới chủ đề này không" đang
để LLM quyết định. G-007 có 66 số liệu định lượng mà LLM vẫn chấm CP8 = NA.

Câu hỏi đó ĐẾM ĐƯỢC, nên nó thuộc về máy.

GIỚI HẠN phải nêu khi báo cáo: các hàm dưới đây đo ở MỨC BÀI, không phải mức
từng claim. "Bài có nêu chuẩn đo ở đâu đó không" khác "claim 420 km này có
kèm chuẩn đo không". Chấp nhận vì hai lẽ: (1) mã lỗi B1/B2 trong
docs/goldset/annotation-guideline.md cũng gán ở mức bài, nên hai thang vẫn so
được với nhau; (2) đo thô mà tái lập được vẫn calibrate được, còn đo tinh mà
mỗi lần ra một kết quả thì không (rubrics.md mục 1).
"""
import re

_SO = r"\d+(?:[.,]\d+)?"

# --- CP5: claim tầm hoạt động / quãng đường ------------------------------
_KM = re.compile(_SO + r"\s*(?:km|ki-?lô-?mét)\b", re.IGNORECASE)

# Chuẩn đo tầm hoạt động được công nhận quốc tế. Corpus 33 bài: chỉ 4 bài nêu
# - đúng thứ mã lỗi B1 muốn bắt.
_CHUAN_DO = re.compile(r"\b(?:NEDC|WLTP|EPA|CLTC)\b", re.IGNORECASE)

# Lưu ý chung: không nêu chuẩn đo nhưng có cảnh báo con số chỉ là tham khảo.
# Đây là mức 1 của CP5 - đỡ hơn không nói gì, chưa bằng nêu chuẩn.
_LUU_Y_CHUNG = re.compile(
    r"thực tế có thể|tùy (?:thuộc|điều kiện)|"
    r"phụ thuộc (?:vào )?(?:điều kiện|cách|địa hình|thời tiết)|"
    r"chỉ mang tính|tham khảo|có thể (?:thay đổi|khác)",
    re.IGNORECASE,
)

# --- CP6: claim thời gian sạc --------------------------------------------
_THOI_GIAN = re.compile(_SO + r"\s*(?:phút|giờ|tiếng)\b", re.IGNORECASE)

# Cửa sổ ký tự quanh mốc thời gian để coi là "nói về sạc". 120 ký tự ~ một
# câu tiếng Việt: đủ rộng để bắt "sạc đầy pin trong khoảng 30 phút", đủ hẹp
# để không dính mốc thời gian của một đoạn khác trong cùng bài.
_CUA_SO_SAC = 120
_SAC = re.compile(r"sạc", re.IGNORECASE)

_LOAI_TRU = re.compile(
    r"\b(?:AC|DC)\b|sạc nhanh|sạc chậm|trụ sạc|cổng sạc|" + _SO + r"\s*kW\b",
    re.IGNORECASE,
)
_DAI_PHAN_TRAM = re.compile(_SO + r"\s*%", re.IGNORECASE)

# --- CP8: số liệu định lượng ---------------------------------------------
# Số PHẢI kèm đơn vị. "năm 2024" là con số nhưng không phải số liệu cần dẫn
# nguồn; "420 km", "82 kWh", "15 triệu" thì có. Corpus: 27/33 bài có.
_DON_VI = (r"km/h|km|kwh|kw|ah|phút|giờ|%|triệu|tỷ|đồng|vnđ|vnd|kg|lít|chỗ|"
           r"năm|tháng|mm|cm|m|lần")
_SO_LIEU = re.compile(_SO + r"\s*(?:" + _DON_VI + r")\b", re.IGNORECASE)


def _tim(pattern, text_theo_field: dict) -> list:
    """Trả list {field, text} cho mọi lần khớp, giữ nguyên văn đoạn khớp."""
    ra = []
    for field, text in text_theo_field.items():
        for m in pattern.finditer(text or ""):
            ra.append({"field": field, "text": m.group(0)})
    return ra


def claim_tam_hoat_dong(text_theo_field: dict) -> list:
    return _tim(_KM, text_theo_field)


def claim_thoi_gian_sac(text_theo_field: dict) -> list:
    """Mốc thời gian có chữ 'sạc' trong bán kính _CUA_SO_SAC ký tự."""
    ra = []
    for field, text in text_theo_field.items():
        text = text or ""
        for m in _THOI_GIAN.finditer(text):
            quanh = text[max(0, m.start() - _CUA_SO_SAC):m.end() + _CUA_SO_SAC]
            if _SAC.search(quanh):
                ra.append({"field": field, "text": m.group(0)})
    return ra


def so_lieu_dinh_luong(text_theo_field: dict) -> list:
    return _tim(_SO_LIEU, text_theo_field)


def _co(pattern, text_theo_field: dict) -> bool:
    return any(pattern.search(t or "") for t in text_theo_field.values())


def co_chuan_do(text_theo_field: dict) -> bool:
    return _co(_CHUAN_DO, text_theo_field)


def co_luu_y_chung(text_theo_field: dict) -> bool:
    return _co(_LUU_Y_CHUNG, text_theo_field)


def co_loai_tru_sac(text_theo_field: dict) -> bool:
    return _co(_LOAI_TRU, text_theo_field)


def co_dai_phan_tram(text_theo_field: dict) -> bool:
    return _co(_DAI_PHAN_TRAM, text_theo_field)

"""Compliance Agent - chấm theo rubric CP1-CP8 (docs/rubrics.md mục 6).

Ba cách đo, không phải ba nguồn flag song song:
  CP1, CP5, CP6      máy  - blacklist + regex (compliance_analysis.py)
  CP3                RAG  - fact_check.danh_gia(), đối chiếu thông số công bố
  CP2, CP4, CP7, CP8 LLM  - MỘT lần gọi, LLM chỉ chấm MỨC, không cho điểm

CP8 đặc biệt: MÁY quyết định tiêu chí có áp dụng hay NA (bài có số liệu định
lượng nào không - đếm được), LLM chỉ chấm mức khi đã áp dụng ("có dẫn nguồn
không" thì cần đọc hiểu).

Điểm do scoring.score_from_criteria() tính tất định; severity tra bảng
scoring.severity_for() theo mã tiêu chí. LLM không còn tự cho `score`, cũng
không còn tự chọn `severity`.

Lý do bỏ hai phán đoán tự do đó ở docs/rubrics.md mục 6.1; bằng chứng số ở
docs/evidence/e1_e4_report.txt: cách chấm cũ cho σ = 5.48 trên bài G-002 -
cùng bài, cùng model, cùng code, lúc ra 0 flag/95 điểm, lúc ra 2-3 flag mức
low/85 điểm. Compliance là agent duy nhất có quyền phủ quyết, nên đúng chỗ
đó lại là chỗ bất định nhất.
"""
import json
import os
import re

import compliance_analysis as ca
from ai_core import call_agent
from agents import fact_check
from prompt_builder import boc_noi_dung, boc_phan_an, chu_trong_doan_an
from scoring import score_from_criteria, severity_for
from text_utils import strip_html, trich_dan_co_that

_RULES_PATH = os.path.join(os.path.dirname(__file__), "compliance_rules.json")

_rules_cache = None

# Các field Compliance đọc (docs/rubrics.md mục 6)
_FIELDS = ("title", "body", "meta_description")

# Bốn tiêu chí do LLM chấm trong cùng một lần gọi.
#
# CP5 và CP6 ĐÃ RỜI danh sách này ngày 2026-08-04: E1 đo được chúng là nguồn
# dao động chính (docs/evidence/cp_phan_bo_muc.txt), và cả hai đo được bằng
# regex nên không có lý do gì để LLM chấm. CP8 vẫn ở đây nhưng phần "có áp
# dụng không" đã giao cho máy - chỉ phần "có dẫn nguồn không" cần đọc hiểu.
_MA_LLM = ("CP2", "CP4", "CP7", "CP8")

# Tiêu chí mà MÁY quyết định áp dụng hay NA, LLM chỉ chấm mức khi đã áp dụng.
_MAY_QUYET_AP_DUNG = ("CP8",)

_NHAN = {
    "CP1": "Claim tuyệt đối/so sánh nhất (CP1)",
    "CP2": "So sánh trực tiếp với đối thủ (CP2)",
    "CP3": "Số liệu lệch thông số công bố (CP3)",
    "CP4": "Khuyến mại thiếu thời hạn/điều kiện (CP4)",
    "CP5": "Tầm hoạt động thiếu điều kiện đo (CP5)",
    "CP6": "Thời gian sạc thiếu loại trụ/dải % (CP6)",
    "CP7": "Chính sách pin thiếu điều kiện/phí/thời hạn (CP7)",
    "CP8": "Số liệu định lượng không nguồn (CP8)",
}


def _nap_file_rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)
    return _rules_cache


def _load_rules() -> list[dict]:
    return _nap_file_rules()["phrases"]


def _pham_vi() -> list[str]:
    """Các cụm chỉ phạm vi so sánh ("thị trường", "Việt Nam"...)."""
    return _nap_file_rules()["pham_vi"]


# Cửa sổ tìm cụm chỉ phạm vi quanh chỗ khớp. Rộng về SAU nhiều hơn vì tiếng
# Việt đặt phạm vi sau tính từ ("tốt nhất thị trường", "số 1 Việt Nam").
_TRUOC_PHAM_VI, _SAU_PHAM_VI = 30, 45


def _co_pham_vi(text: str, start: int, end: int) -> bool:
    cua_so = text[max(0, start - _TRUOC_PHAM_VI):end + _SAU_PHAM_VI].lower()
    return any(p in cua_so for p in _pham_vi())


_KY_TU_TU = re.compile(r"\w", re.UNICODE)


def _mau_khop(cum: str) -> str:
    """Regex cho một cụm cấm: chỉ đặt \\b ở đầu/cuối khi ký tự ở đó là chữ/số.

    Đặt \\b vô điều kiện là SAI và đã làm chết hai cụm. \\b là ranh giới giữa
    ký tự chữ/số và ký tự không phải chữ/số, nên \\b sau '%' đòi ngay sau đó
    phải có chữ/số - mà sau '%' thực tế luôn là dấu cách hoặc dấu câu. Hệ quả
    đo được: "cam kết 100%" và "hiệu quả 100%", cả hai đều severity
    `critical`, chưa từng khớp lần nào.

    Đây là chỗ nguy hiểm để mù, vì blacklist là cách đo DUY NHẤT của CP1 và
    là thứ vẫn chạy khi LLM bị lừa hoàn toàn (docs/prompt-injection.md mục
    4c). Nhưng "miễn nhiễm với injection" không có nghĩa là "đúng" - lỗi ở
    đây tự nó làm hỏng lớp phòng vệ đó, cùng bài học với nợ B2.
    """
    truoc = r"\b" if _KY_TU_TU.match(cum[0]) else ""
    sau = r"\b" if _KY_TU_TU.match(cum[-1]) else ""
    return truoc + re.escape(cum) + sau


def match_blacklist(text: str) -> list[dict]:
    """So khớp cứng (không phân biệt hoa/thường) với danh sách từ cấm.

    Đây là cách đo của CP1 (docs/rubrics.md mục 6.1), không còn là nguồn flag
    song song với LLM - nhờ đó không còn tình huống flags và score mâu thuẫn
    nhau như bản cũ.

    Mỗi cụm khớp tạo 1 mục. Chỉ bắt lần khớp đầu tiên của mỗi cụm trong text
    (không đếm các lần lặp lại).

    Dùng \\b (word boundary) thay vì so khớp chuỗi con thô, để tránh khớp
    nhầm vào số dài hơn (VD cụm "số 1" khớp nhầm vào "số 10", "số 100") -
    nhưng chỉ ở đầu/cuối là chữ/số, xem `_mau_khop`.

    Khoá `la_claim` cho biết lần khớp này có phải claim quảng cáo thật không:
    với cụm `can_pham_vi`, chỉ tính là claim khi quanh đó có cụm chỉ phạm vi
    so sánh. `_cp1_claim_tuyet_doi` dùng nó để chọn mức 0 hay mức 1 - xem lý
    do ở đó.
    """
    flags = []
    for rule in _load_rules():
        pattern = _mau_khop(rule["text"])
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 20)
        flags.append(
            {
                "severity": rule["severity"],
                "rule": rule["rule"],
                "excerpt": text[start:end].strip(),
                "la_claim": (
                    not rule.get("can_pham_vi", False)
                    or _co_pham_vi(text, match.start(), match.end())
                ),
            }
        )
    return flags


def _tieu_chi(ma: str, level, occurrences=None, reason="") -> dict:
    """Một tiêu chí đã chấm.

    `occurrences` là list {field, text, rule?}. `rule` để rỗng thì flag lấy
    nhãn chung của tiêu chí; CP1 và CP3 điền `rule` riêng vì chúng biết chính
    xác điều khoản nào bị vi phạm.
    """
    return {"id": ma, "level": level, "occurrences": occurrences or [], "reason": reason}


# ---------------------------------------------------------------- CP1: máy


def _cp1_claim_tuyet_doi(text_theo_field: dict) -> dict:
    """Mức 0 khi có claim so sánh nhất NÊU RÕ PHẠM VI; mức 1 khi chỉ có cụm
    so sánh nhất dùng không kèm phạm vi.

    Vì sao tách hai mức (2026-08-10): mức 0 sinh flag `critical` -> Aggregator
    veto -> `rejected`, tức chặn xuất bản. Cách cũ coi MỌI lần khớp là mức 0,
    đo trên 33 mẫu gold set cho ra **14 bài bị veto trong khi chỉ 3 bài vi
    phạm thật** - "tốt nhất" trong "cách tốt nhất để khắc phục sự cố", "duy
    nhất" trong "áp dụng duy nhất 01 Gói" đều bị chặn oan. Precision 0,21.

    Lập luận giống hệt CP3 mức 1 (docs/rubrics.md mục 6.2): claim so sánh nhất
    chỉ trở thành khẳng định kiểm chứng được khi nó xác định phạm vi so sánh,
    nên thiếu phạm vi thì "chưa đủ căn cứ để chặn", không phải "chắc chắn vi
    phạm". Sau khi sửa: precision 1,00 trên cùng bộ mẫu, recall giữ nguyên.

    ĐÁNH ĐỔI ĐÃ BIẾT: claim thật mà không nêu phạm vi ("VinFast là thương hiệu
    xe điện tốt nhất.") rơi xuống mức 1. Nó KHÔNG biến mất - vẫn sinh flag
    `low` hiện trong báo cáo cho người duyệt, chỉ thôi tự động từ chối bài.
    Đổi 11 lần chặn oan chắc chắn lấy vài lần hạ mức là đánh đổi có lợi trong
    một hệ thống luôn có người bấm nút cuối (architecture.md mục 2.3).
    """
    if not any(t.strip() for t in text_theo_field.values()):
        return _tieu_chi("CP1", None)

    cho_sai, co_claim = [], False
    for field, text in text_theo_field.items():
        for m in match_blacklist(text):
            cho_sai.append({"field": field, "text": m["excerpt"], "rule": m["rule"]})
            co_claim = co_claim or m["la_claim"]

    if not cho_sai:
        return _tieu_chi("CP1", 2)
    if co_claim:
        return _tieu_chi(
            "CP1", 0, cho_sai,
            "Bỏ cụm so sánh tuyệt đối hoặc thay bằng phát biểu có căn cứ kiểm "
            "chứng được (kèm nguồn, phạm vi so sánh, thời điểm).",
        )
    return _tieu_chi(
        "CP1", 1, cho_sai,
        "Bài dùng cụm so sánh nhất nhưng không nêu phạm vi so sánh. Nhiều khả "
        "năng là cách nói thông thường (VD 'cách tốt nhất để...'), không phải "
        "claim quảng cáo - rà lại để chắc chắn, và cân nhắc diễn đạt khác nếu "
        "câu có thể bị hiểu là khẳng định hơn hẳn đối thủ.",
    )


# ------------------------------------------------------- CP5, CP6: máy


def _cp5_tam_hoat_dong(text_theo_field: dict) -> dict:
    """Claim quãng đường có nêu điều kiện đo không (mã lỗi B1).

    Không có claim km nào -> NA. Đây là NA đúng nghĩa "bài không bàn tới",
    và giờ do máy kết luận nên nó không đổi giữa các lần chấm.
    """
    claims = ca.claim_tam_hoat_dong(text_theo_field)
    if not claims:
        return _tieu_chi("CP5", None)
    if ca.co_chuan_do(text_theo_field):
        return _tieu_chi("CP5", 2)
    if ca.co_luu_y_chung(text_theo_field):
        return _tieu_chi(
            "CP5", 1, claims,
            "Bài có lưu ý con số chỉ mang tính tham khảo nhưng chưa nêu chuẩn "
            "đo. Ghi rõ chuẩn (NEDC, WLTP, EPA hoặc CLTC) ngay cạnh con số.",
        )
    return _tieu_chi(
        "CP5", 0, claims,
        "Claim quãng đường không kèm chuẩn đo lẫn lưu ý nào. Bổ sung chuẩn đo "
        "(NEDC, WLTP, EPA, CLTC) hoặc ít nhất lưu ý quãng đường thực tế thay "
        "đổi theo điều kiện vận hành.",
    )


def _cp6_thoi_gian_sac(text_theo_field: dict) -> dict:
    """Claim thời gian sạc có nêu loại trụ và dải % không (mã lỗi B2)."""
    claims = ca.claim_thoi_gian_sac(text_theo_field)
    if not claims:
        return _tieu_chi("CP6", None)
    du = [ca.co_loai_tru_sac(text_theo_field), ca.co_dai_phan_tram(text_theo_field)]
    if all(du):
        return _tieu_chi("CP6", 2)
    thieu = "dải phần trăm (ví dụ 10-70%)" if du[0] else "loại trụ sạc (AC/DC, công suất kW)"
    if any(du):
        return _tieu_chi("CP6", 1, claims,
                         f"Claim thời gian sạc còn thiếu {thieu}.")
    return _tieu_chi(
        "CP6", 0, claims,
        "Claim thời gian sạc không nêu loại trụ sạc lẫn dải phần trăm. "
        "Thiếu cả hai thì con số thời gian không so sánh được.",
    )


# ---------------------------------------------------------------- CP3: RAG


def _cp3_so_lieu(fields: dict, content_type: str, langcode: str, danh_gia_cp3) -> dict:
    """Lỗi bất kỳ ở tầng KB -> NA, KHÔNG phải 0.

    KB có thể chưa dựng (chạy src/kb/build_kb.py). Hạ tầng hỏng không được
    biến thành hình phạt lên nội dung - cùng nguyên tắc với BV6 và với việc
    Aggregator trả final_score = None khi Compliance không chạy được.
    """
    try:
        kq = danh_gia_cp3(fields, content_type=content_type, langcode=langcode)
    except Exception:
        return _tieu_chi("CP3", None)
    return _tieu_chi("CP3", kq["level"], kq["occurrences"], kq["reason"])


# ------------------------------------------------- CP2, CP4-CP8: một lần LLM

_CP4_CUA_SO = 240
_CP4_MOC_THOI_HAN = re.compile(
    r"(?:"
    r"\b\d{1,2}[/-]\d{1,2}\s*[-–—]\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b(?:từ(?: ngày)?|kể từ(?: ngày)?|trước|đến|tới(?: hết)?)\s+"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|"
    r"\b(?:đến|tới)\s+hết\s+tháng\s+\d{1,2}(?:/\d{4})?\b|"
    r"\btrong(?: vòng)?\s+\d+\s+(?:ngày|tháng|năm)(?:\s+đầu)?\b|"
    r"\b\d+\s+(?:ngày|tháng|năm)\s+kể từ\b|"
    r"\báp dụng\s+đến khi\s+hết hàng\b"
    r")",
    re.IGNORECASE,
)
_CP4_TACH_EVIDENCE = re.compile(r"\s+và\s+|[;\n]|(?<=[.%])\s+")


def _cp4_chuan_hoa(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _cp4_co_thoi_han(evidence: str, text_theo_field: dict) -> bool:
    """Có dấu hiệu thời hạn trong evidence hoặc sát evidence thật hay không."""
    manh = [
        _cp4_chuan_hoa(m).strip(" \"'“”…-")
        for m in _CP4_TACH_EVIDENCE.split(evidence or "")
    ]
    manh = [m for m in manh if m]
    # Evidence nhiều mảnh có thể được xác thực ở các field khác nhau. Khi đó
    # không được lấy một mảnh chỉ chứa ngày ở title để hợp thức hoá khuyến mại
    # nằm trong body. Ưu tiên mảnh không có mốc thời hạn làm anchor khuyến mại;
    # chỉ khi evidence toàn mốc thời gian mới dùng chính các mảnh đó.
    khong_moc = [m for m in manh if not _CP4_MOC_THOI_HAN.search(m)]
    anchors = sorted(khong_moc or manh, key=len, reverse=True)
    if not anchors:
        return False

    for text in text_theo_field.values():
        kho = _cp4_chuan_hoa(text)
        for anchor in anchors:
            start = 0
            while True:
                vi_tri = kho.find(anchor, start)
                if vi_tri < 0:
                    break
                cua_so = kho[
                    max(0, vi_tri - _CP4_CUA_SO):
                    min(len(kho), vi_tri + len(anchor) + _CP4_CUA_SO)
                ]
                if _CP4_MOC_THOI_HAN.search(cua_so):
                    return True
                start = vi_tri + 1
    return False

_LLM_PROMPT = (
    "Bạn là chuyên gia kiểm duyệt tuân thủ pháp lý cho nội dung marketing xe "
    "điện (ô tô điện, xe máy điện) tại Việt Nam.\n\n"
    "Bạn KHÔNG cho điểm và KHÔNG chọn mức nghiêm trọng. Bạn chỉ chấm MỨC cho "
    "từng tiêu chí dưới đây. Điểm số và mức nghiêm trọng do hệ thống tính tất "
    "định từ các mức bạn chấm.\n\n"
    "Chấm đúng 4 tiêu chí sau, mỗi tiêu chí một lần:\n\n"
    "CP2 - So sánh trực tiếp với đối thủ cụ thể (Tesla, BYD, Toyota, Honda, "
    "Yamaha...) theo hướng hơn hẳn. Nguy cơ vi phạm Luật Cạnh tranh 2018.\n"
    "  0 = có so sánh như vậy\n"
    "  2 = không có\n"
    "  (CP2 KHÔNG được chấm NA)\n\n"
    "CP4 - Khuyến mại nêu giá trị cụ thể có đủ ĐIỀU KIỆN áp dụng hay không.\n"
    "  Hệ thống sẽ tự kiểm THỜI HẠN bằng code; bạn không kết luận thiếu/đủ "
    "thời hạn.\n"
    "  Chỉ xét khuyến mại NÊU GIÁ TRỊ CỤ THỂ (số tiền, phần trăm, quà tặng "
    "định lượng). Câu chào mời chung chung không có giá trị nào - 'nhận nhiều "
    "ưu đãi hấp dẫn', 'liên hệ để biết ưu đãi' - KHÔNG phải khuyến mại theo "
    "nghĩa này, chấm NA.\n"
    "  Chính sách của NHÀ NƯỚC (miễn lệ phí trước bạ, ưu đãi thuế) KHÔNG phải "
    "khuyến mại của doanh nghiệp, cũng chấm NA.\n"
    "  0 = có khuyến mại nêu giá trị cụ thể nhưng thiếu điều kiện áp dụng\n"
    "  2 = có khuyến mại nêu giá trị cụ thể và nêu đủ điều kiện áp dụng\n"
    "  NA = bài không có khuyến mại nào nêu giá trị cụ thể\n"
    "  Không dùng mức 1 cho CP4.\n\n"
    "CP7 - Chính sách pin / thuê pin nêu đủ ĐIỀU KIỆN, PHÍ và THỜI HẠN.\n"
    "  0 = thiếu từ 2 yếu tố trở lên\n"
    "  1 = thiếu 1 yếu tố\n"
    "  2 = đủ cả ba\n"
    "  NA = bài không nhắc tới chính sách pin hay thuê pin\n\n"
    "CP8 - Số liệu định lượng có dẫn nguồn.\n"
    "  0 = có số liệu nhưng không nêu nguồn nào\n"
    "  1 = một phần số liệu có nguồn\n"
    "  2 = mọi số liệu đều có nguồn\n"
    "  NA = bài không có số liệu định lượng nào\n"
    "  (CP8: hệ thống đã tự kiểm bài có số liệu hay không, nên nếu bạn chấm "
    "NA mà bài thật sự có số liệu thì kết luận NA sẽ bị bỏ qua)\n\n"
    "QUY TẮC BẮT BUỘC:\n\n"
    "1. NA nghĩa là 'bài không hề bàn tới chuyện này', KHÔNG phải 'bài làm "
    "đúng'. Chấm NA thành mức 2 sẽ cộng điểm miễn phí cho mọi bài không nhắc "
    "tới chủ đề đó.\n\n"
    "2. Mức 0 và mức 1 LUÔN phải kèm `evidence` là đoạn trích NGUYÊN VĂN chỗ "
    "vi phạm - copy chính xác từng chữ từ bài, không diễn giải, không rút gọn, "
    "không sửa dấu câu. Không trích được nguyên văn thì không được hạ mức.\n\n"
    "3. Với CP4-CP8, mức 2 CŨNG phải kèm `evidence` nguyên văn: đoạn chứng "
    "minh bài CÓ bàn tới chủ đề và bàn đúng. Không trích được thì chấm NA, "
    "không phải mức 2. CP2 là ngoại lệ duy nhất - mức 2 của CP2 nghĩa là "
    "'không tìm thấy', không có gì để trích.\n\n"
    "4. Chỉ xét 6 tiêu chí trên. KHÔNG xét chính tả, văn phong, SEO.\n\n"
    "5. Trả lời bằng tiếng Việt ở trường `reason`."
)

_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": list(_MA_LLM)},
                    # Dùng chuỗi thay vì số để biểu diễn được NA trong một
                    # enum duy nhất - schema strict không nhận kiểu hợp
                    # (integer | null) một cách chắc chắn.
                    "muc": {"type": "string", "enum": ["0", "1", "2", "NA"]},
                    "field": {
                        "type": "string",
                        "enum": ["title", "body", "meta_description"],
                    },
                    "evidence": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "muc", "field", "evidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["criteria"],
    "additionalProperties": False,
}


def _hop_thuc_hoa(ma: str, muc, evidence: str, text_theo_field: dict):
    """Áp quy tắc bằng chứng lên mức LLM vừa chấm.

    Hai hướng sửa khác nhau, và chọn sai hướng chính là lỗi "điểm miễn phí"
    mà rubrics.md mục 8.1 ghi lại từ đợt Brand Voice:

    - CP2 (vô điều kiện): không trích được -> quay về mức 2, vì mức 2 của CP2
      đúng nghĩa là "không tìm thấy vi phạm".
    - CP4-CP7 (có điều kiện): không trích được -> NA, TUYỆT ĐỐI không phải
      mức 2. Không chứng minh được bài có bàn tới chủ đề thì cũng không có
      căn cứ nào để nói bài làm đúng chủ đề đó.
    - CP8 (máy đã chốt áp dụng): không trích được -> mức 0, xem dưới.
    """
    if muc is None:
        return None
    if ma == "CP2":
        return muc if (muc == 2 or trich_dan_co_that(evidence, text_theo_field)) else 2
    if ma in _MAY_QUYET_AP_DUNG:
        # Máy mới là bên chốt NA cho các mã này (xem _chot_cp8), nên ở đây
        # chỉ áp quy tắc trích dẫn cho việc HẠ mức, không đẩy về NA.
        #
        # Hạ mà không trích được -> mức 0, KHÔNG phải mức 2 (nợ B5, sửa
        # 2026-08-04). Trả mức 2 là sai theo hướng nguy hiểm nhất: tiêu chí
        # vừa bị nghi vi phạm lại được cộng ĐIỂM TỐI ĐA, `occurrences` rỗng
        # theo nên đầu ra trông y hệt một bài thật sự đạt - nhìn `criteria`
        # không phát hiện được. Đo được 10/20 lượt dính (docs/evidence/
        # cp_lat_muc_raw.json), riêng G-008 dính cả 5/5 lượt nên điểm bị thổi
        # lên một cách NHẤT QUÁN, tức σ không hề báo động.
        #
        # Mức 0 đúng theo chính lập luận của _chot_cp8: máy đã xác nhận bài
        # có số liệu, LLM không chỉ ra được nguồn nào - đó là định nghĩa của
        # mức 0. Khác CP4/CP7 (-> NA) vì với CP8 câu hỏi "bài có bàn tới chủ
        # đề này không" do MÁY chốt, không phụ thuộc LLM trích được hay không.
        return muc if (muc == 2 or trich_dan_co_that(evidence, text_theo_field)) else 0
    return muc if trich_dan_co_that(evidence, text_theo_field) else None


def _danh_gia_llm(fields: dict, text_theo_field: dict) -> dict:
    """Gọi LLM một lần, trả dict mã -> tiêu chí đã hợp thức hoá.

    M1 + M3 qua `prompt_builder.boc_noi_dung`. Compliance là chỗ đáng làm
    nhất trong 4 agent: nó là agent duy nhất có quyền phủ quyết, nên một câu
    chèn thành công ở đây đổi được kết luận "chặn xuất bản" thành "cho qua".

    Phần bị bóc KHÔNG bị vứt: `run()` vẫn quét blacklist CP1 trên
    `text_theo_field` dựng từ body GỐC (docs/prompt-injection.md mục 5 M3).
    """
    noi_dung, _ = boc_noi_dung(fields, _FIELDS)
    kq = call_agent(_LLM_PROMPT, noi_dung, _LLM_SCHEMA)

    theo_ma = {}
    for c in kq["criteria"]:
        ma = c["id"]
        if ma not in _MA_LLM or ma in theo_ma:
            continue      # mã lạ hoặc chấm trùng -> giữ lần đầu
        muc = None if c["muc"] == "NA" else int(c["muc"])
        muc = _hop_thuc_hoa(ma, muc, c["evidence"], text_theo_field)
        can_evidence = muc in (0, 1) or (ma == "CP4" and muc == 2)
        occ = ([{"field": c["field"], "text": c["evidence"]}]
               if can_evidence else [])
        theo_ma[ma] = _tieu_chi(ma, muc, occ, c["reason"] if muc in (0, 1) else "")
    return theo_ma


def _cac_tieu_chi_llm(fields: dict, text_theo_field: dict, danh_gia_llm) -> tuple:
    """Trả (dict mã -> tiêu chí, llm_hong).

    Lỗi LLM -> cả 6 tiêu chí thành NA, KHÔNG phải 0. Nhưng người gọi phải
    biết đó là NA vì HẠ TẦNG HỎNG chứ không phải vì "bài không bàn tới chủ
    đề" - hai thứ này cùng ký hiệu NA nhưng ý nghĩa ngược nhau, xem run().
    """
    try:
        theo_ma = danh_gia_llm(fields, text_theo_field)
    except Exception:
        return {ma: _tieu_chi(ma, None) for ma in _MA_LLM}, True
    # Mã LLM không trả về cũng coi là NA - không suy đoán hộ.
    return {ma: theo_ma.get(ma) or _tieu_chi(ma, None) for ma in _MA_LLM}, False


def _chot_cp8(tu_llm: dict, text_theo_field: dict, llm_hong: bool) -> dict:
    """Máy chốt CP8 có áp dụng hay không; LLM chỉ chấm mức.

    Hai chiều ghi đè, cả hai đều nhằm chặn mẫu số nhảy:

    - Bài KHÔNG có số liệu định lượng nào -> NA, bất kể LLM chấm gì.
    - Bài CÓ số liệu mà LLM vẫn trả NA -> mức 0. Không phải suy đoán hộ: mức
      0 của CP8 định nghĩa đúng là "có số liệu nhưng không nêu nguồn nào", và
      LLM không chỉ ra được nguồn nào chính là trạng thái đó. Đo được trên
      corpus: G-007 có 66 số liệu định lượng mà LLM chấm NA.
    """
    so_lieu = ca.so_lieu_dinh_luong(text_theo_field)
    if not so_lieu:
        return _tieu_chi("CP8", None)
    if llm_hong:
        # LLM chưa chạy thì "không chỉ ra được nguồn nào" không nói lên điều
        # gì về bài viết. Lỗi hạ tầng không được biến thành mức 0.
        return _tieu_chi("CP8", None)
    if tu_llm["level"] is None:
        return _tieu_chi(
            "CP8", 0, so_lieu[:5],
            "Bài có số liệu định lượng nhưng không dẫn nguồn. Ghi rõ nguồn "
            "(thông cáo VinFast, trang thông số chính thức) ngay cạnh số liệu.",
        )
    return tu_llm


def _chot_cp4(tu_llm: dict, text_theo_field: dict) -> dict:
    """Ghép điều kiện do LLM đọc với thời hạn do code nhận diện."""
    muc = tu_llm["level"]
    if muc is None:
        return tu_llm
    if muc in (0, 1):
        # CP4 không có mức một phần: thiếu điều kiện là lỗi A4 mức 0.
        return _tieu_chi("CP4", 0, tu_llm["occurrences"], tu_llm["reason"])
    if muc != 2 or not tu_llm["occurrences"]:
        return _tieu_chi("CP4", None)

    evidence = tu_llm["occurrences"][0].get("text", "")
    if _cp4_co_thoi_han(evidence, text_theo_field):
        # Evidence mức 2 chỉ dùng nội bộ để chốt thời hạn; output đạt giữ
        # hình dạng cũ với occurrences rỗng.
        return _tieu_chi("CP4", 2)
    return _tieu_chi(
        "CP4", 0, tu_llm["occurrences"],
        "Khuyến mại đã nêu điều kiện áp dụng nhưng chưa thấy thời hạn trong "
        "đoạn khuyến mại hoặc nội dung liền kề. Bổ sung ngày bắt đầu/kết thúc "
        "hoặc thời lượng áp dụng ngay cạnh ưu đãi.",
    )


# ------------------------------------------------------------------- ghép


def _flags_from_criteria(criteria: list[dict]) -> list[dict]:
    """Tiêu chí mức 0/1 -> flag. Mức 2 và NA không sinh gì.

    Giữ nguyên hình dạng flag cũ {field, severity, rule, excerpt} vì cả
    graph._issue_to_json lẫn module PHP vf_ai_review đều đọc theo hình dạng
    đó. Thêm `suggestion` - bản cũ không có gì để gợi ý sửa vì LLM chỉ trả
    tên điều khoản.
    """
    flags = []
    for c in criteria:
        if c["level"] not in (0, 1):
            continue
        sev = severity_for(c["id"], c["level"])
        for o in c["occurrences"] or [{"field": "body", "text": ""}]:
            flags.append(
                {
                    "field": o.get("field") or "body",
                    "severity": sev,
                    "rule": o.get("rule") or _NHAN[c["id"]],
                    "excerpt": o.get("text", ""),
                    "suggestion": c["reason"],
                }
            )
    return flags


_CP9_RULE = "Chỉ dẫn ẩn nhắm vào hệ thống đánh giá tự động (CP9)"


def _cp9_chi_dan_an(doan_an) -> list:
    """CP9 (M2) - sinh flag `critical`, KHÔNG tham gia công thức tính điểm.

    Cố ý đứng ngoài `criteria`. Thang 0/1/2 dùng để đo MỨC ĐỘ - "sai nhiều
    hay sai ít". Giấu chỉ dẫn nhắm vào máy chấm thì không có "hơi giấu một
    chút": hoặc có, hoặc không. Đó là câu hỏi CHẶN HAY KHÔNG CHẶN, mà cơ chế
    veto của Aggregator đã trả lời sẵn, độc lập với điểm.

    Đưa vào công thức còn có tác hại đo được: hầu hết bài không giấu gì nên
    tiêu chí này gần như luôn ở mức 2, tức cộng điểm miễn phí cho mọi bài.
    Trên bài G-004 thật, thêm một tiêu chí luôn-đạt đẩy điểm từ 50,0 lên
    62,5 mà bài không đổi một chữ - đúng lỗi rubrics.md mục 2.2 cảnh báo.

    Nó cũng sẽ làm σ đẹp lên bằng cách pha loãng mẫu số, chứ không phải bằng
    cách đo chính xác hơn. Không đáng đổi.
    """
    dang_ngo = ca.doan_an_dang_ngo(doan_an)
    return [
        {
            "field": "body",
            "severity": "critical",
            "rule": _CP9_RULE,
            "excerpt": chu[:200],
            "suggestion": "Đoạn này bị ẩn khỏi người đọc nhưng hệ thống đánh "
                          "giá tự động vẫn đọc được. Xoá khỏi nội dung, và "
                          "kiểm tra lại nguồn gốc bài viết.",
        }
        for chu in dang_ngo
    ]


def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi",
        danh_gia_llm=_danh_gia_llm, danh_gia_cp3=None) -> dict | None:
    """Chấm Compliance. Trả None khi không tiêu chí nào áp dụng được.

    None nghĩa là CHƯA CHẤM ĐƯỢC, khác hẳn 0 điểm: Aggregator gặp
    compliance_result = None thì không bao giờ tự động publish
    (architecture.md mục 6.4).

    `danh_gia_llm` và `danh_gia_cp3` tiêm được để test không gọi LLM/KB.
    `danh_gia_cp3` giải ở thời điểm gọi, không ở default, để test thay được
    cả module fact_check.
    """
    if danh_gia_cp3 is None:
        danh_gia_cp3 = fact_check.danh_gia
    text_theo_field = {f: strip_html(fields.get(f) or "") for f in _FIELDS}

    # M3 vế thứ hai (docs/prompt-injection.md mục 5): phần bị bóc khỏi prompt
    # VẪN phải được quét - chỗ bị bóc ra chính là chỗ đáng ngờ nhất.
    #
    # Không có mấy dòng này thì hệ thống mù thật, không phải mù trên lý
    # thuyết: `strip_html` khớp trọn `<!-- tốt nhất -->` bằng regex `<[^>]+>`
    # và xoá luôn chữ bên trong, nên cụm từ cấm giấu trong bình luận HTML đi
    # qua blacklist CP1 mà không bị bắt lần nào.
    _, doan_an = boc_phan_an(fields.get("body") or "")
    if doan_an:
        text_theo_field["body"] += "\n" + chu_trong_doan_an(doan_an)

    if not any(t.strip() for t in text_theo_field.values()):
        # Bài rỗng: các tiêu chí dạng "không được có X" (CP1, CP2) sẽ trả mức
        # 2 - đúng logic nhưng thành 100 điểm Compliance cho một bài không có
        # nội dung nào để kiểm duyệt.
        return None

    llm, llm_hong = _cac_tieu_chi_llm(fields, text_theo_field, danh_gia_llm)
    criteria = [
        _cp1_claim_tuyet_doi(text_theo_field),
        llm["CP2"],
        _cp3_so_lieu(fields, content_type, langcode, danh_gia_cp3),
        _chot_cp4(llm["CP4"], text_theo_field),
        _cp5_tam_hoat_dong(text_theo_field),
        _cp6_thoi_gian_sac(text_theo_field),
        llm["CP7"],
        _chot_cp8(llm["CP8"], text_theo_field, llm_hong),
    ]

    if llm_hong and not any(c["level"] == 0 for c in criteria):
        # 6/8 tiêu chí không đo được vì hạ tầng, và phần đo được không tìm
        # thấy vi phạm nào. "Không tìm thấy" ở đây KHÔNG có nghĩa là tuân thủ:
        # thứ duy nhất còn chạy là danh sách từ cấm. Trả điểm lúc này là báo
        # Compliance = 100 cho một bài mới chỉ được dò từ khoá.
        #
        # Bắt được nhờ chạy E1 ngày 2026-08-04: API hết hạn mức giữa chừng và
        # 6/7 bài nhận đúng con số vô nghĩa đó.
        #
        # Có vi phạm cứng (mức 0, VD CP1 khớp từ cấm) thì VẪN trả kết quả -
        # bằng chứng đã đủ để từ chối, và đánh mất một veto nguy hiểm hơn hẳn
        # so với việc báo "chưa xác minh được".
        return None

    score = score_from_criteria(criteria)
    if score is None:
        return None
    return {
        "score": score,
        "flags": _flags_from_criteria(criteria) + _cp9_chi_dan_an(doan_an),
        "criteria": criteria,
    }

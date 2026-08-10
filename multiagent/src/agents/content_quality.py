"""Content Quality Agent - chấm theo rubric CQ1-CQ8 (docs/rubrics.md mục 3).

Hai cách đo:
  CQ3, CQ4, CQ5        máy hoàn toàn (đếm câu dài, đoạn dài, cấu trúc heading)
  CQ8                  máy chốt mức 0 (summary trống), LLM phân biệt 1/2
  CQ1, CQ2             LLM LIỆT KÊ lỗi kèm trích dẫn -> MÁY đếm và quy mức
  CQ6, CQ7             LLM chấm mức trực tiếp (định tính)

Điểm do `scoring.score_from_criteria()` tính tất định. LLM không còn tự cho
`score` - trước 2026-08-10 nó trả thẳng `score: 0-100` mà không chỗ nào định
nghĩa 85 khác 70 (nợ A1).

CQ1/CQ2 CỐ Ý KHÔNG ĐỂ LLM TỰ CHẤM MỨC. Hai tiêu chí đó là "đếm số lỗi rồi so
ngưỡng" - phần đếm và phần so ngưỡng đều là việc máy. LLM chỉ làm phần duy
nhất nó làm được: chỉ ra CHỖ NÀO sai, kèm trích dẫn nguyên văn. Máy đếm số
trích dẫn hợp lệ rồi quy mức. Nhờ vậy:
  - ngưỡng nằm ở scoring.yaml chứ không nằm trong đầu LLM
  - trích dẫn bịa bị loại bằng text_utils.trich_dan_co_that, đúng cơ chế đã
    dựng cho Compliance và Brand Voice (rubrics.md mục 2.5)

CẢNH BÁO ĐÃ BIẾT: CQ7 ("số liệu định lượng có nguồn") TRÙNG với CP8 của
Compliance - cùng định nghĩa, cùng ánh xạ mã lỗi B10. Bài có số liệu không
nguồn vì thế bị trừ điểm ở CẢ HAI agent (trọng số 0,25 và 0,30). Giữ nguyên
theo rubric đã chốt; ghi nhận ở docs/technical-debt.md để quyết sau.
"""
import config
import content_analysis as ca
from ai_core import call_agent
from prompt_builder import boc_noi_dung
from scoring import score_from_criteria
from text_utils import trich_dan_co_that

_FIELDS = ("title", "body", "summary")

# LLM liệt kê lỗi (máy đếm rồi quy mức)
_MA_LIET_KE = ("CQ1", "CQ2")
# LLM chấm mức trực tiếp
_MA_CHAM_MUC = ("CQ6", "CQ7", "CQ8")

_NHAN = {
    "CQ1": "Lỗi chính tả (CQ1)",
    "CQ2": "Lỗi ngữ pháp hoặc câu tối nghĩa (CQ2)",
    "CQ3": "Câu quá dài (CQ3)",
    "CQ4": "Đoạn quá dài (CQ4)",
    "CQ5": "Cấu trúc heading chưa đạt (CQ5)",
    "CQ6": "Nội dung lặp ý hoặc thiếu mạch lạc (CQ6)",
    "CQ7": "Số liệu định lượng không dẫn nguồn (CQ7)",
    "CQ8": "Tóm tắt (summary) thiếu hoặc không tóm đúng (CQ8)",
}


def _tieu_chi(ma: str, level, occurrences=None, suggestion="") -> dict:
    return {"id": ma, "level": level, "occurrences": occurrences or [],
            "suggestion": suggestion}


def _muc_theo_so_loi(n: int, ng: dict) -> int:
    """0 lỗi -> mức 2; 1-2 lỗi -> mức 1; >= `loi_nhieu` -> mức 0."""
    if n == 0:
        return 2
    return 0 if n >= ng["loi_nhieu"] else 1


# --------------------------------------------------------------- máy chấm


def _cq3_cau_qua_dai(body: str, ng: dict) -> dict:
    dai = ca.cau_qua_dai(body, ng["long_sentence_words"])
    muc = _muc_theo_so_loi(len(dai), ng)
    if muc == 2:
        return _tieu_chi("CQ3", 2)
    return _tieu_chi(
        "CQ3", muc,
        [{"field": "body", "text": c[:150]} for c in dai[:5]],
        f"{len(dai)} câu dài hơn {ng['long_sentence_words']} tiếng. "
        "Tách thành câu ngắn hơn để dễ đọc.",
    )


def _cq4_doan_qua_dai(body: str, ng: dict) -> dict:
    dai = ca.doan_qua_dai(body, ng["long_paragraph_sentences"])
    muc = _muc_theo_so_loi(len(dai), ng)
    if muc == 2:
        return _tieu_chi("CQ4", 2)
    return _tieu_chi(
        "CQ4", muc,
        [{"field": "body", "text": p[:150]} for p in dai[:5]],
        f"{len(dai)} đoạn dài hơn {ng['long_paragraph_sentences']} câu. "
        "Ngắt đoạn để bài dễ theo dõi.",
    )


def _cq5_cau_truc_heading(body: str, ng: dict) -> dict:
    """Bài ngắn không cần heading -> NA, không phải mức 2.

    Cho mức 2 là cộng điểm miễn phí cho mọi bài ngắn (rubrics.md mục 2.2).
    """
    h = ca.cau_truc_heading(body)
    if not h["co_h2"]:
        if ca.so_tu(body) > ng["heading_required_words"]:
            return _tieu_chi(
                "CQ5", 0, [{"field": "body", "text": "không có <h2>"}],
                f"Bài dài hơn {ng['heading_required_words']} từ nhưng không có "
                "heading <h2> nào. Chia bài thành các mục có tiêu đề.")
        return _tieu_chi("CQ5", None)
    if h["h3_truoc_h2"]:
        return _tieu_chi(
            "CQ5", 1, [{"field": "body", "text": "h3 đứng trước h2 đầu tiên"}],
            "Phân cấp heading lộn xộn: có <h3> trước <h2> đầu tiên.")
    return _tieu_chi("CQ5", 2)


# ------------------------------------------------------------------ LLM

_LLM_PROMPT = (
    "Bạn là biên tập viên nội dung marketing tiếng Việt. Bạn KHÔNG cho điểm. "
    "Điểm do hệ thống tính tất định từ những gì bạn báo cáo.\n\n"
    "KHÔNG đánh giá SEO, thương hiệu, hay tuân thủ pháp lý. Cũng KHÔNG nhận "
    "xét độ dài câu hay độ dài đoạn - hệ thống đã tự đếm.\n\n"
    "PHẦN 1 - LIỆT KÊ LỖI (trường `loi`):\n\n"
    "CQ1 - lỗi CHÍNH TẢ: sai dấu, sai âm, dính chữ, thiếu chữ.\n"
    "CQ2 - lỗi NGỮ PHÁP hoặc câu tối nghĩa: thiếu chủ ngữ, câu cụt, tối nghĩa.\n\n"
    "Mỗi lỗi một mục, kèm `evidence` là đoạn trích NGUYÊN VĂN chứa lỗi - copy "
    "chính xác từng chữ từ bài, không diễn giải, không sửa lại cho đúng. "
    "Không trích được nguyên văn thì KHÔNG báo lỗi đó.\n\n"
    "PHẦN 2 - CHẤM MỨC (trường `criteria`):\n\n"
    "CQ6 - Mạch lạc, không trùng lặp.\n"
    "  0 = có đoạn lặp ý rõ rệt hoặc lạc đề\n  1 = lặp nhẹ\n  2 = mạch lạc\n\n"
    "CQ7 - Số liệu định lượng có dẫn nguồn.\n"
    "  0 = có số liệu nhưng không nêu nguồn nào\n  1 = một phần có nguồn\n"
    "  2 = mọi số liệu đều có nguồn\n  NA = bài không có số liệu định lượng\n\n"
    "CQ8 - Tóm tắt (summary) có tóm đúng nội dung bài không? Hệ thống đã kiểm "
    "summary không trống.\n"
    "  1 = có nhưng không tóm đúng nội dung chính\n  2 = tóm đúng\n\n"
    "QUY TẮC: mức 0 và mức 1 luôn phải kèm `evidence` nguyên văn. Trả lời bằng "
    "tiếng Việt ở `suggestion`."
)

_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "loi": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ma": {"type": "string", "enum": list(_MA_LIET_KE)},
                    "field": {"type": "string", "enum": list(_FIELDS)},
                    "evidence": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["ma", "field", "evidence", "suggestion"],
                "additionalProperties": False,
            },
        },
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": list(_MA_CHAM_MUC)},
                    "muc": {"type": "string", "enum": ["0", "1", "2", "NA"]},
                    "field": {"type": "string", "enum": list(_FIELDS)},
                    "evidence": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["id", "muc", "field", "evidence", "suggestion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["loi", "criteria"],
    "additionalProperties": False,
}


def _danh_gia_llm(fields: dict, text_theo_field: dict, hoi_cq8: bool) -> dict:
    """Gọi LLM một lần. Trả {"loi": [...], "criteria": {ma -> tiêu chí}}.

    Lỗi nào trích dẫn không khớp nguyên văn thì LOẠI ngay ở đây - máy đếm số
    lỗi để quy mức, nên một trích dẫn bịa sẽ đẩy mức xuống oan.
    """
    noi_dung, _ = boc_noi_dung(fields, _FIELDS)
    kq = call_agent(_LLM_PROMPT, noi_dung, _LLM_SCHEMA)

    loi = [
        d for d in kq["loi"]
        if d["ma"] in _MA_LIET_KE
        and trich_dan_co_that(d["evidence"], text_theo_field)
    ]

    theo_ma = {}
    for c in kq["criteria"]:
        ma = c["id"]
        if ma not in _MA_CHAM_MUC or ma in theo_ma:
            continue
        if ma == "CQ8" and not hoi_cq8:
            continue      # máy đã chốt CQ8 = mức 0 (summary trống)
        muc = None if c["muc"] == "NA" else int(c["muc"])
        # Hạ mức mà không trích được nguyên văn -> không được hạ. Cùng quy tắc
        # với BV6 (nợ B7) và CP2: mức 2 nghĩa là "không tìm thấy vấn đề", nên
        # đó là kết luận đúng khi thiếu bằng chứng.
        if muc in (0, 1) and not trich_dan_co_that(c["evidence"], text_theo_field):
            muc = 2
        occ = ([{"field": c["field"], "text": c["evidence"]}]
               if muc in (0, 1) else [])
        theo_ma[ma] = _tieu_chi(ma, muc, occ,
                                c["suggestion"] if muc in (0, 1) else "")
    return {"loi": loi, "criteria": theo_ma}


def _muc_tu_danh_sach_loi(ma: str, loi: list, ng: dict) -> dict:
    """Đếm lỗi LLM liệt kê (đã lọc trích dẫn) -> mức. Máy quy, không phải LLM."""
    cua_ma = [d for d in loi if d["ma"] == ma]
    muc = _muc_theo_so_loi(len(cua_ma), ng)
    if muc == 2:
        return _tieu_chi(ma, 2)
    return _tieu_chi(
        ma, muc,
        [{"field": d["field"], "text": d["evidence"]} for d in cua_ma[:5]],
        "; ".join(dict.fromkeys(d["suggestion"] for d in cua_ma[:3])),
    )


# ------------------------------------------------------------------- ghép


def _issues_from_criteria(criteria: list) -> list:
    issues = []
    for c in criteria:
        if c["level"] not in (0, 1):
            continue
        for o in c["occurrences"] or [{"field": "body", "text": ""}]:
            issues.append({
                "field": o.get("field") or "body",
                "type": _NHAN[c["id"]],
                "suggestion": c["suggestion"],
                "excerpt": o.get("text", ""),
            })
    return issues


def run(fields: dict, *, danh_gia_llm=_danh_gia_llm,
        content_type: str = "cam_nang", langcode: str = "vi") -> dict | None:
    """Chấm Content Quality. Trả None khi không tiêu chí nào áp dụng được."""
    from text_utils import strip_html

    ng = config.load(content_type, langcode)["scoring"]
    text_theo_field = {f: strip_html(fields.get(f) or "") for f in _FIELDS}

    if not any(t.strip() for t in text_theo_field.values()):
        return None      # bài rỗng

    summary_trong = not (fields.get("summary") or "").strip()

    try:
        kq = danh_gia_llm(fields, text_theo_field, not summary_trong)
        loi, tu_llm, llm_hong = kq["loi"], kq["criteria"], False
    except Exception:
        # LLM lỗi -> CQ1/CQ2/CQ6/CQ7/CQ8 thành NA, KHÔNG phải mức 2.
        # Mức 2 sẽ là "không tìm thấy lỗi chính tả nào" trong khi thực ra chưa
        # ai đi tìm - đúng loại điểm miễn phí rubrics.md mục 2.2 cảnh báo.
        loi, tu_llm, llm_hong = [], {}, True

    def cq12(ma):
        return (_tieu_chi(ma, None) if llm_hong
                else _muc_tu_danh_sach_loi(ma, loi, ng))

    cq8 = (_tieu_chi("CQ8", 0, [{"field": "summary", "text": ""}],
                     "Bài chưa có tóm tắt (summary).")
           if summary_trong else tu_llm.get("CQ8") or _tieu_chi("CQ8", None))

    criteria = [
        cq12("CQ1"),
        cq12("CQ2"),
        _cq3_cau_qua_dai(fields.get("body", ""), ng),
        _cq4_doan_qua_dai(fields.get("body", ""), ng),
        _cq5_cau_truc_heading(fields.get("body", ""), ng),
        tu_llm.get("CQ6") or _tieu_chi("CQ6", None),
        tu_llm.get("CQ7") or _tieu_chi("CQ7", None),
        cq8,
    ]

    score = score_from_criteria(criteria)
    if score is None:
        return None
    return {
        "score": score,
        "issues": _issues_from_criteria(criteria),
        "criteria": criteria,
        # Giữ trường cũ để graph.py và module PHP không phải đổi. Rubric không
        # có tiêu chí nào về "điểm mạnh" nên nó luôn rỗng - bỏ hẳn sẽ phải sửa
        # cả hai phía, không đáng cho một trường không ai đọc.
        "strengths": [],
    }

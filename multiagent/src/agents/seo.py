"""SEO Agent - chấm theo rubric SEO1-SEO10 (docs/rubrics.md mục 4).

Hai cách đo:
  SEO1, SEO3, SEO7, SEO10          máy hoàn toàn
  SEO5, SEO8, SEO9                 máy quyết mức 0, LLM phân biệt mức 1/2
  SEO2, SEO4, SEO6                 LLM (cần hiểu "từ khoá xuất hiện tự nhiên")

Điểm do `scoring.score_from_criteria()` tính tất định. LLM không còn tự cho
`score` - trước 2026-08-10 nó trả thẳng `score: 0-100` mà không chỗ nào định
nghĩa 85 khác 70 ở điểm gì (nợ A1).

VÌ SAO SEO CHUYỂN TRƯỚC content_quality: 7/10 tiêu chí đo được bằng máy, nên
chuyển sang rubric nhiều khả năng LÀM GIẢM dao động điểm. Compliance thì
ngược lại (4/8 tiêu chí do LLM chấm) và σ đã tăng khi chuyển - xem
docs/rubrics.md mục 9.1. Thứ tự này là để rủi ro tăng dần, không phải tuỳ ý.

`main_keyword` giữ nguyên trong output: nó là đầu vào chung của SEO2/4/6/8 và
phải nhất quán trong cùng một lần chấm (rubrics.md mục 4).
"""
import config
import seo_analysis as sa
from ai_core import call_agent
from prompt_builder import boc_noi_dung
from scoring import score_from_criteria

_FIELDS = ("title", "meta_description", "url_alias", "body", "image_alt")

# Bốn tiêu chí LLM chấm mức trọn vẹn, hai tiêu chí LLM chỉ phân biệt mức 1/2
# (máy đã loại mức 0). Xem `_MAY_CHOT_MUC_0`.
_MA_LLM = ("SEO2", "SEO4", "SEO5", "SEO6", "SEO8", "SEO9")

# Với ba mã này, máy đã kết luận được mức 0 (trống / không có h2 / thiếu alt).
# LLM chỉ được hỏi khi máy CHƯA loại - nếu không, LLM có thể "cứu" một bài
# thiếu alt lên mức 2 chỉ vì nó không đọc kỹ.
_MAY_CHOT_MUC_0 = ("SEO5", "SEO8", "SEO9")

_NHAN = {
    "SEO1": "Độ dài tiêu đề chưa tối ưu (SEO1)",
    "SEO2": "Tiêu đề thiếu từ khoá chính (SEO2)",
    "SEO3": "Meta description trống hoặc sai độ dài (SEO3)",
    "SEO4": "Meta description thiếu từ khoá (SEO4)",
    "SEO5": "Đường dẫn chưa đạt chuẩn SEO (SEO5)",
    "SEO6": "Từ khoá không xuất hiện trong phần mở đầu (SEO6)",
    "SEO7": "Nội dung quá ngắn so với chuẩn SEO (SEO7)",
    "SEO8": "Heading không mang từ khoá (SEO8)",
    "SEO9": "Alt text của ảnh thiếu hoặc chung chung (SEO9)",
    "SEO10": "Thiếu internal link (SEO10)",
}


def _tieu_chi(ma: str, level, occurrences=None, suggestion="") -> dict:
    return {"id": ma, "level": level, "occurrences": occurrences or [],
            "suggestion": suggestion}


def _o(field: str, text: str) -> list:
    return [{"field": field, "text": text}]


# --------------------------------------------------------------- máy chấm


def _seo1_do_dai_title(title: str, ng: dict) -> dict:
    if not (title or "").strip():
        return _tieu_chi("SEO1", 0, _o("title", ""), "Tiêu đề đang trống.")
    n = sa.do_title(title)["so_ky_tu"]
    ly_tuong, chap_nhan = ng["title_ideal"], ng["title_acceptable"]
    if ly_tuong[0] <= n <= ly_tuong[1]:
        return _tieu_chi("SEO1", 2)
    if chap_nhan[0] <= n <= chap_nhan[1]:
        return _tieu_chi("SEO1", 1, _o("title", title),
                         f"Tiêu đề {n} ký tự. Dải lý tưởng là "
                         f"{ly_tuong[0]}-{ly_tuong[1]} ký tự.")
    return _tieu_chi("SEO1", 0, _o("title", title),
                     f"Tiêu đề {n} ký tự, ngoài dải chấp nhận được "
                     f"{chap_nhan[0]}-{chap_nhan[1]} ký tự.")


def _seo3_do_dai_meta(meta: str, ng: dict) -> dict:
    d = sa.do_meta(meta)
    if d["trong"]:
        return _tieu_chi("SEO3", 0, _o("meta_description", ""),
                         "Meta description đang trống. Thêm mô tả "
                         f"{ng['meta_ideal'][0]}-{ng['meta_ideal'][1]} ký tự.")
    lo, hi = ng["meta_ideal"]
    if lo <= d["so_ky_tu"] <= hi:
        return _tieu_chi("SEO3", 2)
    return _tieu_chi("SEO3", 1, _o("meta_description", meta),
                     f"Meta description {d['so_ky_tu']} ký tự, ngoài dải "
                     f"{lo}-{hi}.")


def _seo7_do_dai_body(body: str, ng: dict) -> dict:
    n = sa.do_body(body)["so_tu"]
    if n < ng["body_thin_words"]:
        return _tieu_chi("SEO7", 0, _o("body", f"{n} từ"),
                         f"Bài chỉ {n} từ, dưới mức {ng['body_thin_words']} từ. "
                         "Nội dung quá mỏng để xếp hạng tìm kiếm.")
    if n >= ng["body_min_words"]:
        return _tieu_chi("SEO7", 2)
    return _tieu_chi("SEO7", 1, _o("body", f"{n} từ"),
                     f"Bài {n} từ. Đạt chuẩn là từ {ng['body_min_words']} từ.")


def _seo10_internal_link(body: str, ng: dict) -> dict:
    n = sa.do_body(body)["so_link"]
    if n >= ng["internal_link_min"]:
        return _tieu_chi("SEO10", 2)
    if n == 0:
        return _tieu_chi("SEO10", 0, _o("body", "0 link"),
                         "Bài không có internal link nào.")
    return _tieu_chi("SEO10", 1, _o("body", f"{n} link"),
                     f"Bài có {n} internal link. Nên có ít nhất "
                     f"{ng['internal_link_min']}.")


# ------------------------------------------- máy chốt mức 0, LLM phần còn lại


def _may_chot_muc_0(fields: dict, ng: dict) -> dict:
    """Mã -> tiêu chí mức 0 mà máy tự kết luận được, hoặc NA.

    Trả dict CHỈ chứa mã đã chốt. Mã không có trong dict nghĩa là máy không
    loại được, phải hỏi LLM.
    """
    ra = {}

    u = sa.do_url(fields.get("url_alias", ""))
    if u["trong"]:
        ra["SEO5"] = _tieu_chi("SEO5", 0, _o("url_alias", ""),
                               "Đường dẫn đang trống.")
    elif u["co_dau"]:
        ra["SEO5"] = _tieu_chi("SEO5", 0, _o("url_alias", fields["url_alias"]),
                               "Đường dẫn còn dấu tiếng Việt.")

    b = sa.do_body(fields.get("body", ""))
    if b["so_h2"] == 0:
        ra["SEO8"] = _tieu_chi("SEO8", 0, _o("body", "không có <h2>"),
                               "Bài không có heading <h2> nào.")

    a = sa.do_anh(fields.get("image_alt", ""))
    if not a["co_anh"]:
        # Bài không ảnh thì tiêu chí không áp dụng. NA chứ KHÔNG phải mức 2 -
        # cho mức 2 là cộng điểm miễn phí cho mọi bài không có ảnh
        # (rubrics.md mục 2.2).
        ra["SEO9"] = _tieu_chi("SEO9", None)
    elif a["so_thieu"]:
        ra["SEO9"] = _tieu_chi(
            "SEO9", 0,
            [{"field": "image_alt", "text": t} for t in a["thieu_alt"]],
            f"{a['so_thieu']}/{a['so_anh']} ảnh thiếu alt text.")

    return ra


# ------------------------------------------------------------------ LLM

_LLM_PROMPT = (
    "Bạn là chuyên gia SEO. Bạn KHÔNG cho điểm - chỉ chấm MỨC cho từng tiêu "
    "chí dưới đây. Điểm do hệ thống tính tất định từ các mức bạn chấm.\n\n"
    "Trước hết, rút ra TỪ KHOÁ CHÍNH của bài từ tiêu đề (`main_keyword`). Dùng "
    "đúng từ khoá đó cho mọi tiêu chí bên dưới.\n\n"
    "SEO2 - Tiêu đề có chứa từ khoá chính không?\n"
    "  0 = không chứa\n  2 = có chứa\n\n"
    "SEO4 - Meta description có chứa từ khoá không?\n"
    "  0 = không chứa\n  2 = có chứa\n"
    "  NA = meta description trống\n\n"
    "SEO5 - Đường dẫn có chứa từ khoá và ngắn gọn không? (hệ thống đã kiểm "
    "đường dẫn không trống và không dấu)\n"
    "  1 = hợp lệ nhưng thiếu từ khoá hoặc quá dài\n"
    "  2 = ngắn gọn, có từ khoá\n\n"
    "SEO6 - Từ khoá chính có xuất hiện trong đoạn mở đầu không? Chỉ xét phần "
    "trong thẻ <dau_bai>, hệ thống đã cắt sẵn.\n"
    "  0 = không xuất hiện\n  2 = có xuất hiện\n\n"
    "SEO8 - Có heading nào chứa từ khoá chính hoặc biến thể không? Danh sách "
    "heading nằm trong thẻ <danh_sach_heading>.\n"
    "  1 = có heading nhưng không heading nào chứa từ khoá\n"
    "  2 = có ít nhất một heading chứa từ khoá\n\n"
    "SEO9 - Alt text của ảnh có mô tả đúng nội dung không? (hệ thống đã kiểm "
    "mọi ảnh đều CÓ alt)\n"
    "  1 = alt chung chung, vô nghĩa ('hình ảnh', 'anh1', 'image')\n"
    "  2 = alt mô tả được nội dung ảnh\n\n"
    "QUY TẮC BẮT BUỘC:\n\n"
    "1. Chỉ chấm các mã được liệt kê ở trên. Mã nào hệ thống không hỏi thì "
    "đừng trả về.\n\n"
    "2. NA nghĩa là 'không có gì để xét', KHÔNG phải 'bài làm đúng'.\n\n"
    "3. KHÔNG đánh giá chính tả, văn phong, thương hiệu hay tuân thủ pháp lý.\n\n"
    "4. Trả lời bằng tiếng Việt ở trường `suggestion`."
)

_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "main_keyword": {"type": "string"},
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "enum": list(_MA_LLM)},
                    # Chuỗi thay vì số để biểu diễn NA trong một enum duy nhất
                    # - schema strict không nhận kiểu hợp (integer | null).
                    "muc": {"type": "string", "enum": ["0", "1", "2", "NA"]},
                    "field": {"type": "string", "enum": list(_FIELDS)},
                    "suggestion": {"type": "string"},
                },
                "required": ["id", "muc", "field", "suggestion"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["main_keyword", "criteria"],
    "additionalProperties": False,
}


def _danh_gia_llm(fields: dict, can_hoi: tuple) -> dict:
    """Gọi LLM một lần. Trả {"main_keyword": str, "criteria": {ma -> tiêu chí}}.

    M1 + M3 qua `prompt_builder.boc_noi_dung` (docs/prompt-injection.md mục 5).
    Thêm hai khối máy cắt sẵn - đoạn mở đầu và danh sách heading - để LLM khỏi
    phải tự đếm 100 từ hay tự lọc thẻ, hai việc máy làm chính xác hơn.
    """
    noi_dung, _ = boc_noi_dung(fields, _FIELDS, boc_an_o=("body",))
    b = sa.do_body(fields.get("body", ""))
    noi_dung += (
        f"\n\n<dau_bai>{sa.dau_body(fields.get('body', ''))}</dau_bai>"
        f"\n<danh_sach_heading>{' | '.join(b['heading'])}</danh_sach_heading>"
        f"\n\nChỉ chấm các mã sau: {', '.join(can_hoi)}"
    )
    kq = call_agent(_LLM_PROMPT, noi_dung, _LLM_SCHEMA)

    theo_ma = {}
    for c in kq["criteria"]:
        ma = c["id"]
        if ma not in can_hoi or ma in theo_ma:
            continue      # mã lạ, mã không hỏi, hoặc chấm trùng -> giữ lần đầu
        muc = None if c["muc"] == "NA" else int(c["muc"])
        # Máy đã loại mức 0 cho ba mã này rồi (chúng không nằm trong `can_hoi`
        # nếu máy đã chốt). LLM vẫn trả 0 thì kéo về 1 - nó không có thẩm
        # quyền kết luận mức 0 ở đây, phần đó đo bằng máy.
        if ma in _MAY_CHOT_MUC_0 and muc == 0:
            muc = 1
        occ = _o(c["field"], "") if muc in (0, 1) else []
        theo_ma[ma] = _tieu_chi(ma, muc, occ,
                                c["suggestion"] if muc in (0, 1) else "")
    return {"main_keyword": kq.get("main_keyword", ""), "criteria": theo_ma}


# ------------------------------------------------------------------- ghép


def _issues_from_criteria(criteria: list) -> list:
    """Tiêu chí mức 0/1 -> issue. Mức 2 và NA không sinh gì.

    Giữ hình dạng {field, type, suggestion} vì `graph._issue_to_json` và module
    PHP `vf_ai_review` đều đọc theo hình dạng đó.
    """
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
    """Chấm SEO. Trả None khi không tiêu chí nào áp dụng được.

    None nghĩa là CHƯA CHẤM ĐƯỢC, khác hẳn 0 điểm - Aggregator sẽ chia lại
    trọng số và ghi `note` (architecture.md mục 6.4).

    `danh_gia_llm` tiêm được để test không gọi LLM.
    """
    ng = config.load(content_type, langcode)["scoring"]

    if not any((fields.get(f) or "").strip() for f in _FIELDS):
        return None      # bài rỗng: không có gì để chấm

    da_chot = _may_chot_muc_0(fields, ng)
    can_hoi = tuple(m for m in _MA_LLM if m not in da_chot)

    tu_llm, main_keyword = {}, ""
    unavailable_checks = []
    if can_hoi:
        try:
            kq = danh_gia_llm(fields, can_hoi)
            tu_llm = kq["criteria"]
            main_keyword = kq.get("main_keyword", "")
            # Callback hop le nhung bo sot ma duoc hoi van la assessment
            # khong day du; khong duoc ngam coi NA la da danh gia.
            unavailable_checks = [m for m in can_hoi if m not in tu_llm]
        except Exception:
            # LLM lỗi -> các mã nó phụ trách thành NA (bị loại khỏi cả tử số
            # lẫn mẫu số), KHÔNG phải 0. Bốn tiêu chí máy chấm vẫn ra điểm -
            # đúng kiểu suy giảm có kiểm soát mà Brand Voice đã chứng minh khi
            # API hết hạn mức (technical-debt.md mục 5).
            tu_llm = {}
            unavailable_checks = list(can_hoi)

    def lay(ma):
        """Tiêu chí LLM chấm. Máy đã chốt -> dùng của máy. LLM lỗi/thiếu -> NA."""
        if ma in da_chot:
            return da_chot[ma]
        return tu_llm.get(ma) or _tieu_chi(ma, None)

    criteria = [
        _seo1_do_dai_title(fields.get("title", ""), ng),
        lay("SEO2"),
        _seo3_do_dai_meta(fields.get("meta_description", ""), ng),
        lay("SEO4"),
        lay("SEO5"),
        lay("SEO6"),
        _seo7_do_dai_body(fields.get("body", ""), ng),
        lay("SEO8"),
        lay("SEO9"),
        _seo10_internal_link(fields.get("body", ""), ng),
    ]

    score = score_from_criteria(criteria)
    if score is None:
        return None
    return {
        "score": score,
        "main_keyword": main_keyword,
        "issues": _issues_from_criteria(criteria),
        "criteria": criteria,
        "unavailable_checks": unavailable_checks,
    }

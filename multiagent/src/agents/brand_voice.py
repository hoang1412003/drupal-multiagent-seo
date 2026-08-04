"""Brand Voice Agent - chấm theo rubric BV1-BV7 (docs/rubrics.md mục 5).

Sáu tiêu chí (BV1-BV5, BV7) đo bằng regex, đối chiếu brand_rules.json sinh
từ corpus BRAND. Chỉ BV6 (mức độ trang trọng) cần LLM + RAG.

Điểm do src/scoring.py tính TẤT ĐỊNH từ các mức, KHÔNG để LLM tự cho điểm -
lý do đầy đủ ở docs/rubrics.md mục 1.

Quy tắc an toàn: quy ước nào corpus chưa đủ căn cứ để chốt (docs/brand/
brand_guideline.md mục "Chưa đủ căn cứ") thì tiêu chí tương ứng trả NA, bị
loại khỏi cả tử số lẫn mẫu số - KHÔNG cho 0 điểm. Đây không phải trường hợp
lý thuyết: corpus 16 bài cho thấy VinFast không có quy ước xưng hô thống
nhất, nên BV4 luôn NA ở phạm vi hiện tại.
"""
import json
import os

from ai_core import call_agent
from brand_analysis import classify_title_case, count_model_name_usage, count_variants
from prompt_builder import boc_noi_dung
from retrieval import COLLECTION_BRAND, retrieve
from scoring import score_from_criteria
from text_utils import strip_html

_RULES_PATH = os.path.join(os.path.dirname(__file__), "brand_rules.json")
_rules_cache = None

# Các field Brand Voice đọc (docs/rubrics.md mục 5)
_FIELDS = ("title", "body", "summary")

# Ngưỡng đếm lấy nguyên docs/rubrics.md mục 5 - giá trị TẠM chờ calibrate
# Sprint 3. Từ ngưỡng trở lên là mức 0; từ 1 đến dưới ngưỡng là mức 1.
_NGUONG_MUC_0 = 3

# Ứng viên xưng hô để phát hiện lẫn lộn. Trùng danh sách trong
# docs/brand/variant_candidates.json - giữ ở đây vì brand_rules.json chỉ lưu
# kiểu CHUẨN, còn BV3 cần biết cả các kiểu khác để đếm số kiểu bị lẫn.
_UNG_VIEN_XUNG_HO = ["bạn", "quý khách", "khách hàng", "người dùng"]

_NHAN = {
    "BV1": "Sai cách viết tên model (BV1)",
    "BV2": "Dùng thuật ngữ không chuẩn (BV2)",
    "BV3": "Xưng hô không nhất quán (BV3)",
    "BV4": "Xưng hô khác chuẩn thương hiệu (BV4)",
    "BV5": "Tiêu đề sai quy ước viết hoa (BV5)",
    "BV6": "Giọng văn lệch chuẩn thương hiệu (BV6)",
    "BV7": "Dùng từ bị guideline loại (BV7)",
}


def _load_rules() -> dict:
    global _rules_cache
    if _rules_cache is None:
        with open(_RULES_PATH, encoding="utf-8") as f:
            _rules_cache = json.load(f)
    return _rules_cache


def _muc_theo_so_cho(so_cho: int) -> int:
    """Đếm được bao nhiêu chỗ sai -> mức. 0 chỗ = đạt, >=3 chỗ = không đạt."""
    if so_cho == 0:
        return 2
    return 0 if so_cho >= _NGUONG_MUC_0 else 1


def _tieu_chi(ma: str, level, occurrences=None, suggestion="", truy_van="") -> dict:
    """`truy_van` là cụm dùng để tìm đoạn trích LÀM BẰNG CHỨNG trong corpus.

    Phải là chính CỤM CHUẨN mà bài đang dùng sai (VD "ô tô điện"), không phải
    câu gợi ý sửa - câu gợi ý là chỉ dẫn cho người đọc, đem đi truy vấn ngữ
    nghĩa sẽ lấy về đoạn không liên quan. Tiêu chí không có cụm chuẩn nào để
    minh hoạ (BV3 nhất quán nội bộ, BV5 viết hoa) thì để rỗng -> bỏ qua.
    """
    return {
        "id": ma,
        "level": level,
        "occurrences": occurrences or [],
        "suggestion": suggestion,
        "truy_van": truy_van,
        "reference": "",     # đoạn trích corpus, do _dinh_bang_chung điền
    }


def _dang_chuan_cua(sai_text: str, canonicals: list[str]) -> str:
    """'VF8'/'vf8' -> 'VF 8'. So sau khi bỏ dấu cách và hoa/thường."""
    chuan_hoa = sai_text.replace(" ", "").lower()
    for c in canonicals:
        if c.replace(" ", "").lower() == chuan_hoa:
            return c
    return ""


def _bv1_ten_model(text_theo_field: dict, rules: dict) -> dict:
    tong_dung, sai = 0, []
    for field, text in text_theo_field.items():
        dung, cac_cho_sai = count_model_name_usage(text, rules["model_names"])
        tong_dung += dung
        sai.extend({"field": field, "text": t} for t in cac_cho_sai)
    if tong_dung == 0 and not sai:
        # Bài không nhắc model nào -> NA, KHÔNG phải mức 2 (mức 2 nghĩa là
        # "có nhắc và viết đúng"), nếu không mọi bài không nhắc model đều
        # được cộng điểm miễn phí.
        return _tieu_chi("BV1", None)
    chuan = ", ".join(f"'{m}'" for m in rules["model_names"])
    # Truy vấn bằng chứng: dạng chuẩn của chính model bị viết sai đầu tiên.
    truy_van = _dang_chuan_cua(sai[0]["text"], rules["model_names"]) if sai else ""
    return _tieu_chi(
        "BV1", _muc_theo_so_cho(len(sai)), sai,
        f"Viết tên model đúng dạng chuẩn ({chuan})." if sai else "",
        truy_van,
    )


def _bv2_thuat_ngu(text_theo_field: dict, rules: dict) -> dict:
    if not rules["terms"]:
        return _tieu_chi("BV2", None)     # corpus chưa đủ căn cứ chốt thuật ngữ
    sai, co_nhac, goi_y, truy_van = [], False, [], ""
    for term in rules["terms"]:
        bien_the = [term["standard"]] + term["non_standard"]
        for field, text in text_theo_field.items():
            dem = count_variants(text, bien_the)
            if dem[term["standard"]]:
                co_nhac = True
            for v in term["non_standard"]:
                if dem[v]:
                    co_nhac = True
                    sai.extend({"field": field, "text": v} for _ in range(dem[v]))
                    so_bai, tong = term["docs"]
                    goi_y.append(
                        f"Dùng '{term['standard']}' thay cho '{v}' "
                        f"({so_bai}/{tong} bài chuẩn dùng cách này)."
                    )
                    # Truy vấn bằng chứng: thuật ngữ CHUẨN của nhóm đầu tiên
                    # bị dùng sai, để lấy về đoạn văn thật đang dùng đúng.
                    truy_van = truy_van or term["standard"]
    if not co_nhac:
        return _tieu_chi("BV2", None)
    return _tieu_chi("BV2", _muc_theo_so_cho(len(sai)), sai,
                     " ".join(dict.fromkeys(goi_y)), truy_van)


def _dem_xung_ho(text_theo_field: dict) -> dict[str, int]:
    """Đếm mọi kiểu xưng hô xuất hiện trong bài.

    Không phụ thuộc brand_rules.json: BV3 (nhất quán trong bài) đo được kể
    cả khi corpus chưa chốt được chuẩn - đây là hai câu hỏi khác nhau.
    """
    tong = {v: 0 for v in _UNG_VIEN_XUNG_HO}
    for text in text_theo_field.values():
        for v, so in count_variants(text, _UNG_VIEN_XUNG_HO).items():
            tong[v] += so
    return {v: so for v, so in tong.items() if so}


def _bv3_nhat_quan(dem: dict) -> dict:
    if not dem:
        return _tieu_chi("BV3", None)     # bài không xưng hô với người đọc
    so_kieu = len(dem)
    level = 2 if so_kieu == 1 else (1 if so_kieu == 2 else 0)
    if level == 2:
        return _tieu_chi("BV3", 2)
    return _tieu_chi(
        "BV3", level,
        [{"field": "body", "text": v} for v in dem],
        f"Bài lẫn {so_kieu} kiểu xưng hô ({', '.join(dem)}) - chọn một kiểu duy nhất.",
    )


def _bv4_khop_corpus(dem: dict, rules: dict) -> dict:
    if not dem or not rules["address_form"]:
        # address_form = None nghĩa là corpus KHÔNG có quy ước xưng hô thống
        # nhất (trường hợp thật của dự án). Không có chuẩn thì không có gì để
        # đối chiếu -> NA, không được quy thành lỗi của bài viết.
        return _tieu_chi("BV4", None)
    chuan = rules["address_form"]["standard"]
    dung_nhieu_nhat = max(dem, key=lambda k: dem[k])
    if dung_nhieu_nhat == chuan:
        return _tieu_chi("BV4", 2)
    so_bai, tong = rules["address_form"]["docs"]
    return _tieu_chi(
        "BV4", 0, [{"field": "body", "text": dung_nhieu_nhat}],
        f"Bài xưng hô '{dung_nhieu_nhat}', chuẩn thương hiệu là '{chuan}' "
        f"({so_bai}/{tong} bài).",
        chuan,
    )


def _bv5_viet_hoa_title(title: str, rules: dict) -> dict:
    if not title.strip():
        return _tieu_chi("BV5", None)
    kieu = classify_title_case(title)
    if kieu == "ALL_CAPS":
        # Luôn là mức 0 kể cả khi corpus chưa chốt được quy ước - đây là mã
        # lỗi B4 đã ghi trong docs/goldset/annotation-guideline.md.
        return _tieu_chi(
            "BV5", 0, [{"field": "title", "text": title}],
            "Tiêu đề viết hoa toàn bộ - viết lại theo quy ước thường.",
        )
    if not rules["title_case"]:
        return _tieu_chi("BV5", None)     # corpus chưa đủ căn cứ
    if kieu == rules["title_case"]["standard"]:
        return _tieu_chi("BV5", 2)
    return _tieu_chi(
        "BV5", 1, [{"field": "title", "text": title}],
        f"Tiêu đề dùng kiểu {kieu}, chuẩn thương hiệu là "
        f"{rules['title_case']['standard']}.",
    )


def _co_nhac_nhom_thuat_ngu(text_theo_field: dict, rules: dict) -> bool:
    """Bài có nói tới khái niệm nào trong các nhóm thuật ngữ không?

    Gộp cả dạng chuẩn, dạng thiểu số lẫn dạng bị loại - chỉ cần một trong số
    đó xuất hiện là bài có bàn tới khái niệm ấy.
    """
    moi_dang = list(rules["excluded_terms"])
    for term in rules["terms"]:
        moi_dang.append(term["standard"])
        moi_dang.extend(term["non_standard"])
    if not moi_dang:
        return False
    return any(
        sum(count_variants(text, moi_dang).values())
        for text in text_theo_field.values()
    )


def _bv7_tu_bi_loai(text_theo_field: dict, rules: dict) -> dict:
    bi_loai = rules["excluded_terms"]
    if not bi_loai:
        return _tieu_chi("BV7", None)
    tim_thay = []
    for field, text in text_theo_field.items():
        for v, so in count_variants(text, bi_loai).items():
            if so:
                tim_thay.append({"field": field, "text": v})
    if not tim_thay:
        # Không dùng từ bị loại. Nhưng chỉ tính là ĐẠT nếu bài có thật sự
        # bàn tới khái niệm ấy - bài không nói gì về xe máy thì "không gọi
        # sai tên xe máy" là thoả mãn RỖNG, không chứng minh được gì. Cho
        # mức 2 ở đây chính là "tiêu chí thành hằng số" mà rubrics.md mục
        # 2.2 cảnh báo: mọi bài ngắn/lạc chủ đề đều được cộng điểm miễn phí.
        if not _co_nhac_nhom_thuat_ngu(text_theo_field, rules):
            return _tieu_chi("BV7", None)
        return _tieu_chi("BV7", 2)
    return _tieu_chi(
        "BV7", 0, tim_thay,
        "Từ này không xuất hiện lần nào trong corpus chuẩn - dùng cách diễn "
        "đạt khác.",
    )


_BV6_PROMPT = (
    "Bạn đối chiếu MỨC ĐỘ TRANG TRỌNG của một bài viết marketing tiếng Việt "
    "với các đoạn văn mẫu đã qua kiểm duyệt của cùng thương hiệu.\n"
    "Chấm 1 mức duy nhất:\n"
    "- 2: giọng văn khớp các đoạn mẫu.\n"
    "- 1: hơi lệch (trang trọng hơn hoặc suồng sã hơn rõ rệt ở vài chỗ).\n"
    "- 0: lệch rõ so với các đoạn mẫu.\n"
    "Khi chấm mức 0 hoặc 1, BẮT BUỘC trích NGUYÊN VĂN một cụm từ trong bài "
    "làm bằng chứng; không trích được nguyên văn thì phải chấm mức 2.\n"
    "Chỉ xét giọng văn. KHÔNG xét chính tả, SEO, hay tính tuân thủ pháp lý.\n"
    "Trả lời bằng tiếng Việt."
)

_BV6_SCHEMA = {
    "type": "object",
    "properties": {
        "level": {"type": "integer", "enum": [0, 1, 2]},
        "evidence": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["level", "evidence", "reason"],
    "additionalProperties": False,
}


def _judge_formality(fields: dict, *, content_type: str = "cam_nang",
                     langcode: str = "vi", retriever=retrieve) -> dict:
    """BV6: lấy đoạn mẫu cùng chủ đề rồi để LLM so giọng văn.

    Đây là chỗ RAG làm được việc mà nhét cứng một đoạn cố định không làm
    được: đoạn văn mẫu phải thay đổi theo chủ đề từng bài (docs/rag-design.md
    mục 3a).
    """
    truy_van = fields.get("title") or fields.get("summary") or ""
    if not truy_van.strip():
        return _tieu_chi("BV6", None)

    hits = retriever(truy_van, content_type, langcode, top_k=3,
                     collection_name=COLLECTION_BRAND)
    if not hits:
        # Không lấy được đoạn mẫu -> không có gì để đối chiếu -> NA, KHÔNG
        # phải 0. Lỗi hạ tầng không được biến thành hình phạt lên nội dung.
        return _tieu_chi("BV6", None)

    khoi, _ = boc_noi_dung(fields, ("title", "summary", "body"))
    doan_mau = "\n\n".join(f"[Đoạn mẫu {i + 1}] {h['text']}" for i, h in enumerate(hits))
    kq = call_agent(_BV6_PROMPT, f"{doan_mau}\n\n{khoi}", _BV6_SCHEMA)

    level = kq["level"]
    # rubrics.md mục 2.5 đòi trích dẫn NGUYÊN VĂN, nhưng chỗ này mới chỉ kiểm
    # chuỗi KHÁC RỖNG - tức LLM trả về bất kỳ ký tự nào cũng qua, kể cả một
    # câu bịa hoàn toàn. Đừng đọc nhầm nó thành cơ chế chống bịa đầy đủ.
    #
    # Phép kiểm thật là compliance._trich_dan_co_that() (so nguyên văn, xét
    # theo mảnh). Dùng lại được ở đây, nhưng phải chuyển nó ra chỗ dùng chung
    # trước - nợ B7 trong docs/technical-debt.md. BV6 là tiêu chí LLM DUY NHẤT
    # của agent này (6/7 tiêu chí kia là regex), nên nó là toàn bộ bề mặt bịa
    # lỗi của Brand Voice.
    if level in (0, 1) and not kq["evidence"].strip():
        level = 2
    if level == 2:
        return _tieu_chi("BV6", 2)
    return _tieu_chi(
        "BV6", level,
        [{"field": "body", "text": kq["evidence"]}],
        kq["reason"],
    )


def _bv6_giong_van(fields: dict, judge_bv6, content_type: str, langcode: str,
                   retriever) -> dict:
    """BV6 cần LLM + RAG. Lỗi bất kỳ -> NA, KHÔNG phải 0 (spec mục 7.2)."""
    if judge_bv6 is None:
        return _tieu_chi("BV6", None)
    try:
        return judge_bv6(fields, content_type=content_type, langcode=langcode,
                         retriever=retriever)
    except Exception:
        return _tieu_chi("BV6", None)


def _dinh_bang_chung(criteria: list[dict], retriever, content_type: str,
                     langcode: str) -> None:
    """Đính đoạn trích thật từ corpus vào các tiêu chí bị hạ mức.

    Đây là vai trò thứ hai của RAG (docs/rag-design.md mục 3b), và là phần
    làm nó có giá trị vượt xa một tiêu chí: regex phát hiện lỗi, RAG CHỨNG
    MINH quy ước. Người viết đọc gợi ý là kiểm chứng được ngay thay vì phải
    tin suông.

    Đính MỘT lần cho mỗi tiêu chí, không phải mỗi lần xuất hiện, để gợi ý
    không dài lê thê. KB lỗi -> bỏ qua, KHÔNG làm sập agent.
    """
    for c in criteria:
        # .get(): judge_bv6 là interface tiêm được từ ngoài, bản cài đặt khác
        # không buộc phải biết các trường nội bộ của agent.
        if c["level"] not in (0, 1) or not c.get("truy_van"):
            continue
        try:
            hits = retriever(c["truy_van"], content_type, langcode, top_k=1,
                             collection_name=COLLECTION_BRAND)
        except Exception:
            continue
        if hits:
            # Bỏ dòng prefix ngữ cảnh do build_brand_kb thêm vào, chỉ giữ
            # câu văn thật của tác giả.
            doan = hits[0]["text"].split("\n", 1)[-1].strip()
            c["reference"] = doan[:200]


def _issues_from_criteria(criteria: list[dict]) -> list[dict]:
    """Tiêu chí mức 0/1 -> issue. Mức 2 và NA không sinh gì.

    Một tiêu chí lỗi ở nhiều field sinh MỘT issue cho MỖI field, để
    write_back_node gom đúng nhóm field (docs/architecture.md mục 6.3).
    """
    issues = []
    for c in criteria:
        if c["level"] not in (0, 1):
            continue
        goi_y = c["suggestion"]
        if c["reference"]:
            goi_y = f"{goi_y} Ví dụ trong bài đã đăng: \"{c['reference']}\""
        cac_field = list(dict.fromkeys(o["field"] for o in c["occurrences"])) or ["body"]
        for field in cac_field:
            trich = [o["text"] for o in c["occurrences"] if o["field"] == field]
            issues.append({
                "field": field,
                "type": _NHAN[c["id"]],
                "suggestion": goi_y,
                # Trích dẫn để RIÊNG, không gộp vào `type`. Gộp vào khiến dòng
                # tiêu đề dài lê thê khi trích dẫn là cả một câu (BV6 trích
                # nguyên câu văn), trong khi Compliance vốn đã tách `excerpt`
                # ra khung riêng và đọc dễ hơn hẳn - để hai agent nhất quán.
                "excerpt": ", ".join(trich),
            })
    return issues


def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi",
        rules: dict | None = None, judge_bv6=_judge_formality,
        retriever=retrieve) -> dict | None:
    """Chấm Brand Voice. Trả None khi không tiêu chí nào áp dụng được.

    `rules`, `judge_bv6` và `retriever` tiêm được để test không cần
    brand_rules.json thật, không gọi LLM và không đọc KB.
    """
    if rules is None:
        rules = _load_rules()
    text_theo_field = {f: strip_html(fields.get(f, "") or "") for f in _FIELDS}

    if not any(text.strip() for text in text_theo_field.values()):
        # Bài rỗng: không có chữ nào để đối chiếu. Phải chặn ở đây vì các
        # tiêu chí dạng "không được có X" (BV7) sẽ trả mức 2 cho bài rỗng -
        # đúng về mặt logic nhưng thành 100 điểm brand cho một bài không có
        # nội dung. Trả None = CHƯA chấm được, Aggregator chia lại trọng số.
        return None

    dem_xung_ho = _dem_xung_ho(text_theo_field)
    criteria = [
        _bv1_ten_model(text_theo_field, rules),
        _bv2_thuat_ngu(text_theo_field, rules),
        _bv3_nhat_quan(dem_xung_ho),
        _bv4_khop_corpus(dem_xung_ho, rules),
        _bv5_viet_hoa_title(fields.get("title", "") or "", rules),
        _bv6_giong_van(fields, judge_bv6, content_type, langcode, retriever),
        _bv7_tu_bi_loai(text_theo_field, rules),
    ]

    _dinh_bang_chung(criteria, retriever, content_type, langcode)
    score = score_from_criteria(criteria)
    if score is None:
        return None      # không tiêu chí nào áp dụng -> CHƯA chấm được
    return {
        "score": score,
        "issues": _issues_from_criteria(criteria),
        "criteria": criteria,
    }

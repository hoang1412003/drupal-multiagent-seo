"""CP3 - RAG fact-check: đối chiếu claim định lượng trong bài với thông số
VinFast công bố công khai (docs/architecture.md mục 5.4, docs/rubrics.md CP3).

Đây là cách ĐO của tiêu chí CP3 trong rubric Compliance. Luồng: trích claim
định lượng (LLM) -> truy vấn KB -> so sánh (LLM) -> quy ra mức 0/1/2/NA.

AN TOÀN (quan trọng nhất): claim KHÔNG tra được, hoặc thông số tra về thuộc
MODEL KHÁC -> KHÔNG bao giờ ra mức 0. KB chỉ có thông số của một số model;
"không tra được" != "sai" (docs/rubrics.md mục 6.2), nên trường hợp đó là
mức 1 và severity `low`, không phải critical. Coi nó là sai sẽ chặn oan mọi
bài nhắc model ngoài KB. Hai lớp chặn: (1) retrieve rỗng -> claim không được
kết luận; (2) compare LLM chỉ trả 'mismatch' khi CÙNG model và số mâu thuẫn,
còn lại trả 'unverifiable'.
"""
from ai_core import call_agent
from prompt_builder import boc_noi_dung
from retrieval import retrieve

_FIELDS = ("title", "body", "meta_description")

_RULE = "Thông tin sai lệch so với thông số công bố chính thức"

# Nhãn RIÊNG cho mức 1. Dùng chung nhãn với mức 0 sẽ báo cho người duyệt rằng
# số liệu đã sai, trong khi thực tế chỉ là chưa tra được - đúng chỗ mà
# rubrics.md mục 6.2 cảnh báo không được nhầm.
_RULE_KHONG_TRA = "Số liệu chưa kiểm chứng được bằng thông số công bố"

_EXTRACT_PROMPT = (
    "Bạn trích các CLAIM ĐỊNH LƯỢNG có thể kiểm chứng bằng thông số kỹ thuật "
    "xe điện VinFast từ nội dung. Chỉ trích claim gắn với một model cụ thể và "
    "một con số kiểm chứng được: tầm hoạt động/quãng đường (km), thời gian sạc, "
    "dung lượng pin, giá, chu kỳ bảo dưỡng. KHÔNG trích câu chung chung không "
    "có số. Với mỗi claim, ghi: model (ví dụ 'VF 8'), metric, value (nguyên "
    "văn con số), field chứa nó (title/body/meta_description), và excerpt "
    "(trích nguyên văn cụm chứa claim). Nếu không có claim định lượng nào, "
    "trả mảng rỗng. Trả lời bằng tiếng Việt."
)

_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "metric": {
                        "type": "string",
                        "enum": ["tam_hoat_dong", "thoi_gian_sac", "pin", "gia", "bao_duong", "khac"],
                    },
                    "value": {"type": "string"},
                    "field": {"type": "string", "enum": ["title", "body", "meta_description"]},
                    "excerpt": {"type": "string"},
                },
                "required": ["model", "metric", "value", "field", "excerpt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}

_COMPARE_PROMPT = (
    "Bạn đối chiếu từng claim với đoạn thông số công bố tra được. Với mỗi mục "
    "đánh số, trả verdict:\n"
    "- 'mismatch' CHỈ KHI đoạn thông số rõ ràng là của ĐÚNG model trong claim "
    "VÀ con số trong claim MÂU THUẪN với con số công bố.\n"
    "- 'match' khi cùng model và con số khớp.\n"
    "- 'unverifiable' khi đoạn thông số thuộc MODEL KHÁC, không đủ dữ kiện, "
    "hoặc không chắc. Khi nghi ngờ luôn chọn 'unverifiable', TUYỆT ĐỐI không "
    "chọn 'mismatch'.\n"
    "Trả lời bằng tiếng Việt trong trường reason."
)

_COMPARE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["match", "mismatch", "unverifiable"]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "verdict", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def _extract_claims(fields: dict) -> list[dict]:
    # M1 + M3 (docs/prompt-injection.md mục 5). Đáng làm ở đây vì claim trích
    # ra được đem đối chiếu KB rồi sinh flag `critical` - một claim giả cấy
    # vào bình luận HTML sẽ thành một cáo buộc "sai lệch thông số" với người
    # duyệt.
    content, _ = boc_noi_dung(fields, _FIELDS)
    return call_agent(_EXTRACT_PROMPT, content, _EXTRACT_SCHEMA)["claims"]


def _compare(pairs: list) -> list[dict]:
    """pairs: list of (claim, hit). Gộp thành 1 lần gọi LLM."""
    lines = []
    for i, (claim, hit) in enumerate(pairs):
        lines.append(
            f"[{i}] Claim: model={claim['model']}, {claim['metric']}={claim['value']}\n"
            f"    Thông số tra được (model {hit['model']}): {hit['text']}"
        )
    return call_agent(_COMPARE_PROMPT, "\n\n".join(lines), _COMPARE_SCHEMA)["verdicts"]


def verdicts_hop_le(verdicts, so_pair: int):
    """Lọc verdict có `index` là số nguyên nằm trong biên của `pairs`."""
    return [
        v for v in verdicts
        if isinstance(v.get("index"), int) and 0 <= v["index"] < so_pair
    ]


def danh_gia(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi",
             extract_fn=_extract_claims, compare_fn=_compare, retriever=retrieve,
             embedder=None) -> dict:
    """Chấm CP3 -> {"level", "occurrences", "reason"}.

    Bốn kết cục, và việc phân biệt được chúng chính là lý do hàm này thay cho
    bản cũ trả list flag: bản cũ trả `[]` cho CẢ BA trường hợp "không có
    claim", "không tra được" và "mọi số liệu khớp" - ba tình huống phải ra ba
    mức khác nhau thì không thể gộp vào một danh sách rỗng.

        NA  bài không có claim định lượng nào -> không có gì để đối chiếu
        1   có claim nhưng ít nhất một claim không kết luận được
        2   mọi claim đều tra được và khớp thông số công bố
        0   có claim mâu thuẫn với thông số công bố (mã lỗi A3)
    """
    claims = extract_fn(fields)
    if not claims:
        return {"level": None, "occurrences": [],
                "reason": "Bài không có claim định lượng để đối chiếu."}

    pairs = []            # (claim, hit) - chỉ giữ claim tra được thông số
    khong_tra_duoc = []   # claim không có đoạn thông số nào để đối chiếu
    for claim in claims:
        query = f"{claim['model']} {claim['metric']}"
        hits = retriever(query, content_type, langcode, embedder=embedder)
        if hits:
            pairs.append((claim, hits[0]))
        else:
            khong_tra_duoc.append(claim)
    if not pairs:
        return {
            "level": 1,
            "occurrences": [{"field": c["field"], "text": c["excerpt"], "rule": _RULE_KHONG_TRA}
                            for c in khong_tra_duoc],
            "reason": "Không tìm thấy thông số công bố tương ứng trong knowledge "
                      "base - cần người kiểm chứng thủ công.",
        }

    # `index` là số do LLM tự điền, không được tin: nó có thể ngoài biên,
    # trùng nhau, hoặc thiếu hẳn cho một pair. Vì vậy gom verdict theo VỊ TRÍ
    # rồi duyệt `pairs`, thay vì tra ngược `pairs[v["index"]]`.
    #
    # Bản cũ tra ngược và văng IndexError, nhưng lỗi đó bị `try/except` của
    # `compliance._cp3_so_lieu` nuốt, nên CP3 âm thầm thành NA - mất hẳn tiêu
    # chí fact-check mà không có dấu hiệu gì. Chấm trùng thì giữ lần đầu, cùng
    # quy ước với `compliance._danh_gia_llm`.
    theo_vi_tri = {}
    for v in verdicts_hop_le(compare_fn(pairs), len(pairs)):
        theo_vi_tri.setdefault(v["index"], v.get("verdict"))

    lech, chua_ket_luan = [], list(khong_tra_duoc)
    for i, (claim, _) in enumerate(pairs):
        verdict = theo_vi_tri.get(i)
        if verdict == "mismatch":
            lech.append(claim)
        elif verdict != "match":
            # Gộp cả "unverifiable" LẪN pair không có verdict nào. Bỏ qua pair
            # thiếu verdict sẽ đẩy bài lên mức 2 ("mọi claim đều khớp") trong
            # khi có claim chưa hề được đối chiếu.
            chua_ket_luan.append(claim)

    if lech:
        return {
            "level": 0,
            "occurrences": [{"field": c["field"], "text": c["excerpt"], "rule": _RULE}
                            for c in lech],
            "reason": "Đối chiếu với thông số công bố chính thức thấy số liệu "
                      "mâu thuẫn - sửa lại theo nguồn chính thức.",
        }
    if chua_ket_luan:
        return {
            "level": 1,
            "occurrences": [{"field": c["field"], "text": c["excerpt"], "rule": _RULE_KHONG_TRA}
                            for c in chua_ket_luan],
            "reason": "Không kiểm chứng được bằng knowledge base - cần người "
                      "kiểm chứng thủ công.",
        }
    return {"level": 2, "occurrences": [], "reason": ""}

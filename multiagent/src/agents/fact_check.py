"""CP3 - RAG fact-check: đối chiếu claim định lượng trong bài với thông số
VinFast công bố công khai (docs/architecture.md mục 5.4, docs/rubrics.md CP3).

Là nguồn flag THỨ 3 của Compliance Agent (bên cạnh LLM tự do + blacklist).
Luồng: trích claim định lượng (LLM) -> truy vấn KB -> so sánh (LLM) -> lệch
thì sinh flag critical (mã A3).

AN TOÀN (quan trọng nhất): claim KHÔNG tra được, hoặc thông số tra về thuộc
MODEL KHÁC -> KHÔNG sinh flag. KB chỉ có thông số một số model; "không tra
được" != "sai" (docs/rubrics.md mục 6.2). Coi nó là sai sẽ chặn oan mọi bài
nhắc model ngoài KB. Hai lớp chặn: (1) retrieve rỗng -> bỏ qua claim;
(2) compare LLM chỉ trả 'mismatch' khi CÙNG model và số mâu thuẫn, còn lại
trả 'unverifiable'.
"""
from ai_core import call_agent
from retrieval import retrieve

_RULE = "Thông tin sai lệch so với thông số công bố chính thức"

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
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}"
    )
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


def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi",
        extract_fn=_extract_claims, compare_fn=_compare, retriever=retrieve,
        embedder=None) -> list[dict]:
    claims = extract_fn(fields)
    if not claims:
        return []

    pairs = []  # (claim, hit) - chỉ giữ claim tra được thông số
    for claim in claims:
        query = f"{claim['model']} {claim['metric']}"
        hits = retriever(query, content_type, langcode, embedder=embedder)
        if hits:
            pairs.append((claim, hits[0]))
    if not pairs:
        return []

    verdicts = compare_fn(pairs)
    flags = []
    for v in verdicts:
        if v.get("verdict") != "mismatch":
            continue
        claim = pairs[v["index"]][0]
        flags.append(
            {
                "field": claim["field"],
                "severity": "critical",
                "rule": _RULE,
                "excerpt": claim["excerpt"],
            }
        )
    return flags

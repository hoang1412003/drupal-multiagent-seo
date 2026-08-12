"""Khung LangGraph cho pipeline Multi-Agent kiểm duyệt nội dung.

Pipeline phân tích gồm Fetch -> Orchestrator/Dispatch -> 4 agent (song song)
-> Aggregator. ``build_graph()`` mặc định nối thêm Write-back để giữ hành vi
của các script chạy thủ công; worker production tắt node đó vì worker phải ghi
audit trước rồi mới tự PATCH trong ranh giới retry của nó.

Cả 4 agent đều chạy thật và dùng rubric để tính điểm tất định. Báo cáo trả về
gom theo từng field (docs/architecture.md mục 3).
"""
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph

import ai_core
import config
from agents import brand_voice, compliance, content_quality, seo
from drupal_client import fetch_content, write_back
from state import ContentReviewState
from text_utils import content_hash

DEFAULT_CONTENT_TYPE = "cam_nang"
DEFAULT_LANGCODE = "vi"


def _khoa_cua(state: ContentReviewState) -> dict:
    """(content_type, langcode) của state, kèm mặc định.

    MỘT chỗ duy nhất suy ra cặp khoá này, để Aggregator và các agent không thể
    tra theo hai giá trị khác nhau trong cùng một lần chấm - đó đúng là điều
    đã xảy ra ở nợ B6: `aggregator_node` đọc từ state, còn hai agent RAG rơi
    về hằng số trong chữ ký hàm.
    """
    return {
        "content_type": state.get("content_type") or DEFAULT_CONTENT_TYPE,
        "langcode": state.get("langcode") or DEFAULT_LANGCODE,
    }


# Alias công khai: worker.py cần suy đúng cặp khoá này để tra config_meta ghi
# vào run_log (audit.ghi), thay vì tự gọi config.load() không tham số - việc
# đó rơi về mặc định của config.load() chứ không phải khoá state đang dùng,
# hai hằng số DEFAULT_* nằm ở hai file độc lập nên "tình cờ" trùng hôm nay
# không đảm bảo mãi trùng. Dùng alias thay vì import thẳng tên có gạch dưới
# đầu để không phá quy ước "gạch dưới đầu = nội bộ module".
khoa_cua = _khoa_cua


def _config_cua(state: ContentReviewState) -> dict:
    """Lấy khối config theo (content_type, langcode) của state.

    Trọng số và ngưỡng KHÔNG còn là hằng số module - chúng nằm ở
    config/scoring.yaml để con số chỉ tồn tại ở một chỗ (docs/config-spec.md
    mục 1: cùng tập số này từng nằm ở 4 nơi và đã trôi lệch một lần).
    """
    khoi = config.load(**_khoa_cua(state))
    config.canh_bao_mot_lan(khoi, ai_core.MODEL)
    return khoi


def fetch_node(state: ContentReviewState) -> dict:
    content = fetch_content(state["node_id"])
    return {
        "fields": content["fields"],
        "raw_content": content["raw_content"],
    }


def orchestrator_node(state: ContentReviewState) -> dict:
    # Hiện chỉ chuyển tiếp (pass-through); để dành cho logic kiểm tra trước
    # khi phát cho agent sau này (VD: bỏ qua hết nếu body rỗng/quá ngắn).
    return {}


def content_quality_node(state: ContentReviewState) -> dict:
    try:
        result = content_quality.run(state["fields"])
    except Exception:
        result = None  # agent lỗi -> để Aggregator xử lý theo fail-safe (mục 6.4)
    return {"content_quality_result": result}


def seo_node(state: ContentReviewState) -> dict:
    try:
        result = seo.run(state["fields"])
    except Exception:
        result = None
    return {"seo_result": result}


def brand_node(state: ContentReviewState) -> dict:
    try:
        # Truyền khoá xuống: BV6 truy vấn KB brand theo (content_type,
        # langcode), không được để nó lọc bằng hằng số (nợ B6).
        result = brand_voice.run(state["fields"], **_khoa_cua(state))
    except Exception:
        result = None  # agent lỗi -> để Aggregator xử lý theo fail-safe (mục 6.4)
    return {"brand_result": result}


def compliance_node(state: ContentReviewState) -> dict:
    try:
        # Truyền khoá xuống: CP3 truy vấn KB fact-check theo (content_type,
        # langcode), không được để nó lọc bằng hằng số (nợ B6).
        result = compliance.run(state["fields"], **_khoa_cua(state))
    except Exception:
        result = None  # agent lỗi -> để Aggregator xử lý theo fail-safe (mục 6.4)
    return {"compliance_result": result}


def aggregator_node(state: ContentReviewState) -> dict:
    results = {
        "content_quality": state.get("content_quality_result"),
        "seo": state.get("seo_result"),
        "brand": state.get("brand_result"),
        "compliance": state.get("compliance_result"),
    }
    compliance_result = results["compliance"]
    missing = [name for name, r in results.items() if r is None]
    veto_reason = None
    note = None

    khoi = _config_cua(state)
    weights = khoi["weights"]
    nguong = khoi["decision"]

    if compliance_result is None:
        # Compliance có quyền phủ quyết (docs/architecture.md mục 6.4) - không bao
        # giờ tự động publish khi không xác minh được rủi ro pháp lý.
        decision = "needs_revision"
        final_score = None
        note = "Không thể xác minh Compliance - cần con người review thủ công."
    else:
        has_critical_flag = any(
            f.get("severity") == "critical" for f in compliance_result.get("flags", [])
        )
        available = {k: v for k, v in results.items() if v is not None}
        total_weight = sum(weights[k] for k in available)
        final_score = (
            sum(weights[k] * v["score"] for k, v in available.items())
            / total_weight
        )
        veto = nguong["compliance_veto_below"]
        if compliance_result["score"] < veto or has_critical_flag:
            decision = "rejected"
            if has_critical_flag and compliance_result["score"] >= veto:
                # Score không phản ánh vi phạm (xem spec mục 4) - ghi rõ lý do
                # thật để tránh gây hiểu nhầm khi điểm cao nhưng vẫn bị từ chối.
                veto_reason = (
                    "Bị từ chối do vi phạm Compliance (severity: critical), "
                    "độc lập với điểm tổng."
                )
        elif final_score >= nguong["publish_min"]:
            decision = "publish"
        elif final_score >= nguong["needs_revision_min"]:
            decision = "needs_revision"
        else:
            decision = "rejected"

        if missing:
            # Điểm vẫn tính được (đã chia lại theo trọng số còn lại) nhưng chưa
            # bao gồm đủ 4 tiêu chí - nói rõ để người duyệt không hiểu nhầm.
            missing_labels = ", ".join(AGENT_LABELS.get(m, m) for m in missing)
            note = (
                f"Điểm số chưa đầy đủ: {missing_labels} không trả được kết quả, "
                "điểm đã chia lại theo các tiêu chí còn lại."
            )

    report = {
        "node_id": state["node_id"],
        "final_score": final_score,
        "decision": decision,
        "missing_agents": missing,
        "details": results,
    }
    if veto_reason:
        report["veto_reason"] = veto_reason
    if note:
        report["note"] = note
    return {"final_score": final_score, "decision": decision, "report": report}


# content_quality/seo dùng "issues", compliance dùng "flags" - đều là list dict
# có gắn trường "field" (docs/architecture.md mục 3).
ISSUE_LIST_KEYS = ("issues", "flags")

# Thứ tự và nhãn hiển thị của từng field trong báo cáo
FIELD_ORDER = ["title", "meta_description", "url_alias", "summary", "body", "image_alt"]
FIELD_LABELS = {
    "title": "Tiêu đề (title)",
    "meta_description": "Meta description",
    "url_alias": "Đường dẫn (URL alias)",
    "summary": "Tóm tắt (summary)",
    "body": "Nội dung (body)",
    "image_alt": "Alt text ảnh",
}
AGENT_LABELS = {
    "content_quality": "Chất lượng",
    "seo": "SEO",
    "brand": "Brand Voice",
    "compliance": "Compliance",
}


def _format_issue(issue) -> str:
    # issue là dict tùy agent (VD {field, type, suggestion} hoặc
    # {field, severity, rule, excerpt}). Bỏ khóa "field" vì nó đã thành tiêu đề
    # nhóm; ghép phần còn lại thành "key: value" cho dễ đọc.
    if not isinstance(issue, dict):
        return str(issue)
    return "; ".join(f"{k}: {v}" for k, v in issue.items() if k != "field")


def _issue_to_json(agent_key: str, issue: dict) -> dict:
    """Một issue/flag của agent -> một mục trong báo cáo JSON.

    Compliance có hình dạng khác 3 agent kia: nó dùng {rule, excerpt,
    severity}. Từ khi chuyển sang rubric CP1-CP8 nó có thêm `suggestion` -
    trước đó LLM chỉ trả tên điều khoản nên `message` luôn None. Vẫn KHÔNG
    đặt message = rule khi thiếu suggestion: in cùng một câu hai lần.
    """
    if agent_key == "compliance":
        return {
            "agent": AGENT_LABELS[agent_key],
            "label": issue.get("rule", ""),
            "message": issue.get("suggestion") or None,
            "excerpt": issue.get("excerpt") or None,
            "severity": issue.get("severity"),
        }
    return {
        "agent": AGENT_LABELS.get(agent_key, agent_key),
        "label": issue.get("type", ""),
        "message": issue.get("suggestion") or None,
        # Brand Voice có trích dẫn nguyên văn (chỗ nó tìm thấy lỗi); Content
        # Quality và SEO thì không - .get() nên cả ba dùng chung nhánh này.
        "excerpt": issue.get("excerpt") or None,
        # Chỉ Compliance định nghĩa mức nghiêm trọng. KHÔNG bịa cho 3 agent
        # kia - docs/rubrics.md mục 6.1 chủ trương severity phải tra bảng
        # tất định theo mã tiêu chí.
        "severity": None,
    }


def _build_report_json(state: ContentReviewState) -> dict:
    """Dựng báo cáo có cấu trúc cho module vf_ai_review render.

    Chạy song song với chuỗi text ghi vào field_ai_suggestions - chuỗi đó
    KHÔNG đổi, để khi module chưa bật thì vẫn đọc được (suy giảm mềm).
    """
    report = state.get("report") or {}
    theo_field: dict = {}

    for agent_key, result in (report.get("details") or {}).items():
        if not isinstance(result, dict):
            continue      # agent lỗi -> đã phản ánh ở missing_agents/note
        for key in ISSUE_LIST_KEYS:
            for issue in result.get(key, []):
                if not isinstance(issue, dict):
                    continue
                field = issue.get("field")
                if not field:
                    continue      # không gắn field thì không hiện dưới widget nào
                theo_field.setdefault(field, []).append(
                    _issue_to_json(agent_key, issue)
                )

    return {
        "version": 1,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash(state.get("fields") or {}),
        # Lấy decision/final_score từ STATE chứ không từ report, vì đó đúng
        # là nguồn write_back() ghi vào field_ai_status/field_ai_score. Đọc
        # từ report là tạo nguồn thứ hai cho cùng một giá trị - lệch nhau thì
        # giao diện và field điểm hiển thị hai con số khác nhau.
        "decision": state.get("decision"),
        "final_score": state.get("final_score"),
        "note": report.get("note"),
        "veto_reason": report.get("veto_reason"),
        "missing_agents": report.get("missing_agents", []),
        "fields": theo_field,
    }


def write_back_node(state: ContentReviewState) -> dict:
    report = state.get("report") or {}
    by_field = {}      # field -> list dòng gợi ý
    other_lines = []   # lý do veto, agent lỗi (không gắn field cụ thể)

    if report.get("veto_reason"):
        other_lines.append(f"[LÝ DO TỪ CHỐI] {report['veto_reason']}")
    if report.get("note"):
        other_lines.append(f"[LƯU Ý] {report['note']}")

    for name, result in report.get("details", {}).items():
        label = AGENT_LABELS.get(name, name)
        if result is None:
            other_lines.append(f"[{label}] Không có kết quả (agent lỗi/thiếu dữ liệu)")
            continue
        for key in ISSUE_LIST_KEYS:
            for issue in result.get(key, []):
                field = issue.get("field") if isinstance(issue, dict) else None
                line = f"[{label}] {_format_issue(issue)}"
                if field:
                    by_field.setdefault(field, []).append(line)
                else:
                    other_lines.append(line)

    # Ghép báo cáo: phần chung trước, rồi từng field theo thứ tự
    lines = list(other_lines)
    ordered = FIELD_ORDER + [f for f in by_field if f not in FIELD_ORDER]
    for field in ordered:
        if by_field.get(field):
            lines.append(f"── {FIELD_LABELS.get(field, field)} ──")
            lines.extend(by_field[field])

    write_back(
        node_id=state["node_id"],
        # final_score = None nghĩa là CHƯA chấm được (Compliance lỗi), khác hẳn
        # với 0 điểm. Giữ nguyên None để Drupal hiển thị field trống thay vì
        # "0 điểm" - xem spec mục 5.1 "Agent lỗi không bị cho điểm 0".
        status=state["decision"],
        score=state["final_score"],
        suggestions="\n".join(lines) or "Không có gợi ý sửa.",
        report_json=_build_report_json(state),
    )
    return {}


def build_graph(*, include_write_back: bool = True):
    graph = StateGraph(ContentReviewState)

    graph.add_node("fetch", fetch_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("content_quality", content_quality_node)
    graph.add_node("seo", seo_node)
    graph.add_node("brand", brand_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("aggregator", aggregator_node)

    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", "orchestrator")

    for agent in ("content_quality", "seo", "brand", "compliance"):
        graph.add_edge("orchestrator", agent)
        graph.add_edge(agent, "aggregator")

    if include_write_back:
        graph.add_node("write_back", write_back_node)
        graph.add_edge("aggregator", "write_back")
        graph.add_edge("write_back", END)
    else:
        graph.add_edge("aggregator", END)

    return graph.compile()

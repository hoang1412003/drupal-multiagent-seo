"""Khung LangGraph cho pipeline Multi-Agent kiểm duyệt nội dung.

Khớp thiết kế 8 node trong docs/architecture.md:
Fetch -> Orchestrator/Dispatch -> 4 agent (song song) -> Aggregator -> Write-back

Content Quality và SEO gọi Claude thật (Sprint 1). Brand Consistency và
Compliance vẫn là STUB - cần có brand guideline (Brand) và thuộc phạm vi
Sprint 2 theo docs/roadmap.md.
"""
from langgraph.graph import END, START, StateGraph

from agents import compliance, content_quality, seo
from drupal_client import fetch_content, write_back
from state import ContentReviewState

WEIGHTS = {
    "content_quality": 0.25,
    "seo": 0.20,
    "brand": 0.25,
    "compliance": 0.30,
}


def fetch_node(state: ContentReviewState) -> dict:
    content = fetch_content(state["node_id"])
    return {
        "title": content["title"],
        "body": content["body"],
        "raw_content": content["raw_content"],
    }


def orchestrator_node(state: ContentReviewState) -> dict:
    # Hiện chỉ chuyển tiếp (pass-through); để dành cho logic kiểm tra trước
    # khi phát cho agent sau này (VD: bỏ qua hết nếu body rỗng/quá ngắn).
    return {}


def _stub_agent_result(name: str) -> dict:
    return {
        "score": 100,
        "issues": [],
        "note": f"STUB - {name} agent chưa triển khai (xem Sprint 1 tiếp theo)",
    }


def content_quality_node(state: ContentReviewState) -> dict:
    try:
        result = content_quality.run(state["title"], state["body"])
    except Exception:
        result = None  # agent lỗi -> để Aggregator xử lý theo fail-safe (mục 6.4)
    return {"content_quality_result": result}


def seo_node(state: ContentReviewState) -> dict:
    try:
        result = seo.run(state["title"], state["body"])
    except Exception:
        result = None
    return {"seo_result": result}


def brand_node(state: ContentReviewState) -> dict:
    return {"brand_result": _stub_agent_result("Brand Consistency")}


def compliance_node(state: ContentReviewState) -> dict:
    try:
        result = compliance.run(state["title"], state["body"])
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

    if compliance_result is None:
        # Compliance có quyền phủ quyết (docs/architecture.md mục 6.4) - không bao
        # giờ tự động publish khi không xác minh được rủi ro pháp lý.
        decision = "needs_revision"
        final_score = None
    else:
        has_critical_flag = any(
            f.get("severity") == "critical" for f in compliance_result.get("flags", [])
        )
        available = {k: v for k, v in results.items() if v is not None}
        total_weight = sum(WEIGHTS[k] for k in available)
        final_score = (
            sum(WEIGHTS[k] * v["score"] for k, v in available.items())
            / total_weight
        )
        if compliance_result["score"] < 50 or has_critical_flag:
            decision = "rejected"
            if has_critical_flag and compliance_result["score"] >= 50:
                # Score không phản ánh vi phạm (xem spec mục 4) - ghi rõ lý do
                # thật để tránh gây hiểu nhầm khi điểm cao nhưng vẫn bị từ chối.
                veto_reason = (
                    "Bị từ chối do vi phạm Compliance (severity: critical), "
                    "độc lập với điểm tổng."
                )
        elif final_score >= 80:
            decision = "publish"
        elif final_score >= 50:
            decision = "needs_revision"
        else:
            decision = "rejected"

    report = {
        "node_id": state["node_id"],
        "final_score": final_score,
        "decision": decision,
        "missing_agents": missing,
        "details": results,
    }
    if veto_reason:
        report["veto_reason"] = veto_reason
    return {"final_score": final_score, "decision": decision, "report": report}


ISSUE_LIST_KEYS = ("issues", "meta_issues", "violations", "flags")


def _format_issue(issue) -> str:
    # issue có thể là string (VD: seo.meta_issues) hoặc dict với các trường
    # khác nhau tùy agent (VD: content_quality {type, location, suggestion}) -
    # in dict thô sẽ ra dạng {'key': 'value', ...} khó đọc, nên ghép lại thành
    # chuỗi "key: value" thay vì để nguyên repr Python.
    if not isinstance(issue, dict):
        return str(issue)
    return "; ".join(f"{k}: {v}" for k, v in issue.items())


def write_back_node(state: ContentReviewState) -> dict:
    report = state.get("report") or {}
    suggestions_lines = []
    if report.get("veto_reason"):
        suggestions_lines.append(f"[LÝ DO TỪ CHỐI] {report['veto_reason']}")
    for name, result in report.get("details", {}).items():
        if result is None:
            suggestions_lines.append(f"[{name}] Không có kết quả (agent lỗi/thiếu dữ liệu)")
            continue
        for key in ISSUE_LIST_KEYS:
            for issue in result.get(key, []):
                suggestions_lines.append(f"[{name}] {_format_issue(issue)}")

    write_back(
        node_id=state["node_id"],
        status=state["decision"],
        score=state["final_score"] or 0,
        suggestions="\n".join(suggestions_lines) or "Không có gợi ý sửa.",
    )
    return {}


def build_graph():
    graph = StateGraph(ContentReviewState)

    graph.add_node("fetch", fetch_node)
    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("content_quality", content_quality_node)
    graph.add_node("seo", seo_node)
    graph.add_node("brand", brand_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("aggregator", aggregator_node)
    graph.add_node("write_back", write_back_node)

    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", "orchestrator")

    for agent in ("content_quality", "seo", "brand", "compliance"):
        graph.add_edge("orchestrator", agent)
        graph.add_edge(agent, "aggregator")

    graph.add_edge("aggregator", "write_back")
    graph.add_edge("write_back", END)

    return graph.compile()

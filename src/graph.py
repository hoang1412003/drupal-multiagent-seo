"""LangGraph skeleton for the Multi-Agent content review pipeline.

Matches the 8-node design in docs/architecture.md:
Fetch -> Orchestrator/Dispatch -> 4 agents (parallel) -> Aggregator -> Write-back

The 4 agent nodes are STUBS for now (Sprint 1 skeleton step) - they return a
fixed placeholder result instead of calling Claude. They get replaced with
real ai_core.call_agent() calls one at a time in the next Sprint 1 task
(SEO + Content Quality agents), then Sprint 2 (Brand + Compliance).
"""
from langgraph.graph import END, START, StateGraph

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
    # Pass-through today; reserved for future pre-dispatch checks (e.g.
    # skipping agents entirely if the body is empty/too short).
    return {}


def _stub_agent_result(name: str) -> dict:
    return {
        "score": 100,
        "issues": [],
        "note": f"STUB - {name} agent chưa triển khai (xem Sprint 1 tiếp theo)",
    }


def content_quality_node(state: ContentReviewState) -> dict:
    return {"content_quality_result": _stub_agent_result("Content Quality")}


def seo_node(state: ContentReviewState) -> dict:
    return {"seo_result": _stub_agent_result("SEO")}


def brand_node(state: ContentReviewState) -> dict:
    return {"brand_result": _stub_agent_result("Brand Consistency")}


def compliance_node(state: ContentReviewState) -> dict:
    result = _stub_agent_result("Compliance")
    result["flags"] = []
    return {"compliance_result": result}


def aggregator_node(state: ContentReviewState) -> dict:
    results = {
        "content_quality": state.get("content_quality_result"),
        "seo": state.get("seo_result"),
        "brand": state.get("brand_result"),
        "compliance": state.get("compliance_result"),
    }
    compliance = results["compliance"]
    missing = [name for name, r in results.items() if r is None]

    if compliance is None:
        # Compliance has veto power (docs/architecture.md 6.4) - never auto-publish
        # without being able to verify legal/compliance risk.
        decision = "needs_revision"
        final_score = None
    else:
        has_critical_flag = any(
            f.get("severity") == "critical" for f in compliance.get("flags", [])
        )
        if compliance["score"] < 50 or has_critical_flag:
            decision = "rejected"
            final_score = compliance["score"]
        else:
            available = {k: v for k, v in results.items() if v is not None}
            total_weight = sum(WEIGHTS[k] for k in available)
            final_score = (
                sum(WEIGHTS[k] * v["score"] for k, v in available.items())
                / total_weight
            )
            if final_score >= 80:
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
    return {"final_score": final_score, "decision": decision, "report": report}


def write_back_node(state: ContentReviewState) -> dict:
    suggestions_lines = []
    for name, result in (state.get("report") or {}).get("details", {}).items():
        if result is None:
            suggestions_lines.append(f"[{name}] Không có kết quả (agent lỗi/thiếu dữ liệu)")
            continue
        for issue in result.get("issues", []):
            suggestions_lines.append(f"[{name}] {issue}")

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

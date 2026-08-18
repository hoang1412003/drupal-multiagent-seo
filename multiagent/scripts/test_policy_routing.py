"""Test route exact policy v1/v2 trong graph, hoàn toàn offline."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import graph  # noqa: E402
from decision_policy import (  # noqa: E402
    POLICY_V1,
    POLICY_V2,
    PolicyContractError,
)


FIELDS = {
    "title": "Hướng dẫn sạc ô tô điện an toàn tại nhà đúng cách",
    "body": "<h2>Hướng dẫn</h2><p>Nội dung hướng dẫn an toàn.</p>",
    "summary": "Tóm tắt hướng dẫn sạc an toàn.",
    "meta_description": "m" * 150,
    "url_alias": "/huong-dan-sac-o-to-dien-an-toan",
    "image_alt": "Ô tô điện đang sạc an toàn",
}


def _criteria(prefix, count):
    return [
        {"id": f"{prefix}{index}", "level": 2, "occurrences": []}
        for index in range(1, count + 1)
    ]


def _agent_results(score):
    return {
        "content_quality_result": {
            "score": score,
            "criteria": _criteria("CQ", 8),
            "issues": [],
            "policy_checks": [{"id": "A5", "status": "absent"}],
            "unavailable_checks": [],
        },
        "seo_result": {
            "score": score,
            "criteria": _criteria("SEO", 10),
            "issues": [],
            "unavailable_checks": [],
        },
        "brand_result": {
            "score": score,
            "criteria": _criteria("BV", 7),
            "issues": [],
            "unavailable_checks": [],
        },
        "compliance_result": {
            "score": score,
            "criteria": _criteria("CP", 8),
            "flags": [],
            "policy_checks": [{"id": "A6", "status": "not_applicable"}],
            "unavailable_checks": [],
        },
    }


def _v2_state(score):
    return {
        "node_id": "routing-v2",
        "fields": dict(FIELDS),
        "policy_version": POLICY_V2,
        "assessment_as_of": "2026-08-17",
        **_agent_results(score),
    }


def test_legacy_thieu_version_duoc_normalize_exact_v1():
    assert graph.orchestrator_node({}) == {"policy_version": POLICY_V1}
    print("[PASS] state legacy thieu version -> exact policy v1")


def test_unknown_version_fail_o_orchestrator_truoc_agent_call():
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("agent/provider must not be called")

    modules = (
        graph.content_quality,
        graph.seo,
        graph.brand_voice,
        graph.compliance,
    )
    originals = [module.run for module in modules]
    for module in modules:
        module.run = forbidden
    try:
        try:
            graph.orchestrator_node({"policy_version": "cam-nang-vn-v2-beta"})
        except PolicyContractError:
            pass
        else:
            raise AssertionError("unknown policy version phai bi tu choi")
    finally:
        for module, original in zip(modules, originals):
            module.run = original
    assert calls == []
    print("[PASS] unknown policy fail tai orchestrator truoc 4 agent")


def test_agent_nodes_truyen_exact_version_cho_cq_va_compliance():
    seen = {}

    def cq_run(fields, **kwargs):
        seen["cq"] = kwargs
        return {"score": 100.0}

    def compliance_run(fields, **kwargs):
        seen["compliance"] = kwargs
        return {"score": 100.0}

    cq_old = graph.content_quality.run
    compliance_old = graph.compliance.run
    graph.content_quality.run = cq_run
    graph.compliance.run = compliance_run
    try:
        state = {"fields": dict(FIELDS), "policy_version": POLICY_V2}
        graph.content_quality_node(state)
        graph.compliance_node(state)
    finally:
        graph.content_quality.run = cq_old
        graph.compliance.run = compliance_old
    assert seen["cq"]["policy_version"] == POLICY_V2
    assert seen["compliance"]["policy_version"] == POLICY_V2
    print("[PASS] CQ/Compliance nodes nhan exact policy version")


def test_v1_aggregator_snapshot_giu_nguyen_veto_score_note():
    critical = {
        "severity": "critical",
        "rule": "So sánh tuyệt đối không có căn cứ",
        "excerpt": "tốt nhất",
    }
    state = {
        "node_id": "legacy-snapshot",
        "content_quality_result": {"score": 90.0},
        "seo_result": None,
        "brand_result": {"score": 80.0},
        "compliance_result": {"score": 85.0, "flags": [critical]},
    }
    expected = {
        "final_score": 85.0,
        "decision": "rejected",
        "report": {
            "node_id": "legacy-snapshot",
            "final_score": 85.0,
            "decision": "rejected",
            "missing_agents": ["seo"],
            "details": {
                "content_quality": {"score": 90.0},
                "seo": None,
                "brand": {"score": 80.0},
                "compliance": {"score": 85.0, "flags": [critical]},
            },
            "veto_reason": (
                "Bị từ chối do vi phạm Compliance (severity: critical), "
                "độc lập với điểm tổng."
            ),
            "note": (
                "Điểm số chưa đầy đủ: SEO không trả được kết quả, "
                "điểm đã chia lại theo các tiêu chí còn lại."
            ),
        },
    }
    assert graph.aggregate_score_v1(state) == expected
    assert graph.aggregator_node({**state, "policy_version": POLICY_V1}) == expected
    assert graph.aggregator_node(state) == expected
    print("[PASS] v1 snapshot giu decision/score/veto/missing note")


def test_v2_score_cao_nhung_cq1_level0_chi_needs_revision_b8():
    state = _v2_state(93.0)
    cq1 = state["content_quality_result"]["criteria"][0]
    cq1["level"] = 0
    cq1["occurrences"] = [
        {"field": "body", "text": "Nội dung hướng dẫn an toàn."}
    ]
    result = graph.aggregator_node(state)
    assert result["final_score"] == 93.0
    assert result["decision"] == "needs_revision"
    assert result["report"]["decision_basis"]["blocking_codes"] == ["B8"]
    print("[PASS] v2 score 93 + CQ1 level0 -> needs_revision B8")


def test_v2_score_thap_nhung_sach_complete_van_publish():
    result = graph.aggregator_node(_v2_state(12.0))
    assert result["final_score"] == 12.0
    assert result["decision"] == "publish"
    assert result["report"]["decision_basis"]["reason"] == "clean"
    assert result["report"]["coverage"]["complete"] is True
    print("[PASS] v2 score 12 + khong A/B + complete -> publish")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_legacy_thieu_version_duoc_normalize_exact_v1,
        test_unknown_version_fail_o_orchestrator_truoc_agent_call,
        test_agent_nodes_truyen_exact_version_cho_cq_va_compliance,
        test_v1_aggregator_snapshot_giu_nguyen_veto_score_note,
        test_v2_score_cao_nhung_cq1_level0_chi_needs_revision_b8,
        test_v2_score_thap_nhung_sach_complete_van_publish,
    ):
        try:
            fn()
        except Exception as error:
            failed = True
            print(f"[FAIL] {fn.__name__}: {error}")
    sys.exit(1 if failed else 0)

"""Metric tests report-only cho raw policy v2; khong import agent/provider."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_policy_v2_metrics  # noqa: E402
from eval_policy_v2_metrics import (  # noqa: E402
    EvaluationContractError,
    gold_metrics,
    stability_metrics,
)


LABELS = ["publish", "needs_revision", "rejected"]


def _row(sample_id, repeat_index, decision, score, expected="needs_revision"):
    return {
        "sample_id": sample_id,
        "repeat_index": repeat_index,
        "expected_label": expected,
        "decision": decision,
        "final_score": score,
        "usage": [],
        "cost": {"estimated_usd": "0"},
        "latency": {"milliseconds": 1.0},
        "status": "complete",
    }


def e1_raw(samples):
    results = []
    for sample_id, values in samples.items():
        for index, (decision, score) in enumerate(values, start=1):
            results.append(_row(sample_id, index, decision, score))
    return {
        "_meta": {
            "dataset_kind": "e1",
            "ordered_sample_ids": list(samples),
            "repeats": 5,
            "label_provenance": "AI-annotated-partially-exposed",
        },
        "results": results,
    }


def gold_raw(pairs):
    results = [
        _row(f"S-{index:03d}", 1, decision, 80.0, expected)
        for index, (expected, decision) in enumerate(pairs, start=1)
    ]
    return {
        "_meta": {
            "dataset_kind": "gold",
            "ordered_sample_ids": [row["sample_id"] for row in results],
            "repeats": 1,
            "label_provenance": "AI-annotated-partially-exposed",
        },
        "results": results,
    }


def _expect_error(label, fn, contains):
    try:
        fn()
    except EvaluationContractError as error:
        assert contains in str(error), str(error)
        print(f"[PASS] {label}")
    else:
        raise AssertionError(f"{label}: phai nem EvaluationContractError")


def test_e1_decision_consistency_va_sigma():
    raw = e1_raw({
        "G-001": [("publish", 80.0)] * 5,
        "G-002": [("needs_revision", 70.0)] * 4 + [("publish", 74.0)],
    })
    metrics = stability_metrics(raw)
    assert metrics["decision_consistency"] == 0.9
    assert metrics["samples"]["G-001"]["mode_agreement"] == 1.0
    assert metrics["samples"]["G-002"]["mode_agreement"] == 0.8
    assert metrics["final_score_sigma"] is not None
    assert metrics["usage"]["events"] == 0
    print("[PASS] E1 decision consistency, per-sample mode va sigma")


def test_e1_thieu_mot_repeat_fatal():
    _expect_error(
        "E1 thieu repeat fatal",
        lambda: stability_metrics(
            e1_raw({"G-001": [("publish", 80.0)] * 4})
        ),
        "repeat",
    )


def test_inventory_duplicate_fatal():
    raw = e1_raw({"G-001": [("publish", 80.0)] * 5})
    raw["results"].append(dict(raw["results"][0]))
    _expect_error(
        "metric inventory duplicate fatal",
        lambda: stability_metrics(raw),
        "duplicate",
    )


def test_gold_confusion_kappa_recall_va_false_publish():
    raw = gold_raw([
        ("publish", "publish"),
        ("needs_revision", "needs_revision"),
        ("rejected", "rejected"),
        ("rejected", "publish"),
    ])
    metrics = gold_metrics(raw)
    assert metrics["label_order"] == LABELS
    assert metrics["confusion"] == [[1, 0, 0], [0, 1, 0], [1, 0, 1]]
    assert metrics["recall"]["rejected"] == 0.5
    assert metrics["false_publish_count"] == 1
    assert metrics["kappa"] is not None
    assert metrics["provenance_limitation"] == "independent_label_reliability_not_demonstrated"
    print("[PASS] gold confusion/kappa/recall/false-publish dung huong")


def test_denominator_zero_tra_none_status_na():
    metrics = gold_metrics(gold_raw([("publish", "publish")]))
    assert metrics["recall"]["rejected"] is None
    assert metrics["gate_status"]["rejected_recall"] == "NA"
    assert metrics["recall"]["needs_revision"] is None
    assert metrics["gate_status"]["needs_revision_recall"] == "NA"
    print("[PASS] denominator zero -> None va gate NA")


def test_report_only_khong_import_ai_core_agents():
    source = Path(eval_policy_v2_metrics.__file__).read_text(encoding="utf-8")
    assert "ai_core" not in source
    assert "src.agents" not in source
    assert "from agents" not in source
    assert "import agents" not in source
    print("[PASS] metrics report-only khong import agent/provider")


if __name__ == "__main__":
    failed = False
    for test in (
        test_e1_decision_consistency_va_sigma,
        test_e1_thieu_mot_repeat_fatal,
        test_inventory_duplicate_fatal,
        test_gold_confusion_kappa_recall_va_false_publish,
        test_denominator_zero_tra_none_status_na,
        test_report_only_khong_import_ai_core_agents,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

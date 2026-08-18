"""Metric tests report-only cho raw policy v2; khong import agent/provider."""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_policy_v2_metrics  # noqa: E402
from eval_policy_v2_metrics import (  # noqa: E402
    EvaluationContractError,
    gold_metrics,
    main,
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


def test_cli_dataset_gold_ghi_report_json_atomic():
    raw = gold_raw([
        ("publish", "publish"),
        ("needs_revision", "needs_revision"),
    ])
    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "gold_raw.json"
        output_path = Path(tmp) / "gold_report.json"
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        exit_code = main(["--dataset", "gold", "--raw", str(raw_path), "--output", str(output_path)])
        assert exit_code == 0
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["dataset_kind"] == "gold"
        assert report["kappa"] is not None
    print("[PASS] CLI --dataset gold ghi report JSON atomic")


def test_cli_dataset_e1_ghi_report_json_atomic():
    raw = e1_raw({"G-001": [("publish", 80.0)] * 5})
    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "e1_raw.json"
        output_path = Path(tmp) / "e1_report.json"
        raw_path.write_text(json.dumps(raw), encoding="utf-8")
        exit_code = main(["--dataset", "e1", "--raw", str(raw_path), "--output", str(output_path)])
        assert exit_code == 0
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["dataset_kind"] == "e1"
        assert report["decision_consistency"] == 1.0
    print("[PASS] CLI --dataset e1 ghi report JSON atomic")


def test_cli_raw_contract_loi_tra_exit_code_khac_khong_khong_crash():
    with tempfile.TemporaryDirectory() as tmp:
        raw_path = Path(tmp) / "bad_raw.json"
        output_path = Path(tmp) / "bad_report.json"
        raw_path.write_text(json.dumps({"_meta": {}, "results": []}), encoding="utf-8")
        exit_code = main(["--dataset", "gold", "--raw", str(raw_path), "--output", str(output_path)])
        assert exit_code == 1
        assert not output_path.exists()
    print("[PASS] CLI raw contract loi tra exit code 1, khong ghi output, khong crash")


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
        test_cli_dataset_gold_ghi_report_json_atomic,
        test_cli_dataset_e1_ghi_report_json_atomic,
        test_cli_raw_contract_loi_tra_exit_code_khac_khong_khong_crash,
        test_report_only_khong_import_ai_core_agents,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

"""Metric tests report-only cho corrected-publish 30 + criterion-coverage 11.

Khong import agent/provider; row shape khop output that cua
``eval_policy_v2.run_policy_sample`` (decision_basis/effective_findings/
coverage/drift), rieng coverage row co them target_code/parent_sample_id
duoc join tu criterion-coverage-labels.csv boi caller.
"""
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_corrected_coverage  # noqa: E402
from eval_corrected_coverage import (  # noqa: E402
    EvaluationContractError,
    class_metrics,
    confusion,
    coverage_metrics,
    main,
    main_metrics,
)


LABELS = ["publish", "needs_revision", "rejected"]

_BASE_RELEASE = {
    "policy_version": "cam-nang-vn-v2",
    "guideline_version": "v1.4",
    "rubric_version": "v1",
    "guideline_hash": "gh-1",
    "rubric_hash": "rh-1",
    "prompt_version": "pv-1",
    "model": "claude-haiku-4-5-20251001",
    "scoring_hash": "sh-1",
    "policy_hash": "ph-1",
    "safety_rules_hash": "sr-1",
    "fact_kb_hash": "fk-1",
    "brand_kb_hash": "bk-1",
    "embedding_hash": "eh-1",
    "embedding_provenance": {"model": "BAAI/bge-m3", "mode": "local", "endpoint": None},
    "weights": {"seo": 1, "brand": 1, "content_quality": 1, "compliance": 1},
    "data_head": "8635a45c9aee1369f6f7b17b0918a580db7390da",
    "git_head": "c60b5e45bafec2890d7ae5dbbbe402ae5073741a",
}


def _row(
    sample_id,
    expected_label,
    decision,
    *,
    findings=None,
    blocking=None,
    coverage_complete=True,
    drift=None,
    target_code=None,
    parent_sample_id=None,
):
    row = {
        "sample_id": sample_id,
        "repeat_index": 1,
        "expected_label": expected_label,
        "decision": decision,
        "effective_findings": findings or [],
        "decision_basis": {"blocking_codes": blocking or [], "reason": "test"},
        "coverage": {"complete": coverage_complete},
        "drift": drift or [],
        "usage": [],
        "cost": {"estimated_usd": "0"},
        "latency": {"milliseconds": 1.0},
        "status": "complete",
    }
    if target_code is not None:
        row["target_code"] = target_code
    if parent_sample_id is not None:
        row["parent_sample_id"] = parent_sample_id
    return row


def _raw(dataset_kind, rows, **meta_overrides):
    meta = {
        **_BASE_RELEASE,
        "dataset_kind": dataset_kind,
        "ordered_sample_ids": [row["sample_id"] for row in rows],
        "repeats": 1,
    }
    meta.update(meta_overrides)
    return {"_meta": meta, "results": rows}


def _gold_33(overrides=None):
    overrides = overrides or {}
    rows = []
    for index in range(1, 21):
        sample_id = f"G-{index:03d}"
        expected, decision = overrides.get(sample_id, ("needs_revision", "needs_revision"))
        rows.append(_row(sample_id, expected, decision))
    for index in range(1, 14):
        sample_id = f"P-{index:03d}"
        expected, decision = overrides.get(sample_id, ("rejected", "rejected"))
        rows.append(_row(sample_id, expected, decision))
    return rows


def _corrected_30(overrides=None):
    overrides = overrides or {}
    rows = []
    for index in range(1, 11):
        sample_id = f"C-{index:03d}"
        decision = overrides.get(sample_id, "publish")
        rows.append(_row(sample_id, "publish", decision))
    for index in range(1, 21):
        sample_id = f"GC-{index:03d}"
        decision = overrides.get(sample_id, "publish")
        rows.append(_row(sample_id, "publish", decision))
    return rows


def _expect_error(label, fn, contains):
    try:
        fn()
    except EvaluationContractError as error:
        assert contains in str(error), str(error)
        print(f"[PASS] {label}")
    else:
        raise AssertionError(f"{label}: phai nem EvaluationContractError")


def test_confusion_luon_dung_thu_tu_nhan():
    expected = {"a": "publish", "b": "needs_revision", "c": "rejected"}
    predicted = {"a": "publish", "b": "rejected", "c": "rejected"}
    matrix = confusion(expected, predicted)
    assert list(matrix.keys()) == LABELS
    for truth in LABELS:
        assert list(matrix[truth].keys()) == LABELS
    assert matrix["needs_revision"]["rejected"] == 1
    print("[PASS] confusion luon dung thu tu publish,needs_revision,rejected")


def test_macro_f1_tinh_du_ba_lop():
    expected = {
        "s1": "publish", "s2": "publish",
        "s3": "needs_revision", "s4": "needs_revision",
        "s5": "rejected", "s6": "rejected",
    }
    predicted = {
        "s1": "publish", "s2": "needs_revision",
        "s3": "needs_revision", "s4": "needs_revision",
        "s5": "rejected", "s6": "publish",
    }
    metrics = class_metrics(expected, predicted)
    for label in LABELS:
        assert metrics["per_class"][label]["f1"] is not None
    manual_f1 = statistics_mean_of_present(metrics)
    assert abs(metrics["macro_f1"] - manual_f1) < 1e-9
    print("[PASS] macro-F1 tinh du ba lop trong bo 63")


def statistics_mean_of_present(metrics):
    values = [metrics["per_class"][label]["f1"] for label in LABELS]
    return sum(values) / len(values)


def test_denominator_khong_tra_mot():
    expected = {"s1": "publish", "s2": "publish"}
    predicted = {"s1": "publish", "s2": "publish"}
    metrics = class_metrics(expected, predicted)
    assert metrics["per_class"]["rejected"]["support"] == 0
    assert metrics["per_class"]["rejected"]["recall"] is None
    assert metrics["per_class"]["rejected"]["precision"] is None
    print("[PASS] denominator bang 0 tra NA/null, khong tra 1")


def test_false_publish_denominator_33_gold():
    gold_rows = _gold_33({"P-001": ("rejected", "publish")})
    corrected_rows = _corrected_30()
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    metrics = main_metrics(
        gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
    )
    assert metrics["gold_33"]["false_publish_count"] == 1
    assert metrics["gold_33"]["false_publish_rate"] == 1 / 33
    print("[PASS] false-publish chi co denominator 33 gold")


def test_corrected_publish_denominator_30():
    gold_rows = _gold_33()
    corrected_rows = _corrected_30({"GC-005": "needs_revision"})
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    metrics = main_metrics(
        gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
    )
    assert metrics["corrected_30"]["publish_count"] == 29
    assert metrics["corrected_30"]["publish_rate"] == 29 / 30
    assert metrics["corrected_30"]["false_block_count"] == 1
    print("[PASS] corrected publish co denominator dung 30")


def test_paired_recovery_yeu_cau_G_chan_va_GC_publish():
    # Mac dinh moi G-001..020 da publish (khong bi chan) -> khong the recovered.
    gold_overrides = {f"G-{i:03d}": ("publish", "publish") for i in range(1, 21)}
    gold_overrides["G-003"] = ("needs_revision", "needs_revision")  # bi chan, GC publish
    gold_overrides["G-007"] = ("needs_revision", "needs_revision")  # bi chan, GC KHONG publish
    gold_rows = _gold_33(gold_overrides)
    corrected_rows = _corrected_30({"GC-007": "needs_revision"})
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    metrics = main_metrics(
        gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
    )
    assert metrics["paired_20"]["recovered_count"] == 1
    assert metrics["paired_20"]["recovery_rate"] == 1 / 20
    print("[PASS] paired recovery yeu cau G bi chan va GC publish")


def _coverage_row(sample_id, target_code, parent_sample_id, expected_label, *, decision=None,
                   findings=None, blocking=None, coverage_complete=True, drift=None):
    decision = expected_label if decision is None else decision
    findings = findings if findings is not None else [{"defect_code": target_code}]
    blocking = blocking if blocking is not None else [target_code]
    return _row(
        sample_id, expected_label, decision,
        findings=findings, blocking=blocking,
        coverage_complete=coverage_complete, drift=drift,
        target_code=target_code, parent_sample_id=parent_sample_id,
    )


def _coverage_11(overrides=None):
    overrides = overrides or {}
    plan = [
        ("CV-A3-01", "A3", "GC-006", "rejected"),
        ("CV-A5-01", "A5", "GC-003", "rejected"),
        ("CV-A5-02", "A5", "GC-018", "rejected"),
        ("CV-A6-01", "A6", "GC-010", "rejected"),
        ("CV-A6-02", "A6", "C-008", "rejected"),
        ("CV-A7-01", "A7", "C-005", "rejected"),
        ("CV-A7-02", "A7", "GC-019", "rejected"),
        ("CV-B6-01", "B6", "C-001", "needs_revision"),
        ("CV-B7-01", "B7", "GC-018", "needs_revision"),
        ("CV-B9-01", "B9", "GC-011", "needs_revision"),
        ("CV-B9-02", "B9", "GC-016", "needs_revision"),
    ]
    rows = []
    for sample_id, target_code, parent_id, expected_label in plan:
        kwargs = overrides.get(sample_id, {})
        rows.append(_coverage_row(sample_id, target_code, parent_id, expected_label, **kwargs))
    return rows


def _coverage_context(coverage_rows):
    corrected_rows = _corrected_30()
    coverage_raw = _raw("coverage", coverage_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    return coverage_raw, corrected_raw


def test_cv_pass_can_ca_target_finding_va_expected_decision():
    rows = _coverage_11()
    coverage_raw, corrected_raw = _coverage_context(rows)
    metrics = coverage_metrics(rows, coverage_raw, corrected_raw)
    assert metrics["passed"] == 11
    assert metrics["failed"] == 0

    rows_wrong_decision = _coverage_11({
        "CV-A3-01": {"decision": "needs_revision", "blocking": ["B1"], "findings": [{"defect_code": "A3"}, {"defect_code": "B1"}]}
    })
    coverage_raw_2, corrected_raw_2 = _coverage_context(rows_wrong_decision)
    metrics_2 = coverage_metrics(rows_wrong_decision, coverage_raw_2, corrected_raw_2)
    assert metrics_2["passed"] == 10
    assert metrics_2["by_code"]["A3"]["failed"] == 1
    print("[PASS] CV chi pass khi co target finding va expected decision")


def test_cv_parent_phai_tiep_tuc_publish():
    rows = _coverage_11()
    corrected_rows = _corrected_30({"GC-006": "needs_revision"})
    coverage_raw = _raw("coverage", rows)
    corrected_raw = _raw("corrected", corrected_rows)
    metrics = coverage_metrics(rows, coverage_raw, corrected_raw)
    assert metrics["passed"] == 10
    assert metrics["by_code"]["A3"]["failed"] == 1
    print("[PASS] parent cua CV phai tiep tuc publish")


def test_cv_blocking_finding_ngoai_target_lam_isolation_fail():
    rows = _coverage_11({
        "CV-B6-01": {
            "blocking": ["B6", "B9"],
            "findings": [{"defect_code": "B6"}, {"defect_code": "B9"}],
        },
    })
    coverage_raw, corrected_raw = _coverage_context(rows)
    metrics = coverage_metrics(rows, coverage_raw, corrected_raw)
    assert metrics["passed"] == 10
    assert metrics["by_code"]["B6"]["failed"] == 1
    print("[PASS] blocking finding ngoai target lam isolation fail")


def test_thieu_hoac_duplicate_sample_trong_raw_la_fatal():
    gold_rows = _gold_33()
    corrected_rows = _corrected_30()
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    corrected_raw["results"] = corrected_raw["results"][:-1]
    _expect_error(
        "thieu sample trong raw la fatal",
        lambda: main_metrics(
            gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
        ),
        "corrected",
    )

    corrected_raw_dup = _raw("corrected", corrected_rows)
    corrected_raw_dup["results"].append(dict(corrected_raw_dup["results"][0]))
    _expect_error(
        "duplicate sample trong raw la fatal",
        lambda: main_metrics(
            gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw_dup,
        ),
        "duplicate",
    )
    print("[PASS] thieu/duplicate sample trong raw la fatal")


def test_release_meta_mismatch_giua_raw_files_la_fatal():
    gold_rows = _gold_33()
    corrected_rows = _corrected_30()
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows, policy_hash="ph-DIFFERENT")
    _expect_error(
        "release/meta mismatch giua raw files la fatal",
        lambda: main_metrics(
            gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
        ),
        "mismatch",
    )
    print("[PASS] release/meta mismatch giua raw files la fatal")


def test_main_metrics_output_shape():
    gold_rows = _gold_33()
    corrected_rows = _corrected_30()
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    metrics = main_metrics(
        gold_rows, corrected_rows[:10], corrected_rows[10:], gold_raw, corrected_raw,
    )
    assert set(metrics) == {"main_63", "gold_33", "corrected_30", "paired_20"}
    assert set(metrics["main_63"]) == {"confusion", "per_class", "macro_f1", "balanced_accuracy"}
    assert set(metrics["gold_33"]) >= {"kappa", "false_publish_count", "false_publish_rate"}
    assert set(metrics["corrected_30"]) == {"publish_count", "publish_rate", "false_block_count"}
    assert set(metrics["paired_20"]) == {"recovered_count", "recovery_rate"}
    print("[PASS] main_metrics tra dung shape 63/33/30/20")


def test_cli_report_corrected_ghi_json_atomic():
    gold_rows = _gold_33()
    corrected_rows = _corrected_30()
    gold_raw = _raw("gold", gold_rows)
    corrected_raw = _raw("corrected", corrected_rows)
    with tempfile.TemporaryDirectory() as tmp:
        gold_path = Path(tmp) / "gold_raw.json"
        corrected_path = Path(tmp) / "corrected_raw.json"
        output_path = Path(tmp) / "corrected_report.json"
        gold_path.write_text(json.dumps(gold_raw), encoding="utf-8")
        corrected_path.write_text(json.dumps(corrected_raw), encoding="utf-8")
        exit_code = main([
            "--report-corrected",
            "--gold-raw", str(gold_path),
            "--corrected-raw", str(corrected_path),
            "--output", str(output_path),
        ])
        assert exit_code == 0
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["corrected_30"]["publish_count"] == 30
    print("[PASS] CLI --report-corrected ghi report JSON atomic")


def test_cli_report_coverage_ghi_json_atomic():
    rows = _coverage_11()
    corrected_rows = _corrected_30()
    coverage_raw = _raw("coverage", rows)
    corrected_raw = _raw("corrected", corrected_rows)
    with tempfile.TemporaryDirectory() as tmp:
        coverage_path = Path(tmp) / "coverage_raw.json"
        corrected_path = Path(tmp) / "corrected_raw.json"
        output_path = Path(tmp) / "coverage_report.json"
        coverage_path.write_text(json.dumps(coverage_raw), encoding="utf-8")
        corrected_path.write_text(json.dumps(corrected_raw), encoding="utf-8")
        exit_code = main([
            "--report-coverage",
            "--coverage-raw", str(coverage_path),
            "--corrected-raw", str(corrected_path),
            "--output", str(output_path),
        ])
        assert exit_code == 0
        report = json.loads(output_path.read_text(encoding="utf-8"))
        assert report["passed"] == 11
    print("[PASS] CLI --report-coverage ghi report JSON atomic")


def test_report_only_khong_import_ai_core_agents():
    source = Path(eval_corrected_coverage.__file__).read_text(encoding="utf-8")
    assert "ai_core" not in source
    assert "src.agents" not in source
    assert "from agents" not in source
    assert "import agents" not in source
    print("[PASS] eval_corrected_coverage report-only khong import agent/provider")


if __name__ == "__main__":
    failed = False
    for test in (
        test_confusion_luon_dung_thu_tu_nhan,
        test_macro_f1_tinh_du_ba_lop,
        test_denominator_khong_tra_mot,
        test_false_publish_denominator_33_gold,
        test_corrected_publish_denominator_30,
        test_paired_recovery_yeu_cau_G_chan_va_GC_publish,
        test_cv_pass_can_ca_target_finding_va_expected_decision,
        test_cv_parent_phai_tiep_tuc_publish,
        test_cv_blocking_finding_ngoai_target_lam_isolation_fail,
        test_thieu_hoac_duplicate_sample_trong_raw_la_fatal,
        test_release_meta_mismatch_giua_raw_files_la_fatal,
        test_main_metrics_output_shape,
        test_cli_report_corrected_ghi_json_atomic,
        test_cli_report_coverage_ghi_json_atomic,
        test_report_only_khong_import_ai_core_agents,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

"""Pure report-only metrics cho corrected-publish (30) va criterion-coverage (11).

File nay chi doc object JSON/row da duoc validate boi caller; khong import
evaluator, model, agent hay provider. Row shape khop output that cua
``eval_policy_v2.run_policy_sample``: ``decision``, ``expected_label``,
``effective_findings`` (list finding co ``defect_code``),
``decision_basis.blocking_codes``, ``coverage.complete``, ``drift``.
Rieng coverage row can them ``target_code``/``parent_sample_id`` duoc join tu
``docs/functional-tests/criterion-coverage-labels.csv`` boi caller truoc khi
goi ``coverage_metrics``.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile
from typing import Any

from eval_policy_v2_metrics import (  # noqa: F401  (re-export cho caller)
    EvaluationContractError,
    LABEL_ORDER,
    LABEL_SET,
    gold_metrics,
)


GOLD_SAMPLE_COUNT = 33
CORRECTED_SAMPLE_COUNT = 30
PAIRED_SAMPLE_COUNT = 20
COVERAGE_SAMPLE_COUNT = 11

# Field trong _meta phai giong het giua cac raw file cung mot release; cac
# field con lai (dataset_kind, ordered_sample_ids, output_path,
# content_hashes_sha256, assessment_as_of) duoc phep khac nhau theo dataset.
_RELEASE_MATCH_FIELDS = (
    "policy_version",
    "guideline_version",
    "rubric_version",
    "guideline_hash",
    "rubric_hash",
    "prompt_version",
    "model",
    "scoring_hash",
    "policy_hash",
    "safety_rules_hash",
    "fact_kb_hash",
    "brand_kb_hash",
    "embedding_hash",
    "embedding_provenance",
    "weights",
    "data_head",
    "git_head",
)


def _validate_raw(raw: Any, dataset_kind: str, expected_count: int) -> tuple[dict, dict[str, dict]]:
    """Validate schema/inventory toi thieu; tra (_meta, rows theo sample_id)."""
    if not isinstance(raw, dict):
        raise EvaluationContractError("raw phai la object")
    meta = raw.get("_meta")
    rows = raw.get("results")
    if not isinstance(meta, dict) or not isinstance(rows, list):
        raise EvaluationContractError("raw phai co _meta object va results list")
    if meta.get("dataset_kind") != dataset_kind:
        raise EvaluationContractError(f"raw khong phai dataset {dataset_kind}")
    ids = meta.get("ordered_sample_ids")
    if (
        not isinstance(ids, list)
        or len(ids) != expected_count
        or len(set(ids)) != expected_count
    ):
        raise EvaluationContractError(
            f"dataset {dataset_kind} phai co dung {expected_count} sample duy nhat"
        )
    by_id: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise EvaluationContractError("result phai la object")
        sample_id = row.get("sample_id")
        if sample_id in by_id:
            raise EvaluationContractError(f"duplicate sample: {sample_id}")
        if row.get("decision") not in LABEL_SET or row.get("expected_label") not in LABEL_SET:
            raise EvaluationContractError(f"decision/expected_label khong hop le tai {sample_id}")
        by_id[sample_id] = row
    if set(by_id) != set(ids):
        missing = sorted(set(ids) - set(by_id))
        extra = sorted(set(by_id) - set(ids))
        raise EvaluationContractError(
            f"dataset {dataset_kind} thieu/du sample so voi ordered_sample_ids: "
            f"thieu={missing[:3]} du={extra[:3]}"
        )
    return meta, by_id


def _validate_release_match(*metas: dict) -> None:
    if len(metas) < 2:
        return
    baseline = metas[0]
    for field in _RELEASE_MATCH_FIELDS:
        expected = baseline.get(field)
        for other in metas[1:]:
            if other.get(field) != expected:
                raise EvaluationContractError(
                    f"release/meta mismatch giua raw files tai field {field!r}"
                )


def confusion(expected: dict[str, str], predicted: dict[str, str]) -> dict:
    """Ma tran nham lan confusion[truth][predicted] = count, luon theo LABEL_ORDER."""
    if set(expected) != set(predicted):
        raise EvaluationContractError("expected/predicted sample_id set khong khop")
    matrix = {truth: {pred: 0 for pred in LABEL_ORDER} for truth in LABEL_ORDER}
    for sample_id, truth in expected.items():
        pred = predicted[sample_id]
        if truth not in LABEL_SET or pred not in LABEL_SET:
            raise EvaluationContractError(f"label khong hop le tai {sample_id}")
        matrix[truth][pred] += 1
    return matrix


def class_metrics(
    expected: dict[str, str],
    predicted: dict[str, str],
    labels: list[str] = LABEL_ORDER,
) -> dict:
    """Confusion + per-class precision/recall/F1 + macro-F1 + balanced accuracy.

    Support (denominator) bang 0 tra ``None`` cho precision/recall/f1 cua lop
    do, khong tra 1.0. macro_f1/balanced_accuracy chi trung binh tren cac lop
    co gia tri xac dinh (khong ep support=0 thanh 0.0).
    """
    matrix = confusion(expected, predicted)
    per_class = {}
    recalls = []
    f1_scores = []
    for label in labels:
        support = sum(matrix[label].values())
        predicted_count = sum(matrix[truth][label] for truth in labels)
        true_positive = matrix[label][label]
        precision = None if predicted_count == 0 else true_positive / predicted_count
        recall = None if support == 0 else true_positive / support
        if precision is None or recall is None or (precision + recall) == 0:
            f1 = None
        else:
            f1 = 2 * precision * recall / (precision + recall)
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
        if recall is not None:
            recalls.append(recall)
        if f1 is not None:
            f1_scores.append(f1)
    return {
        "confusion": matrix,
        "per_class": per_class,
        "macro_f1": statistics.mean(f1_scores) if f1_scores else None,
        "balanced_accuracy": statistics.mean(recalls) if recalls else None,
    }


def main_metrics(
    gold_rows: list[dict],
    clean_rows: list[dict],
    corrected_rows: list[dict],
    gold_raw: dict,
    corrected_raw: dict,
) -> dict:
    """main_63 (gold 33 + clean 10 + corrected(GC) 20) + gold_33 + corrected_30 + paired_20.

    ``gold_raw``/``corrected_raw`` la wrapper JSON dung de validate schema,
    inventory va cross-file release/meta; ``*_rows`` la cac row da duoc cha
    trich xuat tu dung cac raw do (kiem tra doi chieu ben duoi).
    """
    gold_meta, gold_by_id = _validate_raw(gold_raw, "gold", GOLD_SAMPLE_COUNT)
    corrected_meta, corrected_by_id = _validate_raw(
        corrected_raw, "corrected", CORRECTED_SAMPLE_COUNT
    )
    _validate_release_match(gold_meta, corrected_meta)

    if {row["sample_id"] for row in gold_rows} != set(gold_by_id):
        raise EvaluationContractError("gold_rows khong khop gold_raw")
    combined_corrected_rows = list(clean_rows) + list(corrected_rows)
    if {row["sample_id"] for row in combined_corrected_rows} != set(corrected_by_id):
        raise EvaluationContractError("clean_rows/corrected_rows khong khop corrected_raw")

    main_expected = {row["sample_id"]: row["expected_label"] for row in gold_rows}
    main_predicted = {row["sample_id"]: row["decision"] for row in gold_rows}
    for row in combined_corrected_rows:
        main_expected[row["sample_id"]] = row["expected_label"]
        main_predicted[row["sample_id"]] = row["decision"]
    main_63 = class_metrics(main_expected, main_predicted)

    gold_report = gold_metrics(gold_raw)
    gold_33 = {
        "kappa": gold_report["kappa"],
        "false_publish_count": gold_report["false_publish_count"],
        "false_publish_rate": gold_report["false_publish_count"] / GOLD_SAMPLE_COUNT,
    }

    publish_count = sum(
        1 for row in combined_corrected_rows if row["decision"] == "publish"
    )
    false_block_count = sum(
        1
        for row in combined_corrected_rows
        if row["expected_label"] == "publish" and row["decision"] != "publish"
    )
    corrected_30 = {
        "publish_count": publish_count,
        "publish_rate": publish_count / CORRECTED_SAMPLE_COUNT,
        "false_block_count": false_block_count,
    }

    gold_prediction = {row["sample_id"]: row["decision"] for row in gold_rows}
    corrected_prediction = {row["sample_id"]: row["decision"] for row in corrected_rows}
    for index in range(1, PAIRED_SAMPLE_COUNT + 1):
        g_id = f"G-{index:03d}"
        gc_id = f"GC-{index:03d}"
        if g_id not in gold_prediction or gc_id not in corrected_prediction:
            raise EvaluationContractError(
                f"paired_20 thieu sample: can ca {g_id} va {gc_id}"
            )
    recovered = sum(
        gold_prediction[f"G-{index:03d}"] != "publish"
        and corrected_prediction[f"GC-{index:03d}"] == "publish"
        for index in range(1, PAIRED_SAMPLE_COUNT + 1)
    )
    paired_20 = {
        "recovered_count": recovered,
        "recovery_rate": recovered / PAIRED_SAMPLE_COUNT,
    }

    return {
        "main_63": main_63,
        "gold_33": gold_33,
        "corrected_30": corrected_30,
        "paired_20": paired_20,
    }


def coverage_metrics(
    coverage_rows: list[dict],
    coverage_raw: dict,
    corrected_raw: dict,
) -> dict:
    """Coverage 11: pass can dong thoi target finding, decision dung expected,
    parent tiep tuc publish, khong blocking code ngoai target va coverage/drift sach.
    """
    coverage_meta, coverage_by_id = _validate_raw(
        coverage_raw, "coverage", COVERAGE_SAMPLE_COUNT
    )
    corrected_meta, corrected_by_id = _validate_raw(
        corrected_raw, "corrected", CORRECTED_SAMPLE_COUNT
    )
    _validate_release_match(coverage_meta, corrected_meta)

    if {row["sample_id"] for row in coverage_rows} != set(coverage_by_id):
        raise EvaluationContractError("coverage_rows khong khop coverage_raw")

    passed = 0
    by_code: dict[str, dict[str, int]] = {}
    for row in coverage_rows:
        target_code = row.get("target_code")
        parent_id = row.get("parent_sample_id")
        if not target_code or not parent_id:
            raise EvaluationContractError(
                f"coverage row {row.get('sample_id')} thieu target_code/parent_sample_id"
            )
        parent_row = corrected_by_id.get(parent_id)
        if parent_row is None:
            raise EvaluationContractError(
                f"parent_sample_id {parent_id!r} khong ton tai trong corrected_raw"
            )
        finding_codes = {
            finding.get("defect_code") for finding in row.get("effective_findings", [])
        }
        blocking_codes = row.get("decision_basis", {}).get("blocking_codes", [])
        is_pass = (
            target_code in finding_codes
            and row["decision"] == row["expected_label"]
            and parent_row["decision"] == "publish"
            and blocking_codes == [target_code]
            and row.get("coverage", {}).get("complete") is True
            and not row.get("drift")
        )
        entry = by_code.setdefault(target_code, {"passed": 0, "failed": 0})
        if is_pass:
            passed += 1
            entry["passed"] += 1
        else:
            entry["failed"] += 1

    return {
        "passed": passed,
        "failed": COVERAGE_SAMPLE_COUNT - passed,
        "by_code": by_code,
    }


def _write_atomic(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _load_raw(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _split_corrected(corrected_raw: dict) -> tuple[list[dict], list[dict]]:
    """Corrected raw = 10 C (clean) + 20 GC (gold-corrected), tach theo prefix ID."""
    results = corrected_raw.get("results")
    if not isinstance(results, list):
        raise EvaluationContractError("corrected_raw.results phai la list")
    clean_rows = [row for row in results if str(row.get("sample_id", "")).startswith("C-")]
    corrected_rows = [row for row in results if str(row.get("sample_id", "")).startswith("GC-")]
    if len(clean_rows) + len(corrected_rows) != len(results):
        raise EvaluationContractError(
            "corrected_raw co sample_id khong thuoc prefix C-/GC-"
        )
    return clean_rows, corrected_rows


def main(argv: list[str]) -> int:
    """CLI report-only: --report-corrected hoac --report-coverage, ghi JSON atomic.

    Khong support --summary/--manifest o day: buoc tong hop Muc A/B/C doc
    evidence da 'approve' thuoc Task 9 cua Evaluation Plan, chua co du lieu
    that de dinh hinh dung dinh dang manifest.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--report-corrected", action="store_true")
    mode.add_argument("--report-coverage", action="store_true")
    parser.add_argument("--gold-raw", type=Path)
    parser.add_argument("--coverage-raw", type=Path)
    parser.add_argument("--corrected-raw", type=Path, required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        corrected_raw = _load_raw(args.corrected_raw)
        clean_rows, corrected_rows = _split_corrected(corrected_raw)
        if args.report_corrected:
            if args.gold_raw is None:
                print("[FAIL] --report-corrected can --gold-raw")
                return 1
            gold_raw = _load_raw(args.gold_raw)
            report = main_metrics(
                gold_raw["results"], clean_rows, corrected_rows, gold_raw, corrected_raw,
            )
        else:
            if args.coverage_raw is None:
                print("[FAIL] --report-coverage can --coverage-raw")
                return 1
            coverage_raw = _load_raw(args.coverage_raw)
            report = coverage_metrics(coverage_raw["results"], coverage_raw, corrected_raw)
    except (OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] khong doc/parse duoc raw file: {error}")
        return 1
    except EvaluationContractError as error:
        print(f"[FAIL] {error}")
        return 1

    _write_atomic(args.output, report)
    print(f"[OK] report ghi tai {args.output}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv[1:]))

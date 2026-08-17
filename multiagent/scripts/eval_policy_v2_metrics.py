"""Pure report-only metrics cho raw policy v2.

File nay chi doc object JSON; khong import evaluator, model, agent hay provider.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import math
import statistics
from typing import Any


LABEL_ORDER = ["publish", "needs_revision", "rejected"]
LABEL_SET = frozenset(LABEL_ORDER)


class EvaluationContractError(ValueError):
    """Raw schema/inventory khong du de tinh metric dang tin cay."""


def _validate_number(name: str, value: Any, *, allow_none: bool = False):
    if value is None and allow_none:
        return None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise EvaluationContractError(f"{name} phai la so")
    return float(value)


def _validated_rows(raw: dict, dataset_kind: str, repeats: int) -> tuple[dict, list[dict]]:
    if not isinstance(raw, dict):
        raise EvaluationContractError("raw phai la object")
    meta = raw.get("_meta")
    rows = raw.get("results")
    if not isinstance(meta, dict) or not isinstance(rows, list):
        raise EvaluationContractError("raw phai co _meta object va results list")
    if meta.get("dataset_kind") != dataset_kind:
        raise EvaluationContractError(f"raw khong phai dataset {dataset_kind}")
    if meta.get("repeats") != repeats:
        raise EvaluationContractError(f"{dataset_kind} repeat contract khong khop")
    ids = meta.get("ordered_sample_ids")
    if (
        not isinstance(ids, list)
        or not ids
        or not all(isinstance(sample_id, str) and sample_id for sample_id in ids)
    ):
        raise EvaluationContractError("ordered_sample_ids khong hop le")
    if len(ids) != len(set(ids)):
        raise EvaluationContractError("duplicate ordered sample ID")

    expected = [(sample_id, repeat) for sample_id in ids for repeat in range(1, repeats + 1)]
    actual = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise EvaluationContractError("result phai la object")
        key = (row.get("sample_id"), row.get("repeat_index"))
        if key in seen:
            raise EvaluationContractError(f"duplicate sample/repeat: {key}")
        seen.add(key)
        actual.append(key)
        if row.get("decision") not in LABEL_SET:
            raise EvaluationContractError(f"decision khong hop le tai {key}")
        if row.get("expected_label") not in LABEL_SET:
            raise EvaluationContractError(f"expected_label khong hop le tai {key}")
        _validate_number(f"{key}.final_score", row.get("final_score"), allow_none=True)
        if not isinstance(row.get("usage"), list):
            raise EvaluationContractError(f"{key}.usage phai la list")
        if not isinstance(row.get("cost"), dict):
            raise EvaluationContractError(f"{key}.cost phai la object")
        latency = row.get("latency")
        if not isinstance(latency, dict):
            raise EvaluationContractError(f"{key}.latency phai la object")
        _validate_number(f"{key}.latency.milliseconds", latency.get("milliseconds"))
        if row.get("status") != "complete":
            raise EvaluationContractError(f"{key}.status khong complete")
    if actual != expected:
        missing = [key for key in expected if key not in seen]
        raise EvaluationContractError(
            f"sample/repeat inventory thieu hoac sai thu tu: {missing[:3]}"
        )
    return meta, rows


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise EvaluationContractError("estimated_usd khong hop le") from error
    if not parsed.is_finite() or parsed < 0:
        raise EvaluationContractError("estimated_usd khong hop le")
    return parsed


def _usage_metrics(rows: list[dict]) -> dict:
    events = 0
    input_tokens = 0
    output_tokens = 0
    cost = Decimal(0)
    cost_known = True
    latency = []
    for row in rows:
        events += len(row["usage"])
        for usage in row["usage"]:
            if not isinstance(usage, dict):
                raise EvaluationContractError("usage entry phai la object")
            for key in ("input_tokens", "output_tokens"):
                value = usage.get(key)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise EvaluationContractError(f"usage.{key} khong hop le")
            input_tokens += usage["input_tokens"]
            output_tokens += usage["output_tokens"]
        current_cost = _decimal_or_none(row["cost"].get("estimated_usd"))
        if current_cost is None:
            cost_known = False
        else:
            cost += current_cost
        latency.append(float(row["latency"]["milliseconds"]))
    return {
        "events": events,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_usd": format(cost, "f") if cost_known else None,
        "mean_latency_ms": statistics.mean(latency) if latency else None,
    }


def _mode(decisions: list[str]) -> tuple[str, float]:
    counts = Counter(decisions)
    highest = max(counts.values())
    decision = next(label for label in LABEL_ORDER if counts[label] == highest)
    return decision, highest / len(decisions)


def stability_metrics(raw: dict) -> dict:
    """E1: decision consistency, per-sample mode va sigma final score."""
    meta, rows = _validated_rows(raw, "e1", 5)
    by_sample = {sample_id: [] for sample_id in meta["ordered_sample_ids"]}
    for row in rows:
        by_sample[row["sample_id"]].append(row)

    samples = {}
    agreements = 0
    sigmas = []
    for sample_id in meta["ordered_sample_ids"]:
        sample_rows = by_sample[sample_id]
        mode_decision, agreement = _mode([row["decision"] for row in sample_rows])
        scores = [float(row["final_score"]) for row in sample_rows
                  if row["final_score"] is not None]
        sigma = statistics.stdev(scores) if len(scores) > 1 else None
        if sigma is not None:
            sigmas.append(sigma)
        agreements += round(agreement * len(sample_rows))
        samples[sample_id] = {
            "mode_decision": mode_decision,
            "mode_agreement": agreement,
            "final_score_sigma": sigma,
        }

    consistency = agreements / len(rows)
    mean_sigma = statistics.mean(sigmas) if sigmas else None
    return {
        "dataset_kind": "e1",
        "sample_count": len(by_sample),
        "repeat_count": len(rows),
        "decision_consistency": consistency,
        "final_score_sigma": mean_sigma,
        "final_score_sigma_max": max(sigmas) if sigmas else None,
        "samples": samples,
        "usage": _usage_metrics(rows),
        "gate_status": {
            "decision_consistency": "PASS" if consistency >= 0.90 else "FAIL",
            "final_score_sigma": (
                "NA" if mean_sigma is None else "PASS" if mean_sigma < 2.0 else "FAIL"
            ),
        },
        "label_provenance": meta.get("label_provenance"),
    }


def _cohen_kappa(expected: list[str], predicted: list[str]) -> float | None:
    count = len(expected)
    if count == 0:
        return None
    observed = sum(a == b for a, b in zip(expected, predicted)) / count
    expected_counts = Counter(expected)
    predicted_counts = Counter(predicted)
    chance = sum(
        expected_counts[label] * predicted_counts[label]
        for label in LABEL_ORDER
    ) / (count * count)
    if chance == 1:
        return None
    return (observed - chance) / (1 - chance)


def _gate(value: float | None, threshold: float) -> str:
    if value is None:
        return "NA"
    return "PASS" if value >= threshold else "FAIL"


def gold_metrics(raw: dict) -> dict:
    """Gold: confusion expected-row/predicted-column, Kappa va safety recall."""
    meta, rows = _validated_rows(raw, "gold", 1)
    index = {label: position for position, label in enumerate(LABEL_ORDER)}
    confusion = [[0 for _ in LABEL_ORDER] for _ in LABEL_ORDER]
    expected = []
    predicted = []
    false_publish = 0
    for row in rows:
        truth = row["expected_label"]
        decision = row["decision"]
        expected.append(truth)
        predicted.append(decision)
        confusion[index[truth]][index[decision]] += 1
        if truth != "publish" and decision == "publish":
            false_publish += 1

    recall = {}
    for label in LABEL_ORDER:
        row_index = index[label]
        denominator = sum(confusion[row_index])
        recall[label] = (
            None if denominator == 0
            else confusion[row_index][row_index] / denominator
        )
    kappa = _cohen_kappa(expected, predicted)
    return {
        "dataset_kind": "gold",
        "sample_count": len(rows),
        "label_order": list(LABEL_ORDER),
        "confusion": confusion,
        "kappa": kappa,
        "recall": recall,
        "false_publish_count": false_publish,
        "false_publish_denominator": len(rows),
        "usage": _usage_metrics(rows),
        "gate_status": {
            "kappa": _gate(kappa, 0.60),
            "rejected_recall": _gate(recall["rejected"], 0.80),
            "needs_revision_recall": _gate(recall["needs_revision"], 0.80),
            "false_publish": "PASS" if false_publish == 0 else "FAIL",
        },
        "label_provenance": meta.get("label_provenance"),
        "provenance_limitation": "independent_label_reliability_not_demonstrated",
    }

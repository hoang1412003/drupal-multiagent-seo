r"""Regression cho refactor E2 va export evidence $0.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_e2_evidence_export.py
"""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import eval_brand_retrieval
import eval_retrieval
import export_e2_evidence


def test_factcheck_evaluate_schema_va_cli_giu_ket_qua():
    pairs = [
        {"query": "q1", "expected_model": "VF 8"},
        {"query": "q2", "expected_model": "VF 9"},
    ]
    original = eval_retrieval.retrieve

    def fake_retrieve(query, _content_type, _langcode, *, top_k):
        rows = {
            "q1": [{"model": "VF 8"}],
            "q2": [{"model": "khac"}, {"model": "VF 9"}],
        }[query]
        return rows[:top_k]

    eval_retrieval.retrieve = fake_retrieve
    try:
        result = eval_retrieval.evaluate(pairs=pairs)
    finally:
        eval_retrieval.retrieve = original
    assert set(result) == {
        "query_count", "recall_at_1", "recall_at_3", "threshold", "passed"
    }
    assert result == {
        "query_count": 2,
        "recall_at_1": 0.5,
        "recall_at_3": 1.0,
        "threshold": 0.9,
        "passed": True,
    }
    output = io.StringIO()
    with redirect_stdout(output):
        exit_code = eval_retrieval.print_report(result)
    assert exit_code == 0
    assert "recall@1 = 0.50" in output.getvalue()
    assert "recall@3 = 1.00" in output.getvalue()
    assert "DAT" in output.getvalue()
    print("[PASS] fact-check E2 tra schema on dinh va giu output/exit CLI")


def test_brand_evaluate_schema_bang_fixture_khong_cham_db():
    originals = (
        eval_brand_retrieval.GOLD_TOPICS,
        eval_brand_retrieval.parse_sample,
        eval_brand_retrieval.retrieve,
        eval_brand_retrieval.ti_trong_chunk,
    )
    eval_brand_retrieval.GOLD_TOPICS = {"G-001": "a", "G-002": "b"}
    eval_brand_retrieval.parse_sample = lambda path: {"title": Path(path).stem}

    def fake_retrieve(title, *_args, **_kwargs):
        topic = "a" if title == "G-001" else "b"
        return [
            {"topic_group": topic},
            {"topic_group": topic},
            {"topic_group": "khac"},
        ]

    eval_brand_retrieval.retrieve = fake_retrieve
    eval_brand_retrieval.ti_trong_chunk = lambda: {"a": 0.25, "b": 0.25}
    try:
        result = eval_brand_retrieval.evaluate()
    finally:
        (
            eval_brand_retrieval.GOLD_TOPICS,
            eval_brand_retrieval.parse_sample,
            eval_brand_retrieval.retrieve,
            eval_brand_retrieval.ti_trong_chunk,
        ) = originals
    assert set(result) == {
        "query_count",
        "top_k",
        "same_topic_hits",
        "total_chunks",
        "same_topic_rate",
        "random_baseline",
        "ratio_to_baseline",
        "threshold_ratio",
        "passed",
    }
    assert result["query_count"] == 2 and result["top_k"] == 3
    assert result["same_topic_hits"] == 4 and result["total_chunks"] == 6
    assert abs(result["same_topic_rate"] - 2 / 3) < 1e-12
    assert result["random_baseline"] == 0.25
    assert abs(result["ratio_to_baseline"] - 8 / 3) < 1e-12
    assert result["threshold_ratio"] == 1.5 and result["passed"] is True
    print("[PASS] brand E2 tra schema tu fixture, khong cham DB/model")


def test_export_schema_head_va_atomic_failure():
    original_fact = export_e2_evidence.eval_retrieval.evaluate
    original_brand = export_e2_evidence.eval_brand_retrieval.evaluate
    original_head = export_e2_evidence._head_commit
    original_now = export_e2_evidence._utc_now
    fact = {"passed": True, "query_count": 2}
    brand = {"passed": False, "query_count": 2}
    export_e2_evidence.eval_retrieval.evaluate = lambda: fact
    export_e2_evidence.eval_brand_retrieval.evaluate = lambda: brand
    export_e2_evidence._head_commit = lambda: "a" * 40
    export_e2_evidence._utc_now = lambda: datetime(
        2026, 8, 13, 15, 30, tzinfo=timezone.utc
    )
    try:
        summary = export_e2_evidence.build_summary()
    finally:
        export_e2_evidence.eval_retrieval.evaluate = original_fact
        export_e2_evidence.eval_brand_retrieval.evaluate = original_brand
        export_e2_evidence._head_commit = original_head
        export_e2_evidence._utc_now = original_now
    assert summary == {
        "experiment": "E2",
        "run_at": "2026-08-13T15:30:00Z",
        "head_commit": "a" * 40,
        "factcheck": fact,
        "brand": brand,
        "passed": False,
    }
    assert "ai_core" not in sys.modules

    destination = Path(__file__).with_name(".test_e2_evidence.json")
    destination.unlink(missing_ok=True)
    try:
        export_e2_evidence.write_evidence(summary, destination)
        loaded = json.loads(destination.read_text(encoding="utf-8"))
        assert loaded == summary
        assert not list(destination.parent.glob(".test_e2_evidence.json.*.tmp"))

        old = destination.read_bytes()
        original_replace = export_e2_evidence.os.replace
        export_e2_evidence.os.replace = lambda *_args: (_ for _ in ()).throw(
            OSError("replace failure")
        )
        try:
            try:
                export_e2_evidence.write_evidence(summary, destination)
            except OSError:
                pass
            else:
                raise AssertionError("write_evidence nuot loi os.replace")
        finally:
            export_e2_evidence.os.replace = original_replace
        assert destination.read_bytes() == old
        assert not list(destination.parent.glob(".test_e2_evidence.json.*.tmp"))
    finally:
        destination.unlink(missing_ok=True)
        for temporary in destination.parent.glob(".test_e2_evidence.json.*.tmp"):
            temporary.unlink(missing_ok=True)
    print("[PASS] export schema dung HEAD, JSON UTF-8 va ghi atomic")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_factcheck_evaluate_schema_va_cli_giu_ket_qua,
        test_brand_evaluate_schema_bang_fixture_khong_cham_db,
        test_export_schema_head_va_atomic_failure,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)

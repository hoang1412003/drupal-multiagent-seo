"""Contract test cho evaluator policy v2; hoan toan offline, khong goi LLM."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from decision_policy import POLICY_V2  # noqa: E402
from eval_policy_v2 import (  # noqa: E402
    EvaluationContractError,
    EvaluationSample,
    build_runtime_contract,
    load_dataset,
    run_policy_sample,
    run_samples,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
E1_IDS = [f"G-{index:03d}" for index in range(1, 11)]
GOLD_IDS = [
    *[f"G-{index:03d}" for index in range(1, 21)],
    "P-001a", "P-001b", "P-002a", "P-003a", "P-004a", "P-004b",
    "P-005a", "P-006a", "P-007a", "P-007b", "P-008a", "P-009a",
    "P-010a",
]


def _criteria(prefix, count):
    return [
        {"id": f"{prefix}{index}", "level": 2, "occurrences": []}
        for index in range(1, count + 1)
    ]


def clean_agent_results():
    return {
        "content_quality": {
            "score": 12.0,
            "criteria": _criteria("CQ", 8),
            "issues": [],
            "policy_checks": [{"id": "A5", "status": "absent"}],
            "unavailable_checks": [],
        },
        "seo": {
            "score": 12.0,
            "criteria": _criteria("SEO", 10),
            "issues": [],
            "unavailable_checks": [],
        },
        "brand": {
            "score": 12.0,
            "criteria": _criteria("BV", 7),
            "issues": [],
            "unavailable_checks": [],
        },
        "compliance": {
            "score": 12.0,
            "criteria": _criteria("CP", 8),
            "flags": [],
            "policy_checks": [{"id": "A6", "status": "not_applicable"}],
            "unavailable_checks": [],
        },
    }


def _fake_runner(**kwargs):
    return clean_agent_results()


def _fingerprint(value):
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _expect_contract_error(label, fn, contains=""):
    try:
        fn()
    except EvaluationContractError as error:
        assert contains in str(error), (label, str(error))
        print(f"[PASS] {label}")
    else:
        raise AssertionError(f"{label}: phai nem EvaluationContractError")


def test_load_e1_va_gold_exact_canonical_order():
    e1 = load_dataset("e1", REPO_ROOT)
    gold = load_dataset("gold", REPO_ROOT)
    assert [sample.sample_id for sample in e1] == E1_IDS
    assert [sample.sample_id for sample in gold] == GOLD_IDS
    assert len(gold) == 33
    assert all(sample.content_sha256 and len(sample.content_sha256) == 64 for sample in gold)
    assert all(sample.fields.get("image_alt") is not None for sample in gold)
    assert all(sample.expected_label in {"publish", "needs_revision", "rejected"}
               for sample in gold)
    print("[PASS] loader e1=G-001..010, gold=33 canonical AI-v1.4")


def test_unknown_dataset_fail_truoc_agent_import():
    before = {name for name in sys.modules if name == "agents" or name.startswith("agents.")}
    _expect_contract_error(
        "unknown dataset fail truoc import agent",
        lambda: load_dataset("gold-beta", REPO_ROOT),
        "dataset",
    )
    after = {name for name in sys.modules if name == "agents" or name.startswith("agents.")}
    assert after == before == set(), (before, after)


def test_e1_5_repeat_raw_schema_va_khong_ro_nhan():
    samples = load_dataset("e1", REPO_ROOT)
    seen = []

    def runner(**kwargs):
        seen.append(kwargs)
        return clean_agent_results()

    with tempfile.TemporaryDirectory(prefix="eval-v2-e1-") as temp:
        output = Path(temp) / "e1-raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "e1", samples, "2026-08-17", output
        )
        raw = run_samples(
            samples, output, contract, repeats=5, agent_runner=runner
        )

    assert len(raw["results"]) == 50
    for sample_id in E1_IDS:
        repeats = [row["repeat_index"] for row in raw["results"]
                   if row["sample_id"] == sample_id]
        assert repeats == [1, 2, 3, 4, 5], (sample_id, repeats)
    assert len(seen) == 50
    assert all(set(call) == {"fields", "policy_version", "assessment_as_of"}
               for call in seen)
    assert all("expected_label" not in repr(call) and "defect_codes" not in repr(call)
               for call in seen)
    assert raw["_meta"]["usage_events"] == 0
    assert raw["_meta"]["is_fixture"] is True
    meta_required = {
        "dataset_kind", "policy_version", "guideline_version",
        "rubric_version", "prompt_version", "model", "scoring_hash",
        "policy_hash", "safety_rules_hash", "fact_kb_hash",
        "brand_kb_hash", "embedding_provenance",
        "dataset_manifest_hashes", "content_hashes_sha256", "data_head",
        "git_head", "assessment_as_of", "created_at", "release_tuple",
    }
    assert meta_required <= set(raw["_meta"])
    required = {
        "sample_id", "repeat_index", "expected_label", "decision",
        "decision_basis", "coverage", "final_score", "usage", "cost",
        "latency", "release_tuple", "status",
    }
    assert all(required <= set(row) for row in raw["results"])
    # Agent fake sach khong xoa cac field-check tat dinh B3/B4 cua bai that;
    # o day chi khoa schema/inventory, khong gan ket qua mong doi theo label.
    assert all(row["decision"] in {"publish", "needs_revision", "rejected"}
               for row in raw["results"])
    print("[PASS] E1 50 flat results, schema day du, label khong vao runner")


def test_expected_label_khong_duoc_truyen_vao_agent_runner():
    seen = []

    def runner(**kwargs):
        seen.append(kwargs)
        return clean_agent_results()

    sample = EvaluationSample(
        sample_id="G-001",
        fields={
            "title": "Hướng dẫn sạc ô tô điện an toàn đúng cách",
            "body": "<h2>Hướng dẫn</h2><p>Nội dung an toàn.</p>",
            "summary": "Tóm tắt",
            "meta_description": "m" * 150,
            "url_alias": "/huong-dan-sac-o-to-dien-an-toan",
            "image_alt": "Ô tô điện đang sạc",
        },
        expected_label="rejected",
        split="gold",
        source_url="https://example.invalid/G-001",
        content_sha256="0" * 64,
    )
    with tempfile.TemporaryDirectory(prefix="eval-v2-label-") as temp:
        output = Path(temp) / "raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "gold", [sample], "2026-08-17", output
        )
        raw = run_samples([sample], output, contract, agent_runner=runner)
    assert len(raw["results"]) == 1
    assert set(seen[0]) == {"fields", "policy_version", "assessment_as_of"}
    assert "expected_label" not in repr(seen[0])
    assert raw["_meta"]["usage_events"] == 0
    print("[PASS] expected label cach ly khoi agent runner")


def test_unknown_policy_fail_truoc_runner():
    sample = load_dataset("e1", REPO_ROOT)[:1]
    calls = []
    with tempfile.TemporaryDirectory(prefix="eval-v2-policy-") as temp:
        output = Path(temp) / "raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "e1", sample, "2026-08-17", output
        )
        contract["policy_version"] = "cam-nang-vn-v2-beta"
        _expect_contract_error(
            "unknown policy fail truoc runner",
            lambda: run_samples(
                sample,
                output,
                contract,
                agent_runner=lambda **kwargs: calls.append(kwargs),
            ),
            "policy_version",
        )
    assert calls == []


def test_resume_release_tuple_mismatch_fatal_va_khong_ghi_de():
    samples = load_dataset("e1", REPO_ROOT)[:1]
    with tempfile.TemporaryDirectory(prefix="eval-v2-resume-") as temp:
        output = Path(temp) / "raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "e1", samples, "2026-08-17", output
        )
        run_samples(samples, output, contract, agent_runner=_fake_runner)
        original = output.read_bytes()

        for field, value in contract["release_tuple"].items():
            mutated = deepcopy(contract)
            if isinstance(value, str):
                mutated["release_tuple"][field] = value + "-drift"
            elif isinstance(value, list):
                mutated["release_tuple"][field] = value + ["DRIFT"]
            elif isinstance(value, dict):
                mutated["release_tuple"][field] = {**value, "drift": "1"}
            else:
                raise AssertionError(f"test chua biet mutate {field}: {type(value)}")
            mutated["release_sha256"] = _fingerprint(mutated["release_tuple"])
            _expect_contract_error(
                f"resume lech release field {field}",
                lambda current=mutated: run_samples(
                    samples, output, current, agent_runner=_fake_runner
                ),
            )
            assert output.read_bytes() == original, field

        missing = deepcopy(contract)
        del missing["release_tuple"]["policy_hash"]
        missing["release_sha256"] = _fingerprint(missing["release_tuple"])
        _expect_contract_error(
            "resume thieu release field fatal",
            lambda: run_samples(samples, output, missing, agent_runner=_fake_runner),
            "policy_hash",
        )
        assert output.read_bytes() == original


def test_inventory_duplicate_hoac_hole_deu_fatal():
    samples = load_dataset("e1", REPO_ROOT)[:1]
    with tempfile.TemporaryDirectory(prefix="eval-v2-inventory-") as temp:
        output = Path(temp) / "raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "e1", samples, "2026-08-17", output
        )
        raw = run_samples(
            samples, output, contract, repeats=3, agent_runner=_fake_runner
        )
        duplicate = deepcopy(raw)
        duplicate["results"].append(deepcopy(duplicate["results"][0]))
        output.write_text(json.dumps(duplicate, ensure_ascii=False), encoding="utf-8")
        _expect_contract_error(
            "inventory duplicate fatal",
            lambda: run_samples(
                samples, output, contract, repeats=3, agent_runner=_fake_runner
            ),
            "duplicate",
        )

        hole = deepcopy(raw)
        hole["results"] = [row for row in hole["results"] if row["repeat_index"] != 2]
        output.write_text(json.dumps(hole, ensure_ascii=False), encoding="utf-8")
        _expect_contract_error(
            "inventory hole/missing repeat fatal",
            lambda: run_samples(
                samples, output, contract, repeats=3, agent_runner=_fake_runner
            ),
            "repeat",
        )


def test_score_nan_bi_chan_va_khong_tao_raw():
    samples = load_dataset("e1", REPO_ROOT)[:1]

    def invalid_runner(**kwargs):
        results = clean_agent_results()
        results["content_quality"]["score"] = float("nan")
        return results

    with tempfile.TemporaryDirectory(prefix="eval-v2-nan-") as temp:
        output = Path(temp) / "raw.json"
        contract = build_runtime_contract(
            REPO_ROOT, "e1", samples, "2026-08-17", output
        )
        _expect_contract_error(
            "score NaN bi chan truoc raw",
            lambda: run_samples(
                samples, output, contract, agent_runner=invalid_runner
            ),
            "score",
        )
        assert not output.exists()


if __name__ == "__main__":
    failed = False
    for test in (
        test_load_e1_va_gold_exact_canonical_order,
        test_unknown_dataset_fail_truoc_agent_import,
        test_e1_5_repeat_raw_schema_va_khong_ro_nhan,
        test_expected_label_khong_duoc_truyen_vao_agent_runner,
        test_unknown_policy_fail_truoc_runner,
        test_resume_release_tuple_mismatch_fatal_va_khong_ghi_de,
        test_inventory_duplicate_hoac_hole_deu_fatal,
        test_score_nan_bi_chan_va_khong_tao_raw,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

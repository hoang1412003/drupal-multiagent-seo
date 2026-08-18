"""Negative/contract tests cho release guard policy v2; khong goi provider."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_policy_v2 import (  # noqa: E402
    EvaluationContractError,
    build_runtime_contract,
    load_dataset,
    run_samples,
)
from policy_release import (  # noqa: E402
    ReleaseContractError,
    approve,
    authorize_paid_run,
    build_preflight,
    build_parser,
    confirmation_token,
    freeze,
    protected_paths,
    record_preflight,
    record_result,
    verify,
)


SOURCE_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_REL = Path("docs/evidence/publish-policy-v2-manifest.json")


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, text=True, encoding="utf-8"
    ).strip()


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _expect_error(label, fn, contains):
    try:
        fn()
    except ReleaseContractError as error:
        assert contains in str(error), (label, str(error))
        print(f"[PASS] {label}")
    else:
        raise AssertionError(f"{label}: phai nem ReleaseContractError")


def _fixture_repo(temp: Path) -> tuple[Path, Path]:
    repo = temp / "repo"
    repo.mkdir()
    for relative in protected_paths(SOURCE_ROOT):
        source = SOURCE_ROOT / relative
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    manifest_source = SOURCE_ROOT / MANIFEST_REL
    manifest = repo / MANIFEST_REL
    manifest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest_source, manifest)

    _git(repo, "init")
    _git(repo, "config", "user.email", "release-test@example.invalid")
    _git(repo, "config", "user.name", "Release Test")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture protected source")
    data_head = _git(
        repo, "log", "-1", "--format=%H", "--",
        "docs/goldset", "docs/functional-tests",
    )
    skeleton = json.loads(manifest.read_text(encoding="utf-8"))
    skeleton["data_head"] = data_head
    _write_json(manifest, skeleton)
    _git(repo, "add", str(MANIFEST_REL).replace("\\", "/"))
    _git(repo, "commit", "-m", "set fixture data head")
    # Data HEAD la checkpoint da verify snapshot, khong nhat thiet la commit
    # cuoi truc tiep cham thu muc data (giong checkpoint 8635a45 cua repo that).
    checkpoint = repo / "checkpoint.txt"
    checkpoint.write_text("verified data snapshot\n", encoding="utf-8")
    _git(repo, "add", "checkpoint.txt")
    _git(repo, "commit", "-m", "verify fixture data snapshot")
    skeleton["data_head"] = _git(repo, "rev-parse", "HEAD")
    _write_json(manifest, skeleton)
    return repo, manifest


def _frozen(temp: Path) -> tuple[Path, Path, dict]:
    repo, manifest_path = _fixture_repo(temp)
    frozen = freeze(manifest_path, repo)
    assert frozen["release_source_commit"] == _git(repo, "rev-parse", "HEAD")
    assert verify(manifest_path, repo)["verified"] is True
    return repo, manifest_path, frozen


def test_manifest_incomplete_neu_thieu_data_policy_protocol_hash():
    with tempfile.TemporaryDirectory(prefix="release-incomplete-") as raw_temp:
        repo, manifest_path, frozen = _frozen(Path(raw_temp))
        for field in ("data_head", "policy_hash", "protocol_hash"):
            broken = deepcopy(frozen)
            del broken[field]
            _write_json(manifest_path, broken)
            _expect_error(
                f"manifest thieu {field}",
                lambda: verify(manifest_path, repo),
                field,
            )
        _write_json(manifest_path, frozen)


def test_artifact_drift_prompt_safety_scoring_dataset_deu_fail():
    cases = (
        "multiagent/src/agents/content_quality.py",
        "multiagent/src/kb/safety_rules.json",
        "multiagent/config/scoring.yaml",
        "docs/goldset/raw/G-001.txt",
    )
    with tempfile.TemporaryDirectory(prefix="release-drift-") as raw_temp:
        repo, manifest_path, _ = _frozen(Path(raw_temp))
        for relative in cases:
            path = repo / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\nDRIFT")
            _expect_error(
                f"artifact drift {relative}",
                lambda: verify(manifest_path, repo),
                "artifact drift",
            )
            path.write_bytes(original)
        assert verify(manifest_path, repo)["verified"] is True


def test_freeze_chan_dirty_protected_va_giu_manifest_nguyen_byte():
    with tempfile.TemporaryDirectory(prefix="release-dirty-") as raw_temp:
        repo, manifest_path = _fixture_repo(Path(raw_temp))
        protected = repo / "multiagent/config/scoring.yaml"
        protected.write_bytes(protected.read_bytes() + b"\nDIRTY")
        before = manifest_path.read_bytes()
        _expect_error(
            "freeze chan dirty protected path",
            lambda: freeze(manifest_path, repo),
            "dirty protected",
        )
        assert manifest_path.read_bytes() == before


def test_protocol_commit_phai_la_ancestor_release_source():
    with tempfile.TemporaryDirectory(prefix="release-protocol-") as raw_temp:
        repo, manifest_path, frozen = _frozen(Path(raw_temp))
        _git(repo, "add", str(MANIFEST_REL).replace("\\", "/"))
        _git(repo, "commit", "-m", "manifest-only freeze")
        late_commit = _git(repo, "rev-parse", "HEAD")
        broken = deepcopy(frozen)
        broken["protocol_commit"] = late_commit
        broken["release_tuple"]["protocol_commit"] = late_commit
        broken["release_sha256"] = policy_fingerprint(broken["release_tuple"])
        _write_json(manifest_path, broken)
        _expect_error(
            "protocol late khong phai ancestor",
            lambda: verify(manifest_path, repo),
            "protocol_commit",
        )


def test_token_replay_va_bound_field_drift():
    with tempfile.TemporaryDirectory(prefix="release-token-") as raw_temp:
        repo, manifest_path, manifest = _frozen(Path(raw_temp))
        e1_ids = manifest["datasets"]["e1"]["ordered_ids"]
        output = Path(raw_temp) / "e1-raw.json"
        token = confirmation_token(
            manifest=manifest,
            dataset_kind="e1",
            ordered_ids=e1_ids,
            assessment_as_of="2026-08-17",
            output_path=output,
        )

        _expect_error(
            "token E1 khong replay sang gold",
            lambda: authorize_paid_run(
                manifest,
                "gold",
                Path(raw_temp) / "gold-raw.json",
                "2026-08-17",
                token,
            ),
            "token mismatch",
        )
        for label, dataset, target, assessment, current in (
            ("dataset", "gold", output, "2026-08-17", manifest),
            ("output", "e1", Path(raw_temp) / "other.json", "2026-08-17", manifest),
            ("date", "e1", output, "2026-08-18", manifest),
        ):
            _expect_error(
                f"token bind exact {label}",
                lambda d=dataset, o=target, a=assessment, m=current: authorize_paid_run(
                    m, d, o, a, token
                ),
                "token mismatch",
            )
        drifted = deepcopy(manifest)
        drifted["model"] += "-drift"
        drifted["release_tuple"]["model"] += "-drift"
        drifted["release_sha256"] = policy_fingerprint(drifted["release_tuple"])
        _expect_error(
            "token bind exact release tuple",
            lambda: authorize_paid_run(
                drifted, "e1", output, "2026-08-17", token
            ),
            "token mismatch",
        )

        runtime = {"release_sha256": "a" * 64}
        runtime_token = confirmation_token(
            manifest=manifest,
            dataset_kind="e1",
            ordered_ids=e1_ids,
            assessment_as_of="2026-08-17",
            output_path=output,
            runtime_contract=runtime,
        )
        _expect_error(
            "token bind exact runtime release",
            lambda: authorize_paid_run(
                manifest,
                "e1",
                output,
                "2026-08-17",
                runtime_token,
                runtime_contract={"release_sha256": "b" * 64},
            ),
            "token mismatch",
        )
        assert verify(manifest_path, repo)["verified"] is True


def policy_fingerprint(value: dict) -> str:
    import hashlib

    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_unknown_policy_va_paid_env_off_chan_truoc_output():
    with tempfile.TemporaryDirectory(prefix="release-paid-") as raw_temp:
        _, _, manifest = _frozen(Path(raw_temp))
        ids = manifest["datasets"]["e1"]["ordered_ids"]
        output = Path(raw_temp) / "e1-raw.json"
        token = confirmation_token(
            manifest=manifest,
            dataset_kind="e1",
            ordered_ids=ids,
            assessment_as_of="2026-08-17",
            output_path=output,
        )
        unknown = deepcopy(manifest)
        unknown["policy_version"] = "cam-nang-vn-v2-beta"
        _expect_error(
            "unknown policy fail closed",
            lambda: authorize_paid_run(
                unknown, "e1", output, "2026-08-17", token
            ),
            "policy_version",
        )

        old = os.environ.get("VF_ALLOW_PAID_EVAL")
        os.environ["VF_ALLOW_PAID_EVAL"] = "0"
        try:
            _expect_error(
                "paid env 0 chan du token dung",
                lambda: authorize_paid_run(
                    manifest, "e1", output, "2026-08-17", token
                ),
                "VF_ALLOW_PAID_EVAL",
            )
        finally:
            if old is None:
                os.environ.pop("VF_ALLOW_PAID_EVAL", None)
            else:
                os.environ["VF_ALLOW_PAID_EVAL"] = old
        assert not output.exists()


def _criteria(prefix, count):
    return [{"id": f"{prefix}{i}", "level": 2, "occurrences": []}
            for i in range(1, count + 1)]


def _clean_results(**kwargs):
    return {
        "content_quality": {"score": 100.0, "criteria": _criteria("CQ", 8),
                            "policy_checks": [{"id": "A5", "status": "absent"}],
                            "unavailable_checks": []},
        "seo": {"score": 100.0, "criteria": _criteria("SEO", 10),
                "unavailable_checks": []},
        "brand": {"score": 100.0, "criteria": _criteria("BV", 7),
                  "unavailable_checks": []},
        "compliance": {"score": 100.0, "criteria": _criteria("CP", 8),
                       "flags": [],
                       "policy_checks": [{"id": "A6", "status": "not_applicable"}],
                       "unavailable_checks": []},
    }


def test_fake_raw_marker_true_va_authorized_builder_false():
    with tempfile.TemporaryDirectory(prefix="release-fixture-") as raw_temp:
        _, _, manifest = _frozen(Path(raw_temp))
        samples = load_dataset("e1", SOURCE_ROOT)[:1]
        output = Path(raw_temp) / "fixture.json"
        contract = build_runtime_contract(
            SOURCE_ROOT, "e1", samples, "2026-08-17", output
        )
        raw = run_samples(samples, output, contract, agent_runner=_clean_results)
        assert raw["_meta"]["is_fixture"] is True

        real_output = Path(raw_temp) / "real.json"
        token = confirmation_token(
            manifest=manifest,
            dataset_kind="e1",
            ordered_ids=manifest["datasets"]["e1"]["ordered_ids"],
            assessment_as_of="2026-08-17",
            output_path=real_output,
        )
        old = os.environ.get("VF_ALLOW_PAID_EVAL")
        os.environ["VF_ALLOW_PAID_EVAL"] = "1"
        try:
            authorization = authorize_paid_run(
                manifest, "e1", real_output, "2026-08-17", token
            )
        finally:
            if old is None:
                os.environ.pop("VF_ALLOW_PAID_EVAL", None)
            else:
                os.environ["VF_ALLOW_PAID_EVAL"] = old
        assert authorization["is_fixture"] is False
        assert not real_output.exists(), "authorize chi mo gate, khong tu chay provider"
        print("[PASS] fake raw=true; authorized real builder=false va chua goi provider")


def test_preflight_zero_usage_va_default_runner_can_authorization():
    with tempfile.TemporaryDirectory(prefix="release-preflight-") as raw_temp:
        repo, _, manifest = _frozen(Path(raw_temp))
        samples = load_dataset("e1", repo)
        output = Path(raw_temp) / "e1-real.json"
        contract = build_runtime_contract(
            repo,
            "e1",
            samples,
            "2026-08-17",
            output,
            data_head=manifest["data_head"],
        )
        before_agents = {
            name for name in sys.modules if name.startswith("agents.")
        }
        preflight = build_preflight(
            manifest, contract, repeats=5, repo_root=repo
        )
        after_agents = {
            name for name in sys.modules if name.startswith("agents.")
        }

        assert preflight["kind"] == "preflight_only_not_experiment_result"
        assert preflight["usage_events"] == 0
        assert preflight["sample_count"] == 10
        assert preflight["repeats"] == 5
        assert preflight["estimated_max_calls"] == 400
        assert len(preflight["confirmation_token"]) == 64
        assert after_agents == before_agents
        assert not output.exists()

        old = os.environ.get("VF_ALLOW_PAID_EVAL")
        os.environ["VF_ALLOW_PAID_EVAL"] = "0"
        try:
            try:
                run_samples(samples, output, contract)
            except EvaluationContractError as error:
                assert "paid authorization" in str(error), str(error)
            else:
                raise AssertionError(
                    "default runner khong duoc chay neu thieu authorization"
                )

            forged = {
                "authorized": True,
                "is_fixture": False,
                "dataset_kind": "e1",
                "release_sha256": manifest["release_sha256"],
                "runtime_release_sha256": "0" * 64,
                "confirmation_token_hash": "1" * 64,
            }
            try:
                run_samples(
                    samples,
                    output,
                    contract,
                    paid_authorization=forged,
                )
            except EvaluationContractError as error:
                assert "runtime release" in str(error), str(error)
            else:
                raise AssertionError(
                    "authorization lech runtime release phai bi chan"
                )
        finally:
            if old is None:
                os.environ.pop("VF_ALLOW_PAID_EVAL", None)
            else:
                os.environ["VF_ALLOW_PAID_EVAL"] = old
        assert not output.exists()
        assert {
            name for name in sys.modules if name.startswith("agents.")
        } == before_agents
        print("[PASS] preflight $0; default runner fail truoc provider khi thieu gate")


def test_record_preflight_recompute_token_va_record_result_chan_fixture():
    with tempfile.TemporaryDirectory(prefix="release-record-") as raw_temp:
        repo, manifest_path, manifest = _frozen(Path(raw_temp))
        original = manifest_path.read_bytes()
        samples = load_dataset("e1", repo)
        output = Path(raw_temp) / "e1-real.json"
        contract = build_runtime_contract(
            repo,
            "e1",
            samples,
            "2026-08-17",
            output,
            data_head=manifest["data_head"],
        )
        preflight = build_preflight(
            manifest, contract, repeats=5, repo_root=repo
        )
        preflight["confirmation_token"] = "0" * 64
        preflight_path = Path(raw_temp) / "preflight.json"
        _write_json(preflight_path, preflight)
        _expect_error(
            "record-preflight recompute token",
            lambda: record_preflight(
                manifest_path, repo, "e1", preflight_path
            ),
            "confirmation token mismatch",
        )
        assert manifest_path.read_bytes() == original

        fixture_raw = Path(raw_temp) / "fixture-raw.json"
        report = Path(raw_temp) / "report.json"
        _write_json(
            fixture_raw,
            {
                "_meta": {
                    "dataset_kind": "e1",
                    "is_fixture": True,
                },
                "results": [],
            },
        )
        _write_json(report, {})
        _expect_error(
            "record-result chan fixture raw",
            lambda: record_result(
                manifest_path,
                repo,
                "e1",
                raw_path=fixture_raw,
                report_path=report,
            ),
            "fixture",
        )
        assert manifest_path.read_bytes() == original

        _write_json(
            fixture_raw,
            {
                "_meta": {
                    "dataset_kind": "e1",
                    "is_fixture": False,
                    "ordered_sample_ids": ["X-001"],
                    "repeats": 5,
                    "release_tuple": {},
                    "release_sha256": "0" * 64,
                },
                "results": [],
            },
        )
        _expect_error(
            "record-result chan sai canonical inventory",
            lambda: record_result(
                manifest_path,
                repo,
                "e1",
                raw_path=fixture_raw,
                report_path=report,
            ),
            "ordered sample IDs",
        )
        assert manifest_path.read_bytes() == original


def test_cli_khong_co_force():
    parser = build_parser()
    try:
        parser.parse_args([
            "freeze", "--manifest", "manifest.json", "--repo-root", ".", "--force"
        ])
    except SystemExit:
        print("[PASS] CLI khong co --force")
    else:
        raise AssertionError("CLI freeze khong duoc nhan --force")


def _metric_row(sample, repeat, expected, decision, release_tuple):
    return {
        "sample_id": sample, "repeat_index": repeat,
        "expected_label": expected, "decision": decision,
        "final_score": 100.0, "usage": [],
        "cost": {"estimated_usd": "0"},
        "latency": {"milliseconds": 1.0}, "status": "complete",
        "release_tuple": release_tuple,
    }


def _real_meta(contract, repeats):
    return {
        **contract["release_tuple"],
        "schema_version": 1,
        "repeats": repeats,
        "release_tuple": contract["release_tuple"],
        "release_sha256": contract["release_sha256"],
        "label_provenance": "AI-annotated-partially-exposed",
        "is_fixture": False,
        "usage_events": 0,
    }


def test_approve_recompute_gate_nhung_khong_bia_label_doc_lap():
    with tempfile.TemporaryDirectory(prefix="release-approve-") as raw_temp:
        repo, manifest_path, manifest = _frozen(Path(raw_temp))
        evidence = Path(raw_temp) / "evidence"
        e1_samples = load_dataset("e1", repo)
        gold_samples = load_dataset("gold", repo)
        e1_contract = build_runtime_contract(
            repo,
            "e1",
            e1_samples,
            "2026-08-17",
            evidence / "e1.json",
            data_head=manifest["data_head"],
        )
        gold_contract = build_runtime_contract(
            repo,
            "gold",
            gold_samples,
            "2026-08-17",
            evidence / "gold.json",
            data_head=manifest["data_head"],
        )
        e1_ids = manifest["datasets"]["e1"]["ordered_ids"]
        e1_raw = {
            "_meta": _real_meta(e1_contract, 5),
            "results": [
                _metric_row(
                    sample_id,
                    repeat,
                    "needs_revision",
                    "needs_revision",
                    e1_contract["release_tuple"],
                )
                for sample_id in e1_ids
                for repeat in range(1, 6)
            ],
        }
        gold_pairs = [
            (sample_id,
             "needs_revision" if index <= 20 else "rejected")
            for index, sample_id in enumerate(
                manifest["datasets"]["gold"]["ordered_ids"], start=1
            )
        ]
        gold_raw = {
            "_meta": _real_meta(gold_contract, 1),
            "results": [
                _metric_row(
                    sample,
                    1,
                    expected,
                    expected,
                    gold_contract["release_tuple"],
                )
                for sample, expected in gold_pairs
            ],
        }
        paths = {}
        for name, value in (
            ("e1", e1_raw),
            ("gold", gold_raw),
            ("corrected", {"corrected_publish_count": 30,
                           "corrected_total": 30,
                           "paired_recovery_count": 20,
                           "paired_recovery_total": 20,
                           "drift_count": 0}),
            ("coverage", {"target_decision_parent_pass_count": 11,
                          "coverage_total": 11,
                          "failure_count": 0,
                          "drift_count": 0}),
        ):
            path = evidence / f"{name}.json"
            _write_json(path, value)
            paths[name] = path
            record_result(
                manifest_path,
                repo,
                name,
                raw_path=path if name in {"e1", "gold"} else None,
                report_path=path,
            )
        approved = approve(manifest_path, repo)
        assert approved["approval"]["measured_complete"] is True
        assert approved["approval"]["level_b"] == "pass"
        assert approved["independent_label_reliability"] == "not_demonstrated"
        assert approved["approval"]["independent_label_reliability"] == "not_demonstrated"
        assert approved["approval"]["approved_for_limited_pilot"] is False
        print("[PASS] approve recompute gate nhung label doc lap van not_demonstrated")


if __name__ == "__main__":
    failed = False
    for test in (
        test_manifest_incomplete_neu_thieu_data_policy_protocol_hash,
        test_artifact_drift_prompt_safety_scoring_dataset_deu_fail,
        test_freeze_chan_dirty_protected_va_giu_manifest_nguyen_byte,
        test_protocol_commit_phai_la_ancestor_release_source,
        test_token_replay_va_bound_field_drift,
        test_unknown_policy_va_paid_env_off_chan_truoc_output,
        test_fake_raw_marker_true_va_authorized_builder_false,
        test_preflight_zero_usage_va_default_runner_can_authorization,
        test_record_preflight_recompute_token_va_record_result_chan_fixture,
        test_cli_khong_co_force,
        test_approve_recompute_gate_nhung_khong_bia_label_doc_lap,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

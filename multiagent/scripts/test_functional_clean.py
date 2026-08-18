"""Test wrapper tuong thich eval_functional_clean.py -> policy v2.

Wrapper nay khong con tu goi 4 agent (cham_mot_bai v1); moi lenh phai forward
sang eval_policy_v2.cli() (preflight/run) hoac eval_corrected_coverage.main()
(report), tai su dung nguyen manifest/guard/confirmation-token chung.
Chay: .venv\\Scripts\\python.exe scripts\\test_functional_clean.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_functional_clean  # noqa: E402


def test_run_forward_dung_dataset_corrected():
    captured = {}

    def fake_cli(argv):
        captured["argv"] = argv
        return 0

    original = eval_functional_clean.eval_policy_v2.cli
    eval_functional_clean.eval_policy_v2.cli = fake_cli
    try:
        exit_code = eval_functional_clean.main([
            "--run",
            "--manifest", "m.json",
            "--output", "out.json",
            "--assessment-as-of", "2026-08-18",
            "--confirmation-token", "tok",
        ])
    finally:
        eval_functional_clean.eval_policy_v2.cli = original

    assert exit_code == 0
    argv = captured["argv"]
    assert "--dataset" in argv and argv[argv.index("--dataset") + 1] == "corrected"
    assert "--run" in argv
    assert "--preflight" not in argv
    assert "--manifest" in argv and argv[argv.index("--manifest") + 1] == "m.json"
    assert "--confirmation-token" in argv and argv[argv.index("--confirmation-token") + 1] == "tok"
    print("[PASS] --run forward dung --dataset corrected sang eval_policy_v2.cli")


def test_preflight_forward_dung_dataset_corrected():
    captured = {}

    def fake_cli(argv):
        captured["argv"] = argv
        return 0

    original = eval_functional_clean.eval_policy_v2.cli
    eval_functional_clean.eval_policy_v2.cli = fake_cli
    try:
        exit_code = eval_functional_clean.main([
            "--preflight",
            "--manifest", "m.json",
            "--output", "out.json",
            "--assessment-as-of", "2026-08-18",
        ])
    finally:
        eval_functional_clean.eval_policy_v2.cli = original

    assert exit_code == 0
    argv = captured["argv"]
    assert "--dataset" in argv and argv[argv.index("--dataset") + 1] == "corrected"
    assert "--preflight" in argv
    assert "--run" not in argv
    print("[PASS] --preflight forward dung --dataset corrected sang eval_policy_v2.cli")


def test_report_forward_dung_report_corrected():
    captured = {}

    def fake_main(argv):
        captured["argv"] = argv
        return 0

    original = eval_functional_clean.eval_corrected_coverage.main
    eval_functional_clean.eval_corrected_coverage.main = fake_main
    try:
        exit_code = eval_functional_clean.main([
            "--report",
            "--gold-raw", "g.json",
            "--output", "c.json",
            "--report-output", "r.json",
        ])
    finally:
        eval_functional_clean.eval_corrected_coverage.main = original

    assert exit_code == 0
    assert captured["argv"] == [
        "--report-corrected",
        "--gold-raw", "g.json",
        "--corrected-raw", "c.json",
        "--output", "r.json",
    ]
    print("[PASS] --report forward dung --report-corrected sang eval_corrected_coverage.main")


def test_khong_tu_goi_bon_agent_v1():
    source = Path(eval_functional_clean.__file__).read_text(encoding="utf-8")
    assert "cham_mot_bai" not in source
    assert "eval_calibration" not in source
    assert "quyet_dinh" not in source
    print("[PASS] wrapper khong con tu goi cham_mot_bai/quyet_dinh v1")


if __name__ == "__main__":
    failed = False
    for test in (
        test_run_forward_dung_dataset_corrected,
        test_preflight_forward_dung_dataset_corrected,
        test_report_forward_dung_report_corrected,
        test_khong_tu_goi_bon_agent_v1,
    ):
        try:
            test()
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {type(error).__name__}: {error}")
    sys.exit(1 if failed else 0)

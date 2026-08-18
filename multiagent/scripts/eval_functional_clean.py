"""Wrapper tuong thich: chay/bao cao dataset "corrected" (10 C + 20 GC) qua
policy v2 (technical-debt.md muc 8.6 - luong v1 lich su, so voi corrected_30
policy v2 hien hanh).

Thay the hoan toan cach cham/quyet dinh v1 cu (module lich su chuyen scoring
theo nguong trong so): ban cu tu goi rieng bon agent va tu quyet dinh, lech
khoi `decision_policy` v2. Wrapper nay KHONG tu goi agent nao - moi paid path
di qua `eval_policy_v2.cli()` (manifest/guard/confirmation-token chung); moi
bao cao di qua `eval_corrected_coverage.main()` (metric thuan, $0).

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe scripts\\eval_functional_clean.py --preflight ...
    .venv\\Scripts\\python.exe scripts\\eval_functional_clean.py --run ...
    .venv\\Scripts\\python.exe scripts\\eval_functional_clean.py --report ...
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import eval_corrected_coverage
import eval_policy_v2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument(
        "--report", action="store_true",
        help="chi tinh corrected_30 tu raw da co, KHONG goi LLM",
    )
    parser.add_argument("--manifest", help="can cho --preflight/--run")
    parser.add_argument("--output", required=True, help="corrected raw path")
    parser.add_argument("--assessment-as-of", help="can cho --preflight/--run")
    parser.add_argument("--confirmation-token", help="can cho --run")
    parser.add_argument("--gold-raw", help="can cho --report")
    parser.add_argument("--report-output", help="can cho --report")
    parser.add_argument(
        "--repo-root", default=str(Path(__file__).resolve().parents[2])
    )
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)

    if args.report:
        if not args.gold_raw or not args.report_output:
            print("[FAIL] --report can --gold-raw va --report-output")
            return 1
        return eval_corrected_coverage.main([
            "--report-corrected",
            "--gold-raw", args.gold_raw,
            "--corrected-raw", args.output,
            "--output", args.report_output,
        ])

    if not args.manifest or not args.assessment_as_of:
        print("[FAIL] --preflight/--run can --manifest va --assessment-as-of")
        return 1

    cli_argv = [
        "--dataset", "corrected",
        "--manifest", args.manifest,
        "--output", args.output,
        "--assessment-as-of", args.assessment_as_of,
        "--repo-root", args.repo_root,
    ]
    if args.preflight:
        cli_argv.append("--preflight")
    else:
        if not args.confirmation_token:
            print("[FAIL] --run can --confirmation-token")
            return 1
        cli_argv += ["--run", "--confirmation-token", args.confirmation_token]
    return eval_policy_v2.cli(cli_argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

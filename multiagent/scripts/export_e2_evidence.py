"""Chay hai nhanh E2 local va ghi evidence JSON atomically."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import eval_brand_retrieval
import eval_retrieval


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = REPO_ROOT / "docs" / "evidence" / "e2_retrieval_summary.json"


def _head_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip().casefold()
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise RuntimeError("git rev-parse HEAD khong tra SHA-1 40 ky tu")
    return commit


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_summary() -> dict:
    factcheck = eval_retrieval.evaluate()
    brand = eval_brand_retrieval.evaluate()
    return {
        "experiment": "E2",
        "run_at": _utc_now().isoformat(timespec="seconds").replace("+00:00", "Z"),
        "head_commit": _head_commit(),
        "factcheck": factcheck,
        "brand": brand,
        "passed": bool(factcheck.get("passed") and brand.get("passed")),
    }


def write_evidence(summary: dict, destination: Path = EVIDENCE_PATH) -> None:
    destination = Path(destination)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    if os.environ.get("HF_HUB_OFFLINE") != "1":
        print("Tu choi chay: phai dat HF_HUB_OFFLINE=1 de E2 khong tai model.")
        return 2
    summary = build_summary()
    write_evidence(summary)
    print(f"Da ghi {EVIDENCE_PATH}")
    print("DAT" if summary["passed"] else "CHUA DAT")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())

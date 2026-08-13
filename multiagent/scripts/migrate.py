"""CLI xem trang thai va apply SQL migration cua Multi-Agent platform."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform import database, migrations


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def _versions(values: tuple[int, ...] | list[int]) -> str:
    return ", ".join(f"{value:04d}" for value in values) or "none"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("status", "apply"), default="status")
    args = parser.parse_args(argv)

    try:
        with database.open_connection() as conn:
            if args.command == "apply":
                applied_now = migrations.apply_pending(conn, MIGRATIONS_DIR)
                print(f"applied now: {_versions(applied_now)}")
            current = migrations.status(conn, MIGRATIONS_DIR)
    except migrations.MigrationError as exc:
        print(f"migration error: {exc}", file=sys.stderr)
        return 2

    print(f"applied: {_versions(current.applied)}")
    print(f"pending: {_versions(current.pending)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

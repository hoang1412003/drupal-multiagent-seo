"""Migration SQL cua review platform co version va checksum bat bien."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re


_MIGRATION_FILENAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str


@dataclass(frozen=True)
class MigrationStatus:
    applied: tuple[int, ...]
    pending: tuple[int, ...]


class MigrationError(RuntimeError):
    pass


def discover(migrations_dir: Path) -> list[Migration]:
    """Doc migration SQL, xac minh ten/version va bam dung bytes tren disk."""
    root = Path(migrations_dir)
    found: list[Migration] = []
    seen_versions: set[int] = set()

    for path in sorted(root.glob("*.sql"), key=lambda item: item.name):
        match = _MIGRATION_FILENAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"ten migration khong hop le: {path.name}")

        version_text, name = match.groups()
        version = int(version_text)
        if version in seen_versions:
            raise MigrationError(f"trung version {version_text}: {path.name}")
        seen_versions.add(version)
        found.append(Migration(
            version=version,
            name=name,
            path=path,
            checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
        ))

    found.sort(key=lambda migration: migration.version)
    for expected, migration in enumerate(found, start=1):
        if migration.version != expected:
            raise MigrationError(f"thieu version {expected:04d}")
    return found


def _ensure_history_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_migration ("
            "  version integer PRIMARY KEY,"
            "  name text NOT NULL,"
            "  checksum char(64) NOT NULL,"
            "  applied_at timestamptz NOT NULL DEFAULT now()"
            ")"
        )


def _load_applied(conn) -> list[tuple[int, str, str]]:
    _ensure_history_table(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT version, name, checksum FROM schema_migration ORDER BY version"
        )
        return list(cur.fetchall())


def _validate_applied(
    found: list[Migration],
    applied_rows: list[tuple[int, str, str]],
) -> set[int]:
    by_version = {migration.version: migration for migration in found}
    applied_versions: set[int] = set()
    for version, applied_name, applied_checksum in applied_rows:
        migration = by_version.get(version)
        if migration is None:
            raise MigrationError(
                f"migration da apply nhung thieu file version {version:04d}"
            )
        if applied_name != migration.name:
            raise MigrationError(
                f"ten khong khop version {version:04d}: "
                f"database={applied_name}, file={migration.name}"
            )
        if applied_checksum != migration.checksum:
            raise MigrationError(f"checksum khong khop version {version:04d}")
        applied_versions.add(version)
    return applied_versions


def status(conn, migrations_dir: Path) -> MigrationStatus:
    """Tra version da apply/pending va chan lich su bi sua hoac mat file."""
    found = discover(migrations_dir)
    applied_rows = _load_applied(conn)
    applied_versions = _validate_applied(found, applied_rows)
    return MigrationStatus(
        applied=tuple(sorted(applied_versions)),
        pending=tuple(
            migration.version
            for migration in found
            if migration.version not in applied_versions
        ),
    )


def apply_pending(conn, migrations_dir: Path) -> list[int]:
    """Apply moi file pending trong mot transaction rieng cung history row."""
    found = discover(migrations_dir)
    applied_versions = _validate_applied(found, _load_applied(conn))
    applied_now: list[int] = []

    for migration in found:
        if migration.version in applied_versions:
            continue
        try:
            sql = migration.path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MigrationError(
                f"migration {migration.version:04d} khong phai UTF-8"
            ) from exc
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migration (version, name, checksum) "
                    "VALUES (%s, %s, %s)",
                    (migration.version, migration.name, migration.checksum),
                )
        applied_now.append(migration.version)
    return applied_now


def require_current(conn, migrations_dir: Path) -> None:
    """Chan startup khi schema con migration chua apply."""
    current = status(conn, migrations_dir)
    if current.pending:
        versions = ", ".join(f"{version:04d}" for version in current.pending)
        raise MigrationError(
            f"schema migration pending: {versions}; "
            "chay `python scripts/migrate.py apply`"
        )

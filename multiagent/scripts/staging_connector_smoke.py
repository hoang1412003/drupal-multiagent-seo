"""Smoke cutover: chay DUNG MOT job qua worker that, voi engine GIA.

Muc dich: chung minh duong ong Drupal -> API -> worker -> connector ->
result callback thong suot, MA KHONG goi LLM va khong tieu tien.

Vi sao khong dung engine that: mot lan smoke se ton ~$0,057 va - quan trong
hon - se tao ra mot ket qua cham diem THAT nam lan trong bao cao. Ket qua do
khong thuoc bo do nao, khong co nhan, nhung nhin thi khong phan biet duoc voi
ket qua that. Nen o day engine la gia va run duoc danh dau `is_fixture=true`
de moi metric production loai no ra.

Ba chot chan truoc khi chay, deu bat buoc:
1. Phai truyen dung `--confirm-staging-fixture`.
2. Base URL cua site phai la host staging (mac dinh `.ddev.site`).
3. Hang doi phai sach: dung mot job queued, khong co job running.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe scripts\\staging_connector_smoke.py \\
        --job-id <uuid> --confirm-staging-fixture
"""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import job_queue as q
import worker
from review_platform import database, migrations, sites


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

FIXTURE_NOTE = "STAGING FIXTURE - khong phai danh gia AI"
STAGING_HOST_SUFFIXES = (".ddev.site",)
FIXTURE_DECISION = "needs_revision"
FIXTURE_SCORE = 50.0


class SmokeError(RuntimeError):
    pass


def kiem_host_staging(base_url: str, *, hau_to=STAGING_HOST_SUFFIXES) -> str:
    """Tu choi chay tren host khong phai staging.

    Script nay GHI THAT vao Drupal (tao mot revision moi). Chay nham len
    production nghia la mot bai that mang bao cao gia.
    """
    host = (urlsplit(base_url).hostname or "").casefold()
    if not host:
        raise SmokeError(f"base URL khong co host: {base_url!r}")
    if not any(host == ten.lstrip(".") or host.endswith(ten) for ten in hau_to):
        raise SmokeError(
            f"host '{host}' khong nam trong allowlist staging {hau_to}; "
            "smoke fixture tuyet doi khong chay tren production"
        )
    return host


def kiem_hang_doi_sach(conn) -> None:
    """Hang doi phai chi co dung job dang smoke.

    Neu con job khac, `q.claim()` co the bat nham job cua nguoi khac va gan
    cho no mot ket qua GIA - dung thu tuyet doi khong duoc xay ra.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT status, count(*) FROM review_job "
            "WHERE status IN ('queued','running') GROUP BY status"
        )
        dem = dict(cur.fetchall())
    dang_chay = dem.get("running", 0)
    dang_cho = dem.get("queued", 0)
    if dang_chay:
        raise SmokeError(
            f"con {dang_chay} job dang chay; dung worker roi thu lai"
        )
    if dang_cho != 1:
        raise SmokeError(
            f"can dung 1 job queued, dang co {dang_cho}; "
            "lam sach hang doi truoc khi smoke"
        )


def engine_gia(state: dict) -> dict:
    """Ket qua gia, danh dau ro rang. KHONG goi LLM, khong nap model.

    Co y KHONG tra khoa `fields`: worker se dung fields cua tai lieu da fetch,
    nho vay hash trong run_log van la hash noi dung THAT chu khong phai hash
    cua mot dict rong.
    """
    return {
        "node_id": state["node_id"],
        "content_type": state.get("content_type"),
        "langcode": state.get("langcode"),
        "decision": FIXTURE_DECISION,
        "final_score": FIXTURE_SCORE,
        "report": {
            "node_id": state["node_id"],
            "decision": FIXTURE_DECISION,
            "final_score": FIXTURE_SCORE,
            "missing_agents": [],
            "note": FIXTURE_NOTE,
            "details": {},
            "fixture": True,
        },
    }


def chay(conn, *, job_id: str, connector_factory=None, invoke=None) -> dict:
    """Chay mot job smoke. Tra tom tat de ghi evidence."""
    try:
        mong_doi = UUID(str(job_id))
    except ValueError as exc:
        raise SmokeError(f"--job-id khong phai UUID: {job_id!r}") from exc

    site = sites.load_site_by_slug(conn, "drupal-vn-primary")
    host = kiem_host_staging(site.base_url)
    kiem_hang_doi_sach(conn)

    job = q.claim(conn, "staging-smoke")
    if job is None:
        raise SmokeError("khong claim duoc job nao")
    if job["public_id"] != mong_doi:
        # Da kiem hang doi chi co mot job, nen den day nghia la co ai do vua
        # xep them. Dung han thay vi cham nham bai.
        raise SmokeError(
            f"claim ra job {job['public_id']}, khong phai {mong_doi}"
        )

    ket = worker.chay_mot_job(
        conn,
        job,
        invoke=invoke or engine_gia,
        connector_factory=connector_factory,
        fixture_run=True,
    )

    with conn.cursor() as cur:
        cur.execute(
            "SELECT public_id, is_fixture, writeback_status, external_revision_id, "
            "content_hash_version, decision FROM run_log WHERE job_id=%s "
            "ORDER BY id DESC LIMIT 1",
            (job["id"],),
        )
        run = cur.fetchone()

    return {
        "host": host,
        "job_public_id": str(job["public_id"]),
        "job_status": ket,
        "external_content_id": job["external_content_id"],
        "content_hash_version": job.get("content_hash_version"),
        "run_public_id": None if run is None else str(run[0]),
        "run_is_fixture": None if run is None else run[1],
        "writeback_status": None if run is None else run[2],
        "run_revision_id": None if run is None else run[3],
        "run_decision": None if run is None else run[5],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke cutover mot job voi engine gia (khong goi LLM)"
    )
    parser.add_argument("--job-id", required=True)
    parser.add_argument(
        "--confirm-staging-fixture",
        action="store_true",
        help="Bat buoc. Xac nhan ban hieu day la ket qua GIA ghi vao Drupal.",
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.confirm_staging_fixture:
        print(
            "Loi: thieu --confirm-staging-fixture. Script nay ghi ket qua GIA "
            "vao Drupal that.",
            file=sys.stderr,
        )
        return 1
    try:
        with database.open_connection() as conn:
            migrations.require_current(conn, MIGRATIONS_DIR)
            tom_tat = chay(conn, job_id=args.job_id)
    except (SmokeError, sites.ContextSelectionError) as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 1

    for khoa, gia_tri in tom_tat.items():
        print(f"{khoa}: {gia_tri}")
    print(f"note: {FIXTURE_NOTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

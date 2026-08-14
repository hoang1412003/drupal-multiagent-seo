"""Heartbeat cua worker: nguon THAT de biet no con song hay khong.

Vi sao can bang rieng thay vi suy tu API: api.py va worker.py la HAI tien
trinh doc lap. Worker chet vi het RAM thi API van tra 200 va dashboard van
xanh - nguoi van hanh tuong he thong khoe trong khi khong bai nao duoc cham.

Ngu nghia thoi gian o day co y rat chat:
- co row, moi hon nguong  -> `running`     (dang chay)
- co row, cu hon nguong   -> `stale`       (qua han - nghi da chet)
- khong co row nao        -> `unavailable` (chua bao gio chay)

`stale` KHAC `unavailable`: mot worker vua chet khac han mot worker chua bao
gio duoc bat, va hai tinh huong do can hai phan ung khac nhau.

Moi ham nhan `now` tuong minh de test khong phu thuoc dong ho tuong.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID


STALE_AFTER = timedelta(seconds=30)
GIU_LAI = timedelta(days=7)


@dataclass(frozen=True)
class Heartbeat:
    instance_id: str
    started_at: datetime
    last_seen_at: datetime
    version: str
    current_job_id: UUID | None

    def trang_thai(self, *, now: datetime, stale_after: timedelta = STALE_AFTER) -> str:
        return "running" if now - self.last_seen_at < stale_after else "stale"


@dataclass(frozen=True)
class WorkerHealthView:
    status: str
    instances: tuple = field(default=())
    running_count: int = 0
    stale_count: int = 0
    last_seen_at: datetime | None = None


def beat(
    conn,
    *,
    instance_id: str,
    started_at: datetime,
    version: str,
    current_job_id=None,
    now: datetime | None = None,
) -> None:
    """Ghi nhip. `started_at` KHONG bao gio bi ghi de o lan beat sau.

    Giu nguyen started_at de biet worker da chay lien tuc bao lau; de no bi
    ghi de moi nhip thi uptime luon bang 0 va khong phat hien duoc worker
    dang restart lien tuc.
    """
    thoi_diem = now or datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO worker_heartbeat "
            "(instance_id, started_at, last_seen_at, version, current_job_id) "
            "VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (instance_id) DO UPDATE SET "
            "  last_seen_at=EXCLUDED.last_seen_at, "
            "  version=EXCLUDED.version, "
            "  current_job_id=EXCLUDED.current_job_id",
            (instance_id, started_at, thoi_diem, version, current_job_id),
        )


def forget(conn, *, instance_id: str) -> None:
    """Xoa nhip khi worker tat co trat tu, de dashboard khong bao stale oan."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM worker_heartbeat WHERE instance_id=%s", (instance_id,)
        )


def cleanup(conn, *, now: datetime, older_than: timedelta = GIU_LAI) -> int:
    """Don nhip cu hon 7 ngay. Chi xoa dung nhung row qua han do."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM worker_heartbeat WHERE last_seen_at < %s RETURNING instance_id",
            (now - older_than,),
        )
        return len(cur.fetchall())


def list_worker_health(
    conn, *, now: datetime, stale_after: timedelta = STALE_AFTER
) -> WorkerHealthView:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT instance_id, started_at, last_seen_at, version, current_job_id "
            "FROM worker_heartbeat ORDER BY last_seen_at DESC"
        )
        rows = cur.fetchall()

    instances = tuple(Heartbeat(*row) for row in rows)
    if not instances:
        return WorkerHealthView(status="unavailable")

    dang_chay = sum(
        1 for item in instances
        if item.trang_thai(now=now, stale_after=stale_after) == "running"
    )
    return WorkerHealthView(
        # Chi mot instance con song la du de goi la `running`; con lai la stale
        # va van hien so luong de nguoi van hanh thay co instance treo.
        status="running" if dang_chay else "stale",
        instances=instances,
        running_count=dang_chay,
        stale_count=len(instances) - dang_chay,
        last_seen_at=max(item.last_seen_at for item in instances),
    )

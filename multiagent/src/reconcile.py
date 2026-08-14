"""Vong doi soat: bat cac bai lot khi duong event that bai.

Spec: docs/superpowers/specs/2026-08-07-... muc 6.3

Day la LUOI AN TOAN, khong phai duong chinh. No khong can biet VI SAO mot bai
bi lot (service restart, Drupal mat mang, module bi tat, doi state bang drush)
- no chi so trang thai mong muon voi trang thai that roi bu chenh lech. Cung
nguyen ly reconciliation loop ma Kubernetes dung.

Chu ky 5 phut chu khong phai 30 giay: quet thua thi tiet kiem goi API vo ich,
va do tre xau nhat 5 phut chi xay ra trong tinh huong da hong.

Tu Plan 4, vong quet chay THEO SITE: moi site co connector, base URL va
credential rieng. Site tam dung intake khong duoc cham toi - neu van quet no,
"tam dung" chi con dung voi duong event con vong doi soat van bom job vao,
tuc nut tam dung khong con nghia gi.
"""
from dataclasses import dataclass, field
import logging

import job_queue as q
from review_platform import sites

logger = logging.getLogger(__name__)

MAX_ITEM_MOI_TRANG = 50
# Tran so trang cho MOT site trong mot luot: feed hong tra cursor lap lai se
# lam vong quet chay mai va giu connection den het chu ky.
MAX_TRANG_MOI_SITE = 100


@dataclass(frozen=True)
class ReconcileSummary:
    sites_scanned: int = 0
    enqueued: int = 0
    skipped_dead_letter: int = 0
    errors: tuple = field(default=())

    def __bool__(self) -> bool:
        return bool(self.enqueued)


def _sites_can_quet(conn):
    """Chi site dang bat VA khong tam dung intake."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM site WHERE active AND NOT intake_paused ORDER BY slug"
        )
        return [row[0] for row in cur.fetchall()]


def _quet_mot_site(conn, site_id, connector, enqueue_fn, co_that_bai) -> tuple:
    da_xep = 0
    bo_qua = 0
    moc = 0
    for _ in range(MAX_TRANG_MOI_SITE):
        page = connector.list_pending(
            after_revision_id=moc, limit=MAX_ITEM_MOI_TRANG
        )
        for item in page.items:
            try:
                context = sites.select_review_context(
                    conn, site_id, item.content_type, item.langcode
                )
            except sites.ContextSelectionError as exc:
                # Khong co profile khop thi KHONG duoc roi ve profile mac dinh:
                # cham bang policy cua scope khac la sai ket qua am tham.
                logger.warning(
                    "Doi soat bo qua %s: %s", item.external_content_id, exc
                )
                continue

            try:
                if co_that_bai(
                    conn,
                    site_id=site_id,
                    external_content_id=item.external_content_id,
                    content_hash=item.content_hash,
                    policy_version=context.profile.policy_version,
                ):
                    # TUYET DOI khong hoi sinh job da dead-letter (spec 6.3.1).
                    # Bai do chi chay lai duoc qua nut "Cham lai" thu cong, tuc
                    # phai co nguoi quyet dinh - dung tinh than "bam cham lai
                    # la tieu tien API that".
                    bo_qua += 1
                    continue

                ket_qua = enqueue_fn(
                    conn,
                    context,
                    item.external_content_id,
                    item.content_hash,
                    "reconcile",
                    external_revision_id=item.external_revision_id,
                    content_hash_version=item.content_hash_version,
                )
                if ket_qua and ket_qua.get("status") == q.QUEUED:
                    da_xep += 1
            except Exception as exc:
                # Mot item hong khong duoc giet ca luot quet cua site.
                logger.warning(
                    "Doi soat loi xu ly %s: %s", item.external_content_id, exc
                )

        if page.next_after_revision_id is None:
            break
        moc = page.next_after_revision_id
    return da_xep, bo_qua


def quet(
    conn,
    *,
    site_loader=None,
    connector_factory=None,
    enqueue_fn=None,
    co_that_bai=None,
) -> ReconcileSummary:
    """Quet mot vong tren moi site dang bat, tra tom tat da lam gi.

    Loi cua MOT site (Drupal tat, sai credential) khong duoc lam bo qua cac
    site sau: mot site hong se lam ca he thong ngung doi soat.
    """
    if site_loader is None:
        site_loader = _sites_can_quet
    if connector_factory is None:
        from review_platform.connectors.factory import connector_cho_site

        connector_factory = connector_cho_site
    if enqueue_fn is None:
        enqueue_fn = q.enqueue_scoped
    if co_that_bai is None:
        co_that_bai = q.co_job_that_bai_scoped

    tong_xep = 0
    tong_bo_qua = 0
    loi = []
    site_ids = list(site_loader(conn))

    for site_id in site_ids:
        try:
            connector = connector_factory(conn, site_id)
            da_xep, bo_qua = _quet_mot_site(
                conn, site_id, connector, enqueue_fn, co_that_bai
            )
            tong_xep += da_xep
            tong_bo_qua += bo_qua
        except Exception as exc:
            loi.append((str(site_id), exc.__class__.__name__))
            logger.warning("Doi soat loi o site %s: %s", site_id, exc)

    return ReconcileSummary(
        sites_scanned=len(site_ids),
        enqueued=tong_xep,
        skipped_dead_letter=tong_bo_qua,
        errors=tuple(loi),
    )

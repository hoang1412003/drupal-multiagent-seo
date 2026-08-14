"""Nap site va review profile theo scope tuong minh, khong fallback."""
from uuid import UUID

from review_platform.context import (
    ReviewContext,
    ReviewProfileContext,
    SiteContext,
)


class ContextSelectionError(RuntimeError):
    pass


def _site(row) -> SiteContext:
    return SiteContext(
        id=row[0],
        slug=row[1],
        connector_type=row[2],
        base_url=row[3],
        secret_ref=row[4],
        active=row[5],
        intake_paused=row[6],
    )


def load_site_by_slug(conn, slug: str) -> SiteContext:
    """Nap dung mot site theo slug, ke ca site dang inactive/paused."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, slug, connector_type, base_url, secret_ref, active, "
            "intake_paused FROM site WHERE slug=%s ORDER BY id LIMIT 2",
            (slug,),
        )
        rows = cur.fetchall()
    if not rows:
        raise ContextSelectionError(f"khong co site voi slug '{slug}'")
    if len(rows) > 1:
        raise ContextSelectionError(f"co nhieu site voi slug '{slug}'")
    return _site(rows[0])


def load_site_by_id(conn, site_id: UUID) -> SiteContext:
    """Nap site theo id de worker dung connector cua dung site so huu job."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, slug, connector_type, base_url, secret_ref, active, "
            "intake_paused FROM site WHERE id=%s",
            (site_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ContextSelectionError(f"khong co site voi id '{site_id}'")
    return _site(row)


def select_review_context(
    conn,
    site_id: UUID,
    content_type: str,
    langcode: str,
) -> ReviewContext:
    """Chon chinh xac mot profile active cho site/content type/ngon ngu."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT "
            "s.id, s.slug, s.connector_type, s.base_url, s.secret_ref, "
            "s.active, s.intake_paused, "
            "p.id, p.code, p.market_code, p.language_code, p.content_type, "
            "p.policy_version, p.policy_snapshot "
            "FROM site AS s "
            "JOIN site_profile_assignment AS assignment ON assignment.site_id=s.id "
            "JOIN review_profile AS p ON p.id=assignment.profile_id "
            "WHERE s.id=%s AND s.active AND assignment.active "
            "AND p.status='active' AND p.content_type=%s AND p.language_code=%s "
            "ORDER BY p.id LIMIT 2",
            (site_id, content_type, langcode),
        )
        rows = cur.fetchall()

    scope = f"site={site_id}, content_type={content_type}, langcode={langcode}"
    if not rows:
        raise ContextSelectionError(f"khong co profile active cho {scope}")
    if len(rows) > 1:
        raise ContextSelectionError(f"co nhieu profile active cho {scope}")

    row = rows[0]
    return ReviewContext(
        site=_site(row[:7]),
        profile=ReviewProfileContext(
            id=row[7],
            code=row[8],
            market_code=row[9],
            language_code=row[10],
            content_type=row[11],
            policy_version=row[12],
            policy_snapshot=dict(row[13]),
        ),
    )

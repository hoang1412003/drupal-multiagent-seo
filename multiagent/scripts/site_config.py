"""CLI cau hinh site theo moi truong: base URL doc tu env, secret chi la ten.

Seed migration 0001 dat `http://drupal.ddev.site` de bootstrap may dev. Do la
bootstrap, KHONG phai cau hinh dung duoc o staging/production: neu quen chay
lenh nay, connector cua staging se goi vao Drupal tren may lap trinh vien.

CLI nay chi luu TEN bien moi truong chua secret (`secret_ref`), khong bao gio
luu hay in gia tri user/password - database khong phai noi giu secret.
"""
import argparse
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from review_platform import database, migrations, sites


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
SECRET_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")


class SiteConfigError(RuntimeError):
    pass


def chuan_hoa_base_url(raw: str) -> str:
    """Kiem URL tuyet doi, khong userinfo/query/fragment, bo trailing slash."""
    if not raw or not raw.strip():
        raise SiteConfigError("base URL rong")

    value = raw.strip()
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https"):
        raise SiteConfigError(
            f"base URL phai co scheme http hoac https, nhan duoc: '{parts.scheme}'"
        )
    if not parts.hostname:
        raise SiteConfigError("base URL thieu host")
    if parts.username or parts.password or "@" in parts.netloc:
        raise SiteConfigError("base URL khong duoc chua userinfo")
    if parts.query:
        raise SiteConfigError("base URL khong duoc chua query")
    if parts.fragment:
        raise SiteConfigError("base URL khong duoc chua fragment")

    path = parts.path.rstrip("/")
    return f"{parts.scheme}://{parts.netloc}{path}"


def chuan_hoa_secret_ref(raw: str) -> str:
    """Chi nhan ten bien moi truong: prefix nay se dung de tra os.environ.

    Chan ky tu la o day de mot row database bi sua khong the bien thanh lenh
    tra bien moi truong tuy y o buoc resolve secret cua connector.
    """
    value = (raw or "").strip()
    if not SECRET_REF_PATTERN.fullmatch(value):
        raise SiteConfigError(
            "secret-ref phai dang A-Z, so va gach duoi, bat dau bang chu hoa, "
            f"toi da 64 ky tu; nhan duoc: '{raw}'"
        )
    return value


def _site(conn, slug: str):
    try:
        return sites.load_site_by_slug(conn, slug)
    except sites.ContextSelectionError as exc:
        raise SiteConfigError(str(exc)) from exc


def _set_from_env(conn, slug: str, base_url_env: str, secret_ref: str, environ, print_fn):
    raw_url = environ.get(base_url_env, "")
    if not raw_url:
        raise SiteConfigError(
            f"bien moi truong {base_url_env} chua dat hoac rong"
        )
    # Validate het truoc khi cham database: mot lenh sai khong duoc de site o
    # trang thai nua cu nua moi.
    base_url = chuan_hoa_base_url(raw_url)
    ten_secret = chuan_hoa_secret_ref(secret_ref)
    site = _site(conn, slug)

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE site SET base_url=%s, secret_ref=%s, updated_at=now() WHERE id=%s",
            (base_url, ten_secret, site.id),
        )
    print_fn(f"site {slug}: base_url={base_url} secret_ref={ten_secret}")
    return base_url


def _show(conn, slug: str, print_fn):
    site = _site(conn, slug)
    print_fn(f"slug          : {site.slug}")
    print_fn(f"base_url      : {site.base_url}")
    print_fn(f"secret_ref    : {site.secret_ref} (ten bien, khong phai gia tri)")
    print_fn(f"active        : {site.active}")
    print_fn(f"intake_paused : {site.intake_paused}")
    return site


def execute(conn, args, *, environ=None, print_fn=print):
    moi_truong = os.environ if environ is None else environ
    if args.command == "set-from-env":
        return _set_from_env(
            conn, args.site, args.base_url_env, args.secret_ref, moi_truong, print_fn
        )
    if args.command == "show":
        return _show(conn, args.site, print_fn)
    raise SiteConfigError(f"command khong duoc ho tro: {args.command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cau hinh site theo moi truong")
    commands = parser.add_subparsers(dest="command", required=True)

    set_from_env = commands.add_parser(
        "set-from-env",
        help="Dat base URL tu bien moi truong va ten bien chua secret",
    )
    set_from_env.add_argument("--site", required=True)
    set_from_env.add_argument("--base-url-env", required=True)
    set_from_env.add_argument("--secret-ref", required=True)

    show = commands.add_parser("show", help="In cau hinh site (khong in secret)")
    show.add_argument("--site", required=True)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with database.open_connection() as conn:
            migrations.require_current(conn, MIGRATIONS_DIR)
            execute(conn, args)
    except (SiteConfigError, migrations.MigrationError) as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

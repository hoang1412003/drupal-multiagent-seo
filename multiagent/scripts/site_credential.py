"""CLI quan ly API credential theo site: import, rotate, revoke, list.

Raw token khong bao gio nhan qua argument dong lenh - argv nam trong lich su
shell va trong bang tien trinh cua may. `import-env` doc tu bien moi truong,
`rotate` tu sinh; ca hai chi luu SHA-256.
"""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from review_platform import database, migrations, sites
from review_platform.api import auth


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


class CredentialCLIError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Quan ly API credential theo site")
    commands = parser.add_subparsers(dest="command", required=True)

    import_env = commands.add_parser(
        "import-env",
        help="Nap token dang dung tu bien moi truong (khong in raw)",
    )
    import_env.add_argument("--site", required=True)
    import_env.add_argument("--env", required=True)

    rotate = commands.add_parser("rotate", help="Sinh token moi va revoke token cu")
    rotate.add_argument("--site", required=True)

    revoke = commands.add_parser("revoke", help="Revoke mot credential theo id")
    revoke.add_argument("--credential", required=True)
    revoke.add_argument(
        "--allow-no-active",
        action="store_true",
        help="Cho phep site khong con credential active nao (luc disable site)",
    )

    listing = commands.add_parser("list", help="Liet ke prefix/trang thai/thoi gian")
    listing.add_argument("--site")
    return parser


def _site_id(conn, slug: str):
    try:
        return sites.load_site_by_slug(conn, slug).id
    except sites.ContextSelectionError as exc:
        raise CredentialCLIError(str(exc)) from exc


def _them_credential(conn, site_id, token: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO site_api_credential (site_id, token_prefix, token_hash) "
            "VALUES (%s, %s, %s) RETURNING id",
            (site_id, auth.token_prefix(token), auth.hash_token(token)),
        )
        return cur.fetchone()[0]


def _import_env(conn, slug: str, env_name: str, environ, print_fn):
    token = environ.get(env_name, "")
    if not token:
        raise CredentialCLIError(
            f"bien moi truong {env_name} chua dat hoac rong"
        )
    site_id = _site_id(conn, slug)
    token_hash = auth.hash_token(token)

    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, active FROM site_api_credential WHERE token_hash=%s",
            (token_hash,),
        )
        san_co = cur.fetchone()
    if san_co is not None:
        print_fn(f"Credential da ton tai: {san_co[0]} (active={san_co[1]})")
        return san_co[0]

    credential_id = _them_credential(conn, site_id, token)
    print_fn(f"Credential {credential_id}, prefix {auth.token_prefix(token)}")
    return credential_id


def _rotate(conn, slug: str, print_fn, token_fn):
    site_id = _site_id(conn, slug)
    token = token_fn()
    with conn.transaction():
        with conn.cursor() as cur:
            # Khoa row site de hai lan rotate song song khong cung tao active.
            cur.execute("SELECT id FROM site WHERE id=%s FOR UPDATE", (site_id,))
            cur.execute(
                "UPDATE site_api_credential SET active=false, revoked_at=now() "
                "WHERE site_id=%s AND active",
                (site_id,),
            )
        credential_id = _them_credential(conn, site_id, token)
    print_fn(f"Credential {credential_id}, prefix {auth.token_prefix(token)}")
    print_fn(f"Token moi, chi hien thi mot lan: {token}")
    return credential_id


def _revoke(conn, credential_id: str, allow_no_active: bool, print_fn):
    with conn.cursor() as cur:
        try:
            cur.execute(
                "SELECT site_id, active FROM site_api_credential WHERE id=%s",
                (credential_id,),
            )
        except Exception as exc:
            raise CredentialCLIError(f"credential id khong hop le: {exc}") from exc
        row = cur.fetchone()
    if row is None:
        raise CredentialCLIError(f"khong tim thay credential {credential_id}")

    site_id, dang_active = row
    if dang_active and not allow_no_active:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM site_api_credential "
                "WHERE site_id=%s AND active AND id<>%s",
                (site_id, credential_id),
            )
            con_lai = cur.fetchone()[0]
        if con_lai == 0:
            raise CredentialCLIError(
                "day la credential active cuoi cung cua site; rotate truoc, "
                "hoac truyen --allow-no-active neu that su muon dung site"
            )

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE site_api_credential SET active=false, revoked_at=now() "
            "WHERE id=%s AND active",
            (credential_id,),
        )
    print_fn(f"Da revoke credential {credential_id}")
    return credential_id


def _list(conn, slug, print_fn):
    query = (
        "SELECT c.id, c.token_prefix, c.active, c.created_at, c.last_used_at, "
        "c.revoked_at, s.slug FROM site_api_credential AS c "
        "JOIN site AS s ON s.id=c.site_id"
    )
    params = ()
    if slug is not None:
        query += " WHERE s.slug=%s"
        params = (slug,)
    query += " ORDER BY c.created_at"

    with conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    for row in rows:
        trang_thai = "active" if row[2] else "revoked"
        print_fn(
            f"{row[6]} {row[1]} {trang_thai} tao={row[3]:%Y-%m-%d %H:%M} "
            f"dung_cuoi={row[4]} revoke={row[5]}"
        )
    return rows


def execute(conn, args, *, environ=None, print_fn=print, token_fn=auth.generate_token):
    moi_truong = os.environ if environ is None else environ
    if args.command == "import-env":
        return _import_env(conn, args.site, args.env, moi_truong, print_fn)
    if args.command == "rotate":
        return _rotate(conn, args.site, print_fn, token_fn)
    if args.command == "revoke":
        return _revoke(conn, args.credential, args.allow_no_active, print_fn)
    if args.command == "list":
        return _list(conn, args.site, print_fn)
    raise CredentialCLIError(f"command khong duoc ho tro: {args.command}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with database.open_connection() as conn:
            migrations.require_current(conn, MIGRATIONS_DIR)
            execute(conn, args)
    except (CredentialCLIError, migrations.MigrationError) as exc:
        print(f"Loi: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

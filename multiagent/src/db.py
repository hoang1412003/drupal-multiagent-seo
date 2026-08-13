"""Ket noi Postgres + pgvector cho kho vector (KB brand va KB fact-check).

Thay cho Chroma tu 2026-08-05. Ly do doi KHONG phai vi Chroma cham - o quy mo
1.132 chunk moi thu deu nhanh - ma vi phia Multi-Agent tro thanh mot service
rieng, va service rieng thi con phai giu lich su cham + trang thai cham (du
lieu QUAN HE), chu khong chi giu vector. Mot Postgres phuc vu ca hai; mot
vector DB thuan thi phai dung them DB thu hai.

Loi keo theo, do duoc: o 1.132 dong Postgres quet toan bo trong vai mili giay
nen KHONG can index - tuc tim kiem CHINH XAC TUYET DOI, khong con xap xi ANN
nhu HNSW cua Chroma.
"""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

# Khop docker-compose.yml. De mac dinh chay duoc ngay sau `docker compose up`
# ma khong phai cau hinh gi - dung tinh than voi DRUPAL_BASE_URL trong
# drupal_client.py.
DSN_MAC_DINH = "postgresql://vf_agent:vf_agent@127.0.0.1:5433/vf_agent"

TEN_BANG = "kb_chunk"

# Cache khoa theo DSN, KHONG phai mot bien toan cuc duy nhat. Day dung la bai
# hoc no B11: ban cu cua config._nap_file va retrieval._get_collection giu mot
# doi tuong duy nhat roi bo qua tham so duong dan, nen lan goi thu hai voi
# duong dan khac van tra ve du lieu cu - tham so hua mot dang, ham lam mot neo.
_conns: dict = {}


def dsn() -> str:
    """DSN dang dung. Doc tu PG_DSN neu co, khong thi dung mac dinh local."""
    return os.environ.get("PG_DSN") or DSN_MAC_DINH


def get_conn(dsn_str: "str | None" = None):
    """Ket noi dung chung cho mot DSN. Tu mo lai neu ket noi da dong."""
    d = dsn_str or dsn()
    conn = _conns.get(d)
    if conn is None or conn.closed:
        _conns[d] = psycopg.connect(d, autocommit=True)
    return _conns[d]


def _chieu_cua_bang(conn) -> "int | None":
    """So chieu vector cua bang hien co. None neu bang chua ton tai.

    pgvector luu so chieu ngay trong `atttypmod` cua cot.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT a.atttypmod FROM pg_attribute a "
            "WHERE a.attrelid = to_regclass(%s) AND a.attname = 'embedding'",
            (TEN_BANG,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def dam_bao_bang(conn, dim: int) -> None:
    """Validate bang KB da migrate va dimension; chi bo sung index loc KB.

    Ghim so chieu vao kieu cot (`vector(1024)`) chu khong de `vector` tran:
    doi model embedding la phai nhung lai toan bo KB (docs/rag-design.md muc
    4.2), va neu cot khong ghim chieu thi hai model tron lan nhau trong cung
    mot bang MA KHONG CO DAU HIEU GI. Ghim vao thi Postgres tu chan, va thong
    bao duoi day noi ro phai lam gi - dung chu truong "khong de bay im lang"
    cua du an.
    """
    hien_co = _chieu_cua_bang(conn)
    if hien_co is None:
        raise RuntimeError(
            f"Bang {TEN_BANG} chua ton tai; chay `python scripts/migrate.py apply` "
            "truoc khi build KB."
        )
    if hien_co != dim:
        raise ValueError(
            f"Bang {TEN_BANG} dang ghim vector {hien_co} chieu, embedder hien "
            f"tai sinh {dim} chieu. Doi model embedding thi phai dung lai KB tu "
            f"dau: xoa bang (DROP TABLE {TEN_BANG}) roi chay lai src/kb/"
            f"build_kb.py va src/kb/build_brand_kb.py."
        )
    with conn.cursor() as cur:
        # CO Y khong tao index vector (HNSW/IVFFlat). O 1.132 dong, quet toan bo
        # nhanh hon ca dung index, va quan trong hon: ket qua la lang gieng gan
        # nhat CHINH XAC, khong phai xap xi. Chi tao index khi KB vuot ~100.000
        # chunk - nguong ghi o docs/rag-design.md.
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {TEN_BANG}_loc_idx "
            f"ON {TEN_BANG} (collection, content_type, langcode)"
        )


def vector_literal(vec) -> str:
    """List float -> chuoi '[1,2,3]' de Postgres ep sang kieu vector.

    Tu ghep chuoi thay vi cai them goi `pgvector` cho Python: chi can dung mot
    dinh dang duy nhat, them mot phu thuoc de lam viec nay la khong dang.
    """
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"

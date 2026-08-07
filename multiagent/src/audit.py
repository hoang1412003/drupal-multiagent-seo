"""Nhat ky truy vet: mot ban ghi append-only cho moi lan cham.

Thiet ke: docs/operations.md muc 2 (ghi cai gi, khong ghi cai gi).
Cho luu: Postgres thay vi JSONL - ly do doi ket luan o spec 2026-08-07 muc 2.1
(tien de da doi: luc operations.md viet thi phia Multi-Agent chua co CSDL nao).

Tra loi duoc cau "bai nay bi chan hoi thang truoc, vi sao" - Drupal giu duoc
DIEM BAO NHIEU qua revision, nhung khong giu BOI CANH sinh ra no.
"""
import json

TEN_BANG = "run_log"


def dam_bao_bang(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {TEN_BANG} ("
            "  id             bigserial PRIMARY KEY,"
            "  job_id         bigint,"
            "  node_id        text        NOT NULL,"
            "  content_hash   text        NOT NULL,"
            "  scored_at      timestamptz NOT NULL DEFAULT now(),"
            "  duration_ms    int,"
            "  decision       text,"
            "  final_score    numeric,"
            "  missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb,"
            "  veto_reason    text,"
            "  note           text,"
            "  agent_results  jsonb NOT NULL,"
            "  config_meta    jsonb NOT NULL,"
            "  usage          jsonb NOT NULL,"
            "  model          text  NOT NULL,"
            "  payload        jsonb NOT NULL"
            ")"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {TEN_BANG}_tra_cuu "
            f"ON {TEN_BANG} (node_id, content_hash)"
        )


def _js(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)


def ghi(conn, *, job_id, node_id: str, content_hash: str, duration_ms: int,
        report: dict, config_meta: dict, usage: list, model: str,
        payload: dict) -> int:
    """Ghi mot ban ghi. CHI INSERT - khong bao gio UPDATE hay DELETE.

    `final_score = None` duoc giu nguyen NULL, KHONG quy ve 0: None nghia la
    CHUA cham duoc (Compliance loi), khac han voi 0 diem.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} "
            "(job_id, node_id, content_hash, duration_ms, decision, final_score,"
            " missing_agents, veto_reason, note, agent_results, config_meta,"
            " usage, model, payload) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb,"
            "        %s::jsonb,%s,%s::jsonb) RETURNING id",
            (
                job_id, node_id, content_hash, duration_ms,
                report.get("decision"), report.get("final_score"),
                _js(report.get("missing_agents") or []),
                report.get("veto_reason"), report.get("note"),
                _js(report.get("details") or {}),
                _js(config_meta), _js(usage), model, _js(payload),
            ),
        )
        return cur.fetchone()[0]


def da_cham(conn, node_id: str, content_hash: str):
    """Da co ket qua cho dung cap (node_id, content_hash) chua?

    Worker hoi cau nay TRUOC khi goi LLM. Co roi -> chi ghi lai `payload` cu
    sang Drupal, khong chay lai pipeline. Day la cho chan duong mat tien khi
    write_back that bai: cham lai mot bai ton $0,057 that.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, payload FROM {TEN_BANG} "
            f"WHERE node_id=%s AND content_hash=%s ORDER BY scored_at DESC LIMIT 1",
            (node_id, content_hash),
        )
        row = cur.fetchone()
    return None if row is None else {"id": row[0], "payload": row[1]}

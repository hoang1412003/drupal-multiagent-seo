"""Gan nhan token theo tung agent MA KHONG sua mot dong nao cua agent.

Cach lam: moi module agent lam `from ai_core import call_agent`, tao mot
BINDING rieng trong namespace cua no. Thay binding do bang mot wrapper la du
de biet lan goi nay thuoc agent nao - va `git diff` tren file agent van rong,
tuc bo khoa score-path cho E1/E5 khong bi dong.

Vi sao khong truyen tham so xuong agent: lam vay phai sua chu ky ham cua ca
bon agent, tuc sua dung duong dang bi khoa. Wrapper la cach duy nhat vua co
attribution vua giu diff rong.

Vi sao ContextVar chu khong phai bien module: LangGraph chay bon agent SONG
SONG trong executor thread. Bien module se lam agent nay ghi nhan token cua
agent kia. Wrapper set/reset ContextVar ngay TRONG chinh thread goi, nen
khong phu thuoc parent context co tu truyen qua thread hay khong.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import logging
import threading


logger = logging.getLogger(__name__)

# Nhan cha cua tung module agent. `brand_voice` bao cao duoi nhan `brand` cho
# khop voi report/scoring hien hanh.
NHAN_MODULE = {
    "content_quality": ("content_quality", "main"),
    "seo": ("seo", "main"),
    "brand_voice": ("brand", "main"),
    "compliance": ("compliance", "main"),
}
MODULE_FACT_CHECK = "fact_check"
KHOA_ENTRY = ("agent", "phase", "model", "input_tokens", "output_tokens")

_ngu_canh: ContextVar[tuple] = ContextVar("usage_agent", default=("unknown", "unknown"))


class UsageScopeError(RuntimeError):
    pass


def _bam(prompt) -> str:
    return hashlib.sha256(str(prompt).encode("utf-8")).hexdigest()


class UsageCollector:
    """Thay cho `ai_core.USAGE_LOG`, tuong thich list nhung co gan nhan.

    Chi mot job duoc active tai mot thoi diem - worker MVP xu ly tuan tu, va
    cho phep hai scope long nhau se lam entry lan job.
    """

    def __init__(self, sink=None):
        self._entries = []
        self._lock = threading.Lock()
        self._sink = sink
        self._job_public_id = None
        self._job_db_id = None
        self._correlation_id = None
        self._attempt = 1
        self._is_fixture = False
        self._dang_mo = False
        self._sequence = 0

    # ---- giao dien giong list, de code cu khong phai doi -----------------

    def append(self, entry) -> None:
        agent, phase = _ngu_canh.get()
        day_du = {
            "agent": agent,
            "phase": phase,
            "model": entry.get("model"),
            "input_tokens": entry.get("input_tokens"),
            "output_tokens": entry.get("output_tokens"),
        }
        with self._lock:
            self._sequence += 1
            thu_tu = self._sequence
            self._entries.append(day_du)
            job_db_id = self._job_db_id
            correlation_id = self._correlation_id
            attempt = self._attempt
            is_fixture = self._is_fixture

        if self._sink is None or job_db_id is None:
            return
        # Ghi NGAY, khong doi het job: agent co the nem loi ngay sau lan goi
        # nay va khong bao gio co run_log - tien da tieu van phai vao so.
        self._sink(
            job_id=job_db_id,
            attempt=attempt,
            sequence_no=thu_tu,
            correlation_id=correlation_id,
            is_fixture=is_fixture,
            entry=day_du,
        )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __iter__(self):
        return iter(list(self._entries))

    def __len__(self) -> int:
        return len(self._entries)

    def __bool__(self) -> bool:
        return bool(self._entries)

    def __getitem__(self, index):
        return self._entries[index]

    def __eq__(self, other):
        if isinstance(other, list):
            return list(self._entries) == other
        return NotImplemented

    def __repr__(self) -> str:
        return f"UsageCollector({self._entries!r})"

    # ---- vong doi scope --------------------------------------------------

    def begin(self, *, job_public_id, job_db_id, correlation_id, attempt,
              is_fixture=False) -> None:
        with self._lock:
            if self._dang_mo:
                raise UsageScopeError(
                    f"da co scope dang mo cho job {self._job_public_id}"
                )
            if self._entries:
                raise UsageScopeError(
                    "collector con entry cua luot truoc; phai clear() truoc khi mo"
                )
            self._dang_mo = True
            self._job_public_id = job_public_id
            self._job_db_id = job_db_id
            self._correlation_id = correlation_id
            self._attempt = attempt
            self._is_fixture = is_fixture
            self._sequence = 0

    def end(self) -> list:
        with self._lock:
            ban_sao = list(self._entries)
            self._dang_mo = False
            self._job_public_id = None
            self._job_db_id = None
            self._correlation_id = None
            self._entries.clear()
            self._sequence = 0
        return ban_sao


@contextmanager
def usage_scope(collector, *, job_public_id, job_db_id, correlation_id,
                attempt=1, is_fixture=False):
    collector.begin(
        job_public_id=job_public_id,
        job_db_id=job_db_id,
        correlation_id=correlation_id,
        attempt=attempt,
        is_fixture=is_fixture,
    )
    try:
        yield collector
    finally:
        collector.end()


def _wrapper(goc, nhan_co_dinh=None, ban_do_prompt=None):
    """Bao `call_agent` giu NGUYEN chu ky, gia tri tra ve va ngoai le."""

    def call_agent(system_prompt, content, output_schema):
        if nhan_co_dinh is not None:
            nhan = nhan_co_dinh
        else:
            nhan = (ban_do_prompt or {}).get(_bam(system_prompt))
            if nhan is None:
                # KHONG doan. Ghi `unknown` va canh bao - doan sai se gan chi
                # phi cho nham agent, va con so sai thi te hon con so thieu.
                logger.warning(
                    "usage: khong nhan ra prompt cua fact_check, ghi phase unknown"
                )
                nhan = ("compliance", "unknown")
        token = _ngu_canh.set(nhan)
        try:
            return goc(system_prompt, content, output_schema)
        finally:
            _ngu_canh.reset(token)

    call_agent.__wrapped__ = goc
    return call_agent


_da_cai = False


def install_worker_usage_instrumentation(*, sink=None, force=False):
    """Cai wrapper vao 5 module agent. Idempotent.

    Tra ve UsageCollector da duoc gan vao `ai_core.USAGE_LOG`.
    """
    global _da_cai
    import ai_core
    from agents import brand_voice, compliance, content_quality, fact_check, seo

    modules = {
        "content_quality": content_quality,
        "seo": seo,
        "brand_voice": brand_voice,
        "compliance": compliance,
    }

    if _da_cai and not force:
        return ai_core.USAGE_LOG

    for ten, module in modules.items():
        goc = getattr(module.call_agent, "__wrapped__", module.call_agent)
        module.call_agent = _wrapper(goc, nhan_co_dinh=NHAN_MODULE[ten])

    # fact_check dung CUNG mot ham cho hai pha, nen phai phan biet bang chinh
    # noi dung system prompt tai thoi diem cai dat.
    ban_do = {
        _bam(fact_check._EXTRACT_PROMPT): ("compliance", "fact_check_extract"),
        _bam(fact_check._COMPARE_PROMPT): ("compliance", "fact_check_compare"),
    }
    goc_fact = getattr(fact_check.call_agent, "__wrapped__", fact_check.call_agent)
    fact_check.call_agent = _wrapper(goc_fact, ban_do_prompt=ban_do)

    collector = UsageCollector(sink=sink)
    ai_core.USAGE_LOG = collector
    _da_cai = True
    return collector


def record_usage_event(conn_factory, *, job_id, attempt, sequence_no,
                       correlation_id, is_fixture, entry) -> None:
    """Ghi mot event. Idempotent theo (job_id, attempt, sequence_no).

    Dung connection RIENG tu factory: ham nay duoc goi tu executor thread cua
    LangGraph, con connection cua worker dang do chinh worker dung.
    """
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO llm_usage_event "
                "(job_id, attempt, sequence_no, correlation_id, agent, phase, "
                " model, input_tokens, output_tokens, is_fixture) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                "ON CONFLICT (job_id, attempt, sequence_no) DO NOTHING",
                (
                    job_id,
                    attempt,
                    sequence_no,
                    correlation_id,
                    entry.get("agent"),
                    entry.get("phase"),
                    entry.get("model"),
                    entry.get("input_tokens") or 0,
                    entry.get("output_tokens") or 0,
                    is_fixture,
                ),
            )

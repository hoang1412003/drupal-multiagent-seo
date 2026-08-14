"""Test gan nhan usage theo agent MA KHONG doi hanh vi agent (Plan 5 Task 3).

Hai dieu phai chung minh, va dieu thu hai quan trong hon:
1. Nhan agent/phase dung, khong lan giua cac thread chay song song.
2. Wrapper KHONG doi gia tri tra ve, ngoai le hay tham so cua call_agent -
   neu doi thi duong cham diem da khac va E1/E5 do sau nay se do mot he
   thong khac voi he thong da thiet ke.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_usage.py
"""
from concurrent.futures import ThreadPoolExecutor
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform import usage as platform_usage
from review_platform.usage import (
    UsageCollector,
    UsageScopeError,
    install_worker_usage_instrumentation,
    usage_scope,
)


def _entry(model="m", vao=10, ra=5):
    return {"model": model, "input_tokens": vao, "output_tokens": ra}


def test_collector_tuong_thich_list():
    """Code cu goi .clear(), lap, list() - tat ca phai con chay."""
    collector = UsageCollector()
    assert len(collector) == 0 and not collector
    collector.append(_entry())
    assert len(collector) == 1 and collector
    assert list(collector)[0]["model"] == "m"
    assert collector[0]["input_tokens"] == 10
    collector.clear()
    assert list(collector) == [] and len(collector) == 0
    print("[PASS] UsageCollector dung duoc y het list cu")


def test_entry_chi_co_dung_nam_khoa():
    collector = UsageCollector()
    collector.append({"model": "m", "input_tokens": 1, "output_tokens": 2, "thua": "x"})
    assert set(collector[0]) == set(platform_usage.KHOA_ENTRY), collector[0]
    # Khong bao gio luu prompt/output/noi dung.
    assert "thua" not in collector[0]
    print("[PASS] entry chi giu dung nam khoa, khoa la bi loai")


def test_chi_mot_scope_duoc_mo_mot_luc():
    collector = UsageCollector()
    with usage_scope(collector, job_public_id="j1", job_db_id=1,
                     correlation_id="c1"):
        try:
            collector.begin(job_public_id="j2", job_db_id=2, correlation_id="c2",
                            attempt=1)
        except UsageScopeError:
            pass
        else:
            raise AssertionError("phai chan scope thu hai")
    # Ra khoi scope thi mo lai duoc.
    with usage_scope(collector, job_public_id="j2", job_db_id=2,
                     correlation_id="c2"):
        collector.append(_entry())
    print("[PASS] chi mot job active mot luc; ra scope thi mo lai duoc")


def test_scope_dong_thi_clear_de_job_sau_khong_ke_thua():
    collector = UsageCollector()
    with usage_scope(collector, job_public_id="j1", job_db_id=1, correlation_id="c"):
        collector.append(_entry())
        assert len(collector) == 1
    assert len(collector) == 0, "entry cua job truoc phai duoc don"

    with usage_scope(collector, job_public_id="j2", job_db_id=2, correlation_id="c"):
        assert len(collector) == 0
    print("[PASS] dong scope thi clear, job sau khong ke thua entry job truoc")


def test_ghi_sink_ngay_ke_ca_khi_sau_do_agent_loi():
    ghi = []
    collector = UsageCollector(sink=lambda **kw: ghi.append(kw))

    try:
        with usage_scope(collector, job_public_id="j", job_db_id=7,
                         correlation_id="corr", attempt=2):
            collector.append(_entry(vao=100))
            raise RuntimeError("agent no ngay sau khi tieu tien")
    except RuntimeError:
        pass

    assert len(ghi) == 1, ghi
    assert ghi[0]["job_id"] == 7 and ghi[0]["attempt"] == 2
    assert ghi[0]["sequence_no"] == 1
    assert ghi[0]["entry"]["input_tokens"] == 100
    print("[PASS] usage duoc ghi NGAY, khong mat du agent no sau do")


def test_sequence_tang_dan_va_khong_lan_giua_thread():
    ghi = []
    collector = UsageCollector(sink=lambda **kw: ghi.append(kw))
    goc = platform_usage._ngu_canh

    def chay(nhan):
        token = goc.set(nhan)
        try:
            collector.append(_entry())
        finally:
            goc.reset(token)

    with usage_scope(collector, job_public_id="j", job_db_id=1, correlation_id="c"):
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(chay, [
                ("seo", "main"), ("brand", "main"),
                ("compliance", "main"), ("content_quality", "main"),
            ]))

    assert sorted(item["sequence_no"] for item in ghi) == [1, 2, 3, 4], ghi
    nhan = {item["entry"]["agent"] for item in ghi}
    assert nhan == {"seo", "brand", "compliance", "content_quality"}, nhan
    print("[PASS] bon thread song song: sequence khong trung, nhan khong lan")


def test_wrapper_giu_nguyen_tra_ve_ngoai_le_va_tham_so():
    """Diem quan trong nhat: wrapper KHONG duoc doi hanh vi cua call_agent."""
    nhan_duoc = []

    def call_agent_goc(system_prompt, content, output_schema):
        nhan_duoc.append((system_prompt, content, output_schema))
        if content == "no":
            raise ValueError("loi goc")
        return {"ket_qua": 42}

    boc = platform_usage._wrapper(call_agent_goc, nhan_co_dinh=("seo", "main"))

    prompt, noi_dung, schema = "P", "C", {"type": "object"}
    assert boc(prompt, noi_dung, schema) == {"ket_qua": 42}
    # Tham so phai la CHINH object do, khong phai ban sao.
    assert nhan_duoc[0][0] is prompt
    assert nhan_duoc[0][1] is noi_dung
    assert nhan_duoc[0][2] is schema

    try:
        boc("P", "no", schema)
    except ValueError as exc:
        assert str(exc) == "loi goc", exc
    else:
        raise AssertionError("ngoai le goc phai di nguyen ra ngoai")

    # ContextVar phai duoc reset ke ca khi nem loi.
    assert platform_usage._ngu_canh.get() == ("unknown", "unknown")
    print("[PASS] wrapper giu nguyen tra ve, ngoai le va identity cua tham so")


def test_cai_dat_gan_dung_nam_binding_va_sau_nhan():
    import ai_core
    from agents import brand_voice, compliance, content_quality, fact_check, seo

    goc = {
        "content_quality": content_quality.call_agent,
        "seo": seo.call_agent,
        "brand_voice": brand_voice.call_agent,
        "compliance": compliance.call_agent,
        "fact_check": fact_check.call_agent,
    }
    goc_usage_log = ai_core.USAGE_LOG
    try:
        collector = install_worker_usage_instrumentation(force=True)
        assert ai_core.USAGE_LOG is collector

        for module in (content_quality, seo, brand_voice, compliance, fact_check):
            assert hasattr(module.call_agent, "__wrapped__"), module.__name__

        # Cai lai lan hai KHONG duoc boc chong len nhau.
        lai = install_worker_usage_instrumentation(force=True)
        assert seo.call_agent.__wrapped__ is not seo.call_agent
        assert not hasattr(seo.call_agent.__wrapped__, "__wrapped__"), (
            "boc chong: wrapper cu bi boc lan hai"
        )

        # Sau nhan: bon agent + hai pha cua fact_check.
        #
        # Phai boc lai bang `_wrapper` voi ham GIA. Gan `__wrapped__` khong co
        # tac dung: wrapper dong (closure) qua bien `goc` chu khong tra thuoc
        # tinh do luc chay - va call_agent that se doi ANTHROPIC_API_KEY.
        ghi = []
        lai._sink = lambda **kw: ghi.append(kw["entry"])

        def _gia(p, c, s):
            ai_core.USAGE_LOG.append(_entry())
            return {"x": 1}

        for ten, module in (
            ("content_quality", content_quality), ("seo", seo),
            ("brand_voice", brand_voice), ("compliance", compliance),
        ):
            module.call_agent = platform_usage._wrapper(
                _gia, nhan_co_dinh=platform_usage.NHAN_MODULE[ten]
            )
        fact_check.call_agent = platform_usage._wrapper(_gia, ban_do_prompt={
            platform_usage._bam(fact_check._EXTRACT_PROMPT):
                ("compliance", "fact_check_extract"),
            platform_usage._bam(fact_check._COMPARE_PROMPT):
                ("compliance", "fact_check_compare"),
        })

        with usage_scope(lai, job_public_id="j", job_db_id=1, correlation_id="c"):
            content_quality.call_agent("p", "c", {})
            seo.call_agent("p", "c", {})
            brand_voice.call_agent("p", "c", {})
            compliance.call_agent("p", "c", {})
            fact_check.call_agent(fact_check._EXTRACT_PROMPT, "c", {})
            fact_check.call_agent(fact_check._COMPARE_PROMPT, "c", {})

        nhan = [(item["agent"], item["phase"]) for item in ghi]
        assert nhan == [
            ("content_quality", "main"),
            ("seo", "main"),
            ("brand", "main"),
            ("compliance", "main"),
            ("compliance", "fact_check_extract"),
            ("compliance", "fact_check_compare"),
        ], nhan
    finally:
        for ten, ham in goc.items():
            module = {
                "content_quality": content_quality, "seo": seo,
                "brand_voice": brand_voice, "compliance": compliance,
                "fact_check": fact_check,
            }[ten]
            module.call_agent = ham
        ai_core.USAGE_LOG = goc_usage_log
        platform_usage._da_cai = False
    print("[PASS] cai dat gan dung 5 binding, sinh 6 nhan, khong boc chong")


def test_prompt_la_thi_ghi_unknown_chu_khong_doan():
    ban_do = {platform_usage._bam("A"): ("compliance", "fact_check_extract")}
    thay = []

    # Doc nhan tu BEN TRONG lan goi: ContextVar.set la read-only, khong
    # monkeypatch duoc, va doc tu trong cung dung hon - do la noi entry that
    # su lay nhan.
    def _doc_nhan(p, c, s):
        thay.append(platform_usage._ngu_canh.get())
        return None

    boc = platform_usage._wrapper(_doc_nhan, ban_do_prompt=ban_do)
    boc("A", "c", {})
    boc("PROMPT LA", "c", {})

    assert thay[0] == ("compliance", "fact_check_extract"), thay
    assert thay[1] == ("compliance", "unknown"), thay
    print("[PASS] prompt la -> ghi unknown kem canh bao, tuyet doi khong doan")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_collector_tuong_thich_list,
        test_entry_chi_co_dung_nam_khoa,
        test_chi_mot_scope_duoc_mo_mot_luc,
        test_scope_dong_thi_clear_de_job_sau_khong_ke_thua,
        test_ghi_sink_ngay_ke_ca_khi_sau_do_agent_loi,
        test_sequence_tang_dan_va_khong_lan_giua_thread,
        test_wrapper_giu_nguyen_tra_ve_ngoai_le_va_tham_so,
        test_cai_dat_gan_dung_nam_binding_va_sau_nhan,
        test_prompt_la_thi_ghi_unknown_chu_khong_doan,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)

r"""Behavior tests cho publish decision policy v2 thuần.

Chạy từ ``multiagent``::

    .venv\Scripts\python.exe scripts\test_decision_policy.py

Expected values đều là literal theo design spec, không tính lại bằng helper
của production module.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from decision_policy import (  # noqa: E402
    POLICY_V1,
    POLICY_V2,
    PolicyContractError,
    evaluate,
    require_policy_version,
)


EXCERPT = "Đọc hướng dẫn trước khi sử dụng."


def criterion(
    criterion_id: str,
    level: int | None,
    *,
    field: str = "body",
    text: str = EXCERPT,
) -> dict:
    return {
        "id": criterion_id,
        "level": level,
        "occurrences": (
            [{"field": field, "text": text}] if level in {0, 1} else []
        ),
        "suggestion": "Sửa nội dung có vấn đề.",
    }


def clean_fields() -> dict:
    return {
        "title": "Hướng dẫn sử dụng xe điện VinFast an toàn mỗi ngày",
        "meta_description": "m" * 150,
        "url_alias": "huong-dan-su-dung-xe-dien-vinfast-an-toan-moi-ngay",
        "summary": "Tóm tắt hướng dẫn sử dụng xe điện.",
        "body": f"<h2>Chuẩn bị</h2><p>{EXCERPT}</p>",
        "image_alt": "Người dùng đọc hướng dẫn xe điện",
    }


def base_results() -> dict:
    return {
        "content_quality": {
            "score": 100.0,
            "criteria": [
                criterion(code, 2)
                for code in ("CQ1", "CQ2", "CQ3", "CQ4", "CQ5", "CQ6", "CQ7", "CQ8")
            ],
            "policy_checks": [{"id": "A5", "status": "absent"}],
            "unavailable_checks": [],
        },
        "seo": {
            "score": 100.0,
            "criteria": [criterion(f"SEO{index}", 2) for index in range(1, 11)],
            "unavailable_checks": [],
        },
        "brand": {
            "score": 100.0,
            "criteria": [criterion(f"BV{index}", 2) for index in range(1, 8)],
            "unavailable_checks": [],
        },
        "compliance": {
            "score": 100.0,
            "criteria": [criterion(f"CP{index}", 2) for index in range(1, 9)],
            "policy_checks": [{"id": "A6", "status": "not_applicable"}],
            "flags": [],
            "unavailable_checks": [],
        },
    }


def replace_level(
    results: dict,
    agent: str,
    criterion_id: str,
    level: int | None,
    *,
    text: str = EXCERPT,
) -> None:
    results[agent]["criteria"] = [
        criterion(criterion_id, level, text=text)
        if item["id"] == criterion_id
        else item
        for item in results[agent]["criteria"]
    ]


def set_policy_check(
    results: dict,
    code: str,
    *,
    status: str = "present",
    reference_id: str | None = None,
    evidence: str = EXCERPT,
) -> None:
    agent = "content_quality" if code == "A5" else "compliance"
    check = {
        "id": code,
        "status": status,
        "field": "body",
        "evidence": evidence,
        "reason": (
            "Body không trả lời title và cần viết lại trên 50%."
            if code == "A5"
            else "Chỉ dẫn tạo nguy cơ kỹ thuật rõ ràng."
        ),
    }
    if reference_id is not None:
        check["reference_id"] = reference_id
    results[agent]["policy_checks"] = [check]


def expect_contract_error(action, fragment: str) -> None:
    try:
        action()
    except PolicyContractError as error:
        if fragment.casefold() not in str(error).casefold():
            raise AssertionError(
                f"Expected error chứa {fragment!r}, got {str(error)!r}"
            ) from error
    else:
        raise AssertionError(f"Expected PolicyContractError chứa {fragment!r}")


def assert_single_block(result: dict, decision: str, code: str) -> None:
    assert result["decision"] == decision, result
    assert result["decision_basis"]["blocking_codes"] == [code], result
    assert [item["defect_code"] for item in result["effective_findings"]] == [
        code
    ], result


def test_moi_ma_a_doc_lap_deu_rejected() -> None:
    for code, criterion_id in (
        ("A1", "CP1"),
        ("A2", "CP2"),
        ("A3", "CP3"),
    ):
        results = base_results()
        replace_level(results, "compliance", criterion_id, 0)
        actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
        assert_single_block(actual, "rejected", code)
        assert actual["decision_basis"]["highest_group"] == "A"

    results = base_results()
    set_policy_check(results, "A5")
    assert_single_block(
        evaluate(clean_fields(), results, assessment_as_of="2026-08-17"),
        "rejected",
        "A5",
    )

    fields = clean_fields()
    fields["body"] += "<!-- văn xuôi ẩn -->"
    results = base_results()
    results["compliance"]["flags"] = [
        {
            "criterion_id": "CP9",
            "defect_code": "A7",
            "field": "body",
            "evidence": "văn xuôi ẩn",
        }
    ]
    assert_single_block(
        evaluate(fields, results, assessment_as_of="2026-08-17"),
        "rejected",
        "A7",
    )


def test_moi_ma_b_doc_lap_deu_needs_revision() -> None:
    for code, agent, criterion_id in (
        # A4 giu ten ma "A4" (CP4/scoring/prompt/test khong doi) nhung
        # quyen chan da ha xuong nhom B - cung ly do/dot voi A6 (xem
        # docs/evidence/e1_v2_2026-08-18_report.md): CP4 gop chung vao
        # mot muc level "thoi han" (da tat dinh) va "dieu kien ap dung"
        # (thuan LLM, cung ho P-006a cu) nen khong tach rieng duoc.
        ("A4", "compliance", "CP4"),
        ("B1", "compliance", "CP5"),
        ("B2", "compliance", "CP6"),
        ("B5", "brand", "BV1"),
        ("B6", "seo", "SEO9"),
        ("B7", "seo", "SEO5"),
        ("B8", "content_quality", "CQ1"),
        ("B9", "content_quality", "CQ5"),
        ("B10", "content_quality", "CQ7"),
        ("B11", "compliance", "CP7"),
    ):
        results = base_results()
        replace_level(results, agent, criterion_id, 0)
        actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
        assert_single_block(actual, "needs_revision", code)
        assert actual["decision_basis"]["highest_group"] == "B"

    for code, changed_fields in (
        ("B3", {"meta_description": "quá ngắn"}),
        ("B4", {"title": "TIÊU ĐỀ VIẾT HOA TOÀN BỘ"}),
        ("B9", {"body": " ".join(["từ"] * 501)}),
    ):
        fields = clean_fields()
        fields.update(changed_fields)
        actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
        assert_single_block(actual, "needs_revision", code)

    # A6 giu ten ma "A6" (an toan reference/prompt/test khong doi) nhung
    # quyen chan da ha xuong nhom B - E1 v2 do that 2026-08-18 cho thay
    # phan doan "co khop dung safety rule" con dao dong giua cac lan goi
    # LLM (evidence/e1_v2_2026-08-18_report.md). Khong con tu no day
    # quyet dinh sang rejected duoc nua, dung mang tinh than "nghi van
    # nghiem trong chi tu LLM cung dung o needs_revision" da chot tu dau.
    results = base_results()
    set_policy_check(
        results,
        "A6",
        reference_id="VF-SAFE-CHARGING-CABLE-001",
    )
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert_single_block(actual, "needs_revision", "A6")
    assert actual["decision_basis"]["highest_group"] == "B"


def test_nhieu_b_khong_tu_nang_thanh_rejected() -> None:
    results = base_results()
    for agent, criterion_id in (
        ("compliance", "CP5"),
        ("compliance", "CP6"),
        ("content_quality", "CQ1"),
        ("content_quality", "CQ7"),
    ):
        replace_level(results, agent, criterion_id, 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert actual["decision_basis"] == {
        "highest_group": "B",
        "blocking_codes": ["B1", "B2", "B8", "B10"],
        "reason": "defect",
    }


def test_advisory_level_0_khong_chan_publish() -> None:
    results = base_results()
    for agent, criterion_id in (
        ("content_quality", "CQ3"),
        ("content_quality", "CQ4"),
        ("seo", "SEO7"),
        ("seo", "SEO10"),
    ):
        replace_level(results, agent, criterion_id, 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "publish"
    assert actual["effective_findings"] == []
    assert [item["source_check"] for item in actual["advisory_findings"]] == [
        "CQ3",
        "CQ4",
        "SEO7",
        "SEO10",
    ]


def test_clean_complete_publish_va_score_chi_diagnostic() -> None:
    actual = evaluate(
        clean_fields(),
        base_results(),
        assessment_as_of="2026-08-17",
        final_score=12.0,
    )
    assert actual["decision"] == "publish"
    assert actual["final_score"] == 12.0
    assert actual["coverage"]["complete"] is True
    assert actual["coverage"]["required_checks"] == [
        "A1",
        "A2",
        "A3",
        "A4",
        "A5",
        "A6",
        "A7",
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "B6",
        "B7",
        "B8",
        "B9",
        "B10",
        "B11",
    ]
    assert actual["decision_basis"] == {
        "highest_group": "none",
        "blocking_codes": [],
        "reason": "clean",
    }


def test_unavailable_khong_co_a_thanh_needs_revision() -> None:
    results = base_results()
    replace_level(results, "seo", "SEO5", None)
    results["seo"]["unavailable_checks"] = ["SEO5"]
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert actual["incomplete_assessment"] is True
    assert actual["coverage"]["complete"] is False
    assert actual["coverage"]["unavailable_checks"] == ["B7"]
    assert actual["decision_basis"] == {
        "highest_group": "none",
        "blocking_codes": [],
        "reason": "incomplete_assessment",
    }


def test_a_cong_unavailable_van_rejected_va_incomplete() -> None:
    results = base_results()
    replace_level(results, "compliance", "CP1", 0)
    replace_level(results, "seo", "SEO5", None)
    results["seo"]["unavailable_checks"] = ["SEO5"]
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "rejected"
    assert actual["incomplete_assessment"] is True
    assert actual["decision_basis"]["blocking_codes"] == ["A1"]
    assert actual["coverage"]["unavailable_checks"] == ["B7"]


def test_missing_agent_duoc_ghi_ro_va_fail_safe() -> None:
    results = base_results()
    results["brand"] = None
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert actual["missing_agents"] == ["brand"]
    assert actual["coverage"]["unavailable_checks"] == ["B5"]
    assert actual["incomplete_assessment"] is True


def test_multisource_chi_unavailable_khi_chua_co_finding() -> None:
    results = base_results()
    replace_level(results, "compliance", "CP8", None)
    results["compliance"]["unavailable_checks"] = ["CP8"]
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["coverage"]["unavailable_checks"] == ["B10"]
    assert actual["decision"] == "needs_revision"

    replace_level(results, "content_quality", "CQ7", 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert "B10" not in actual["coverage"]["unavailable_checks"]
    assert "B10" in actual["coverage"]["assessed_checks"]


def test_b10_dedupe_giu_hai_sources() -> None:
    results = base_results()
    replace_level(results, "content_quality", "CQ7", 0)
    replace_level(results, "compliance", "CP8", 0)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    b10 = [
        item
        for item in actual["effective_findings"]
        if item["defect_code"] == "B10"
    ]
    assert len(b10) == 1
    assert b10[0]["sources"] == ["CQ7", "CP8"]
    assert b10[0]["source_agent"] == "content_quality"
    assert b10[0]["source_check"] == "CQ7"


def test_output_order_canonical_va_khong_mutate_input() -> None:
    fields = clean_fields()
    results = base_results()
    replace_level(results, "compliance", "CP7", 0)
    replace_level(results, "compliance", "CP1", 0)
    before_fields = deepcopy(fields)
    before_results = deepcopy(results)
    actual = evaluate(fields, results, assessment_as_of="2026-08-17")
    assert [item["defect_code"] for item in actual["effective_findings"]] == [
        "A1",
        "B11",
    ]
    assert fields == before_fields
    assert results == before_results


def test_field_checks_dung_bien_va_assessment_date() -> None:
    for length in (140, 170):
        fields = clean_fields()
        fields["meta_description"] = "m" * length
        actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
        assert "B3" not in actual["decision_basis"]["blocking_codes"]

    for length in (139, 171):
        fields = clean_fields()
        fields["meta_description"] = "m" * length
        actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
        assert "B3" in actual["decision_basis"]["blocking_codes"]

    fields = clean_fields()
    fields["title"] = "Hướng dẫn sử dụng xe điện VinFast an toàn năm 2025"
    actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
    assert "B4" in actual["decision_basis"]["blocking_codes"]

    fields = clean_fields()
    fields["body"] = "<h3>Mục nhỏ</h3>" + " ".join(["từ"] * 501)
    actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
    assert "B9" in actual["decision_basis"]["blocking_codes"]

    fields["body"] = "<h2>Mục chính</h2>" + " ".join(["từ"] * 501)
    actual = evaluate(fields, base_results(), assessment_as_of="2026-08-17")
    assert "B9" not in actual["decision_basis"]["blocking_codes"]


def test_evidence_bia_khong_tao_finding_va_lam_incomplete() -> None:
    results = base_results()
    replace_level(
        results,
        "content_quality",
        "CQ1",
        0,
        text="đoạn không tồn tại trong bất kỳ field nào",
    )
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["effective_findings"] == []
    assert actual["decision"] == "needs_revision"
    assert actual["coverage"]["unavailable_checks"] == ["B8"]


def test_a6_thieu_reference_chi_needs_revision() -> None:
    results = base_results()
    set_policy_check(results, "A6")
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    assert actual["decision"] == "needs_revision"
    assert actual["effective_findings"] == []
    assert actual["coverage"]["unavailable_checks"] == ["A6"]


def test_finding_shape_on_dinh() -> None:
    results = base_results()
    replace_level(results, "content_quality", "CQ1", 1)
    actual = evaluate(clean_fields(), results, assessment_as_of="2026-08-17")
    finding = actual["effective_findings"][0]
    assert finding == {
        "defect_code": "B8",
        "group": "B",
        "source_agent": "content_quality",
        "source_check": "CQ1",
        "level": 1,
        "field": "body",
        "evidence_kind": "excerpt",
        "evidence": EXCERPT,
        "observed": None,
        "suggestion": "Sửa nội dung có vấn đề.",
        "reference_id": None,
        "sources": ["CQ1"],
    }


def test_unknown_va_malformed_schema_fatal() -> None:
    results = base_results()
    results["content_quality"]["policy_checks"] = [
        {"id": "A99", "status": "present"}
    ]
    expect_contract_error(
        lambda: evaluate(
            clean_fields(), results, assessment_as_of="2026-08-17"
        ),
        "A99",
    )

    results = base_results()
    results["compliance"]["policy_checks"] = [
        {"id": "CP9", "status": "absent"}
    ]
    expect_contract_error(
        lambda: evaluate(
            clean_fields(), results, assessment_as_of="2026-08-17"
        ),
        "CP9",
    )

    results = base_results()
    results["compliance"]["flags"] = [
        {
            "criterion_id": "CP9",
            "defect_code": "A99",
            "field": "body",
            "evidence": "văn xuôi ẩn",
        }
    ]
    expect_contract_error(
        lambda: evaluate(
            clean_fields(), results, assessment_as_of="2026-08-17"
        ),
        "A99",
    )

    results = base_results()
    results["seo"]["criteria"].append(criterion("SEO99", 0))
    expect_contract_error(
        lambda: evaluate(
            clean_fields(), results, assessment_as_of="2026-08-17"
        ),
        "SEO99",
    )

    expect_contract_error(
        lambda: evaluate(
            clean_fields(), base_results(), assessment_as_of="17/08/2026"
        ),
        "assessment_as_of",
    )


def test_policy_version_exact_khong_fuzzy() -> None:
    assert POLICY_V1 == "cam-nang-vn-v1"
    assert POLICY_V2 == "cam-nang-vn-v2"
    assert require_policy_version(None, allow_legacy_default=True) == POLICY_V1
    expect_contract_error(
        lambda: require_policy_version(None, allow_legacy_default=False),
        "policy_version",
    )
    for value in (
        "v2",
        "cam-nang-vn-v2 ",
        "CAM-NANG-VN-V2",
        "cam-nang-vn-v3",
    ):
        expect_contract_error(
            lambda value=value: require_policy_version(
                value, allow_legacy_default=False
            ),
            value,
        )


if __name__ == "__main__":
    failed = False
    for test in (
        test_moi_ma_a_doc_lap_deu_rejected,
        test_moi_ma_b_doc_lap_deu_needs_revision,
        test_nhieu_b_khong_tu_nang_thanh_rejected,
        test_advisory_level_0_khong_chan_publish,
        test_clean_complete_publish_va_score_chi_diagnostic,
        test_unavailable_khong_co_a_thanh_needs_revision,
        test_a_cong_unavailable_van_rejected_va_incomplete,
        test_missing_agent_duoc_ghi_ro_va_fail_safe,
        test_multisource_chi_unavailable_khi_chua_co_finding,
        test_b10_dedupe_giu_hai_sources,
        test_output_order_canonical_va_khong_mutate_input,
        test_field_checks_dung_bien_va_assessment_date,
        test_evidence_bia_khong_tao_finding_va_lam_incomplete,
        test_a6_thieu_reference_chi_needs_revision,
        test_finding_shape_on_dinh,
        test_unknown_va_malformed_schema_fatal,
        test_policy_version_exact_khong_fuzzy,
    ):
        try:
            test()
            print(f"[PASS] {test.__name__}")
        except Exception as error:
            failed = True
            print(f"[FAIL] {test.__name__}: {error}")
    sys.exit(1 if failed else 0)

"""Pure publish decision policy for ``cam-nang-vn-v2``.

Agent modules detect issues; this module only validates their result contract,
normalizes evidence, aggregates assessment coverage by canonical defect code,
and applies the literal A -> B -> incomplete -> publish decision order.
It deliberately does not import the graph, agents, provider, config, or clock.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

from text_utils import strip_html


POLICY_V1 = "cam-nang-vn-v1"
POLICY_V2 = "cam-nang-vn-v2"

AGENT_ORDER = ("content_quality", "seo", "brand", "compliance")
DEFECT_ORDER = (
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
)

# Each tuple is (agent, criterion id, blocking levels). Field and policy-only
# sources are added separately below. The mapping is literal on purpose: a
# digit in a criterion name must never acquire blocking authority by accident.
CRITERION_SOURCES = {
    "A1": (("compliance", "CP1", frozenset({0})),),
    "A2": (("compliance", "CP2", frozenset({0})),),
    "A3": (("compliance", "CP3", frozenset({0})),),
    "A4": (("compliance", "CP4", frozenset({0})),),
    "B1": (("compliance", "CP5", frozenset({0, 1})),),
    "B2": (("compliance", "CP6", frozenset({0, 1})),),
    "B5": tuple(
        ("brand", criterion_id, frozenset({0, 1}))
        for criterion_id in ("BV1", "BV2", "BV3", "BV4", "BV7")
    ),
    "B6": (("seo", "SEO9", frozenset({0, 1})),),
    "B7": (("seo", "SEO5", frozenset({0, 1})),),
    "B8": tuple(
        ("content_quality", criterion_id, frozenset({0, 1}))
        for criterion_id in ("CQ1", "CQ2")
    ),
    "B9": (("content_quality", "CQ5", frozenset({0, 1})),),
    "B10": (
        ("content_quality", "CQ7", frozenset({0, 1})),
        ("compliance", "CP8", frozenset({0, 1})),
    ),
    "B11": (("compliance", "CP7", frozenset({0, 1})),),
}

KNOWN_CRITERIA = {
    "content_quality": frozenset(f"CQ{index}" for index in range(1, 9)),
    "seo": frozenset(f"SEO{index}" for index in range(1, 11)),
    "brand": frozenset(f"BV{index}" for index in range(1, 8)),
    "compliance": frozenset(f"CP{index}" for index in range(1, 9)),
}
POLICY_CHECKS_BY_AGENT = {
    "content_quality": frozenset({"A5"}),
    "seo": frozenset(),
    "brand": frozenset(),
    "compliance": frozenset({"A6"}),
}
UNAVAILABLE_ONLY_CHECKS_BY_AGENT = {
    "content_quality": frozenset(),
    "seo": frozenset(),
    "brand": frozenset(),
    "compliance": frozenset({"CP9"}),
}

_CRITERION_TO_DEFECT: dict[tuple[str, str], tuple[str, frozenset[int]]] = {}
for _defect_code, _sources in CRITERION_SOURCES.items():
    for _agent, _criterion_id, _levels in _sources:
        _key = (_agent, _criterion_id)
        if _key in _CRITERION_TO_DEFECT:
            raise RuntimeError(f"duplicate canonical criterion source: {_key}")
        _CRITERION_TO_DEFECT[_key] = (_defect_code, _levels)

_YEAR_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_H2_RE = re.compile(r"<h2\b", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


class PolicyContractError(ValueError):
    """Raised when policy/schema drift makes an evaluation unsafe."""


def require_policy_version(
    value: str | None,
    *,
    allow_legacy_default: bool,
) -> str:
    """Return one of the two exact policy IDs or fail closed."""
    if value is None:
        if allow_legacy_default:
            return POLICY_V1
        raise PolicyContractError("policy_version is required")
    if value not in {POLICY_V1, POLICY_V2}:
        raise PolicyContractError(f"unknown policy_version: {value!r}")
    return value


def _assessment_year(value: str) -> int:
    if not isinstance(value, str) or not _ISO_DATE_RE.fullmatch(value):
        raise PolicyContractError(
            f"assessment_as_of must use YYYY-MM-DD, got {value!r}"
        )
    try:
        return date.fromisoformat(value).year
    except ValueError as error:
        raise PolicyContractError(
            f"assessment_as_of is not a valid date: {value!r}"
        ) from error


def _field_value(fields: dict, name: str) -> str:
    value = fields.get(name, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PolicyContractError(f"field {name!r} must be a string")
    return value


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _evidence_is_exact(fields: dict, field: Any, evidence: Any) -> bool:
    if not isinstance(field, str) or field not in fields:
        return False
    if not isinstance(evidence, str):
        return False
    raw = _field_value(fields, field)
    normalized_evidence = _normalize_text(evidence)
    if not normalized_evidence:
        return not _normalize_text(strip_html(raw))
    return (
        normalized_evidence in _normalize_text(raw)
        or normalized_evidence in _normalize_text(strip_html(raw))
    )


def _validate_agent_result(agent: str, result: Any) -> dict | None:
    if result is None:
        return None
    if not isinstance(result, dict):
        raise PolicyContractError(f"result for {agent} must be an object or null")

    criteria = result.get("criteria", [])
    if not isinstance(criteria, list):
        raise PolicyContractError(f"{agent}.criteria must be a list")
    criterion_by_id: dict[str, dict] = {}
    for item in criteria:
        if not isinstance(item, dict):
            raise PolicyContractError(f"{agent}.criteria contains a non-object")
        criterion_id = item.get("id")
        if criterion_id not in KNOWN_CRITERIA[agent]:
            raise PolicyContractError(
                f"unknown criterion id for {agent}: {criterion_id!r}"
            )
        if criterion_id in criterion_by_id:
            raise PolicyContractError(
                f"duplicate criterion id for {agent}: {criterion_id}"
            )
        level = item.get("level")
        if level is not None and (
            isinstance(level, bool) or not isinstance(level, int) or level not in {0, 1, 2}
        ):
            raise PolicyContractError(
                f"invalid level for {agent}.{criterion_id}: {level!r}"
            )
        occurrences = item.get("occurrences", [])
        if not isinstance(occurrences, list) or not all(
            isinstance(occurrence, dict) for occurrence in occurrences
        ):
            raise PolicyContractError(
                f"{agent}.{criterion_id}.occurrences must be a list of objects"
            )
        criterion_by_id[criterion_id] = item

    unavailable = result.get("unavailable_checks", [])
    if not isinstance(unavailable, list) or not all(
        isinstance(item, str) for item in unavailable
    ):
        raise PolicyContractError(f"{agent}.unavailable_checks must be a list")
    allowed_unavailable = (
        KNOWN_CRITERIA[agent]
        | POLICY_CHECKS_BY_AGENT[agent]
        | UNAVAILABLE_ONLY_CHECKS_BY_AGENT[agent]
    )
    unknown_unavailable = sorted(set(unavailable) - allowed_unavailable)
    if unknown_unavailable:
        raise PolicyContractError(
            f"unknown unavailable check for {agent}: {unknown_unavailable}"
        )

    policy_checks = result.get("policy_checks", [])
    if not isinstance(policy_checks, list) or not all(
        isinstance(item, dict) for item in policy_checks
    ):
        raise PolicyContractError(f"{agent}.policy_checks must be a list of objects")
    policy_by_id: dict[str, dict] = {}
    for check in policy_checks:
        check_id = check.get("id")
        if check_id not in POLICY_CHECKS_BY_AGENT[agent]:
            raise PolicyContractError(
                f"unknown policy check for {agent}: {check_id!r}"
            )
        if check_id in policy_by_id:
            raise PolicyContractError(
                f"duplicate policy check for {agent}: {check_id}"
            )
        allowed_statuses = (
            {"present", "absent", "unavailable"}
            if check_id == "A5"
            else {"present", "absent", "not_applicable", "unavailable"}
        )
        if check.get("status") not in allowed_statuses:
            raise PolicyContractError(
                f"invalid status for {agent}.{check_id}: {check.get('status')!r}"
            )
        policy_by_id[check_id] = check

    flags = result.get("flags", [])
    if not isinstance(flags, list) or not all(isinstance(item, dict) for item in flags):
        raise PolicyContractError(f"{agent}.flags must be a list of objects")
    for flag in flags:
        defect_code = flag.get("defect_code")
        if defect_code is not None and defect_code not in DEFECT_ORDER:
            raise PolicyContractError(f"unknown defect_code in flag: {defect_code!r}")
        if defect_code is not None and not (
            agent == "compliance"
            and flag.get("criterion_id") == "CP9"
            and defect_code == "A7"
        ):
            raise PolicyContractError(
                "flag mapping is not canonical: "
                f"{agent}.{flag.get('criterion_id')} -> {defect_code}"
            )

    return {
        "raw": result,
        "criteria": criterion_by_id,
        "policy_checks": policy_by_id,
        "unavailable": set(unavailable),
        "flags": flags,
    }


def _criterion_finding(
    defect_code: str,
    agent: str,
    criterion_id: str,
    criterion: dict,
    occurrence: dict,
) -> dict:
    evidence = occurrence.get("text", "")
    suggestion = criterion.get("suggestion") or criterion.get("reason") or ""
    return {
        "defect_code": defect_code,
        "group": defect_code[0],
        "source_agent": agent,
        "source_check": criterion_id,
        "level": criterion["level"],
        "field": occurrence.get("field"),
        "evidence_kind": "absence" if not evidence else "excerpt",
        "evidence": evidence,
        "observed": None,
        "suggestion": suggestion,
        "reference_id": None,
        "sources": [criterion_id],
    }


def _policy_finding(code: str, agent: str, check: dict) -> dict:
    return {
        "defect_code": code,
        "group": "A",
        "source_agent": agent,
        "source_check": code,
        "level": None,
        "field": check.get("field"),
        "evidence_kind": "excerpt",
        "evidence": check.get("evidence", ""),
        "observed": None,
        "suggestion": check.get("suggestion") or check.get("reason") or "",
        "reference_id": check.get("reference_id"),
        "sources": [code],
    }


def _field_finding(
    code: str,
    source_check: str,
    field: str,
    evidence_kind: str,
    observed: Any,
    suggestion: str,
) -> dict:
    return {
        "defect_code": code,
        "group": "B",
        "source_agent": "field_check",
        "source_check": source_check,
        "level": None,
        "field": field,
        "evidence_kind": evidence_kind,
        "evidence": "",
        "observed": observed,
        "suggestion": suggestion,
        "reference_id": None,
        "sources": [source_check],
    }


def _criterion_source(
    fields: dict,
    prepared: dict[str, dict | None],
    defect_code: str,
    agent: str,
    criterion_id: str,
    blocking_levels: frozenset[int],
) -> tuple[str, list[dict]]:
    result = prepared[agent]
    if result is None:
        return "unavailable", []
    criterion = result["criteria"].get(criterion_id)
    if criterion is None or criterion_id in result["unavailable"]:
        return "unavailable", []
    level = criterion["level"]
    if level is None:
        return "not_applicable", []
    if level not in blocking_levels:
        return "assessed", []

    findings = []
    for occurrence in criterion.get("occurrences", []):
        if _evidence_is_exact(
            fields, occurrence.get("field"), occurrence.get("text")
        ):
            findings.append(
                _criterion_finding(
                    defect_code,
                    agent,
                    criterion_id,
                    criterion,
                    occurrence,
                )
            )
    return ("present", findings) if findings else ("unavailable", [])


def _policy_source(
    fields: dict,
    prepared: dict[str, dict | None],
    code: str,
    agent: str,
) -> tuple[str, list[dict]]:
    result = prepared[agent]
    if result is None:
        return "unavailable", []
    if code in result["unavailable"]:
        return "unavailable", []
    check = result["policy_checks"].get(code)
    if check is None:
        return "unavailable", []
    status = check["status"]
    if status == "unavailable":
        return "unavailable", []
    if status == "not_applicable":
        return "not_applicable", []
    if status == "absent":
        return "assessed", []
    if not _evidence_is_exact(fields, check.get("field"), check.get("evidence")):
        return "unavailable", []
    if code == "A6" and not str(check.get("reference_id") or "").strip():
        return "unavailable", []
    return "present", [_policy_finding(code, agent, check)]


def _a7_source(
    fields: dict,
    prepared: dict[str, dict | None],
) -> tuple[str, list[dict]]:
    result = prepared["compliance"]
    if result is None or "CP9" in result["unavailable"]:
        return "unavailable", []
    matches = [
        flag
        for flag in result["flags"]
        if flag.get("criterion_id") == "CP9" and flag.get("defect_code") == "A7"
    ]
    if not matches:
        return "assessed", []
    findings = []
    for flag in matches:
        evidence = flag.get("evidence", "")
        field = flag.get("field")
        if not _evidence_is_exact(fields, field, evidence):
            continue
        findings.append(
            {
                "defect_code": "A7",
                "group": "A",
                "source_agent": "compliance",
                "source_check": "CP9",
                "level": None,
                "field": field,
                "evidence_kind": "excerpt",
                "evidence": evidence,
                "observed": None,
                "suggestion": flag.get("suggestion") or "Xóa văn xuôi bị ẩn.",
                "reference_id": None,
                "sources": ["CP9"],
            }
        )
    return ("present", findings) if findings else ("unavailable", [])


def _field_sources(
    fields: dict,
    assessment_year: int,
) -> dict[str, tuple[str, list[dict]]]:
    meta = _field_value(fields, "meta_description").strip()
    title = _field_value(fields, "title").strip()
    body = _field_value(fields, "body")

    meta_bad = not 140 <= len(meta) <= 170
    meta_findings = (
        [
            _field_finding(
                "B3",
                "FIELD_B3",
                "meta_description",
                "absence" if not meta else "measurement",
                {"length": len(meta)},
                "Viết meta description trong khoảng 140–170 ký tự.",
            )
        ]
        if meta_bad
        else []
    )

    stale_years = sorted(
        {int(match.group(0)) for match in _YEAR_RE.finditer(title) if int(match.group(0)) < assessment_year}
    )
    title_bad = not 40 <= len(title) <= 70 or title.isupper() or bool(stale_years)
    title_findings = (
        [
            _field_finding(
                "B4",
                "FIELD_B4",
                "title",
                "absence" if not title else "measurement",
                {
                    "length": len(title),
                    "all_caps": title.isupper(),
                    "stale_years": stale_years,
                },
                "Sửa độ dài, kiểu viết hoa hoặc năm cũ trong title.",
            )
        ]
        if title_bad
        else []
    )

    word_count = len(strip_html(body).split())
    has_h2 = bool(_H2_RE.search(body))
    body_bad = word_count > 500 and not has_h2
    body_findings = (
        [
            _field_finding(
                "B9",
                "FIELD_B9",
                "body",
                "measurement",
                {"word_count": word_count, "has_h2": has_h2},
                "Chia bài dài bằng ít nhất một heading H2.",
            )
        ]
        if body_bad
        else []
    )

    return {
        "B3": ("present" if meta_findings else "assessed", meta_findings),
        "B4": ("present" if title_findings else "assessed", title_findings),
        "B9": ("present" if body_findings else "assessed", body_findings),
    }


def _advisory_findings(
    fields: dict,
    prepared: dict[str, dict | None],
) -> list[dict]:
    findings = []
    for agent in AGENT_ORDER:
        result = prepared[agent]
        if result is None:
            continue
        for criterion_id, criterion in result["criteria"].items():
            if (agent, criterion_id) in _CRITERION_TO_DEFECT:
                continue
            if criterion["level"] not in {0, 1}:
                continue
            for occurrence in criterion.get("occurrences", []):
                if not _evidence_is_exact(
                    fields, occurrence.get("field"), occurrence.get("text")
                ):
                    continue
                evidence = occurrence.get("text", "")
                findings.append(
                    {
                        "source_agent": agent,
                        "source_check": criterion_id,
                        "level": criterion["level"],
                        "field": occurrence.get("field"),
                        "evidence_kind": "absence" if not evidence else "excerpt",
                        "evidence": evidence,
                        "observed": None,
                        "suggestion": criterion.get("suggestion")
                        or criterion.get("reason")
                        or "",
                    }
                )
    return findings


def _dedupe_findings(findings: list[dict]) -> list[dict]:
    merged: dict[tuple[str, str, str], dict] = {}
    for finding in findings:
        key = (
            finding["defect_code"],
            finding.get("field") or "",
            _normalize_text(finding.get("evidence") or ""),
        )
        if key not in merged:
            merged[key] = dict(finding)
            merged[key]["sources"] = list(finding["sources"])
            continue
        for source in finding["sources"]:
            if source not in merged[key]["sources"]:
                merged[key]["sources"].append(source)
    order = {code: index for index, code in enumerate(DEFECT_ORDER)}
    return sorted(
        merged.values(),
        key=lambda item: (
            order[item["defect_code"]],
            item.get("field") or "",
            _normalize_text(item.get("evidence") or ""),
        ),
    )


def _coverage(
    source_states: dict[str, list[str]],
    findings: list[dict],
) -> dict:
    present_codes = {finding["defect_code"] for finding in findings}
    assessed = []
    not_applicable = []
    unavailable = []
    for code in DEFECT_ORDER:
        states = source_states[code]
        if code in present_codes:
            assessed.append(code)
        elif "unavailable" in states:
            unavailable.append(code)
        elif states and all(state == "not_applicable" for state in states):
            not_applicable.append(code)
        else:
            assessed.append(code)
    return {
        "required_checks": list(DEFECT_ORDER),
        "assessed_checks": assessed,
        "not_applicable_checks": not_applicable,
        "unavailable_checks": unavailable,
        "complete": not unavailable,
    }


def evaluate(
    fields: dict,
    agent_results: dict,
    *,
    assessment_as_of: str,
    final_score: float | None = None,
) -> dict:
    """Evaluate one article with the literal v2 blocking contract.

    ``final_score`` is returned for diagnostics only and never participates in
    the decision. The caller supplies ``assessment_as_of``; this function does
    not read the clock.
    """
    if not isinstance(fields, dict):
        raise PolicyContractError("fields must be an object")
    if not isinstance(agent_results, dict):
        raise PolicyContractError("agent_results must be an object")
    unknown_agents = sorted(set(agent_results) - set(AGENT_ORDER))
    if unknown_agents:
        raise PolicyContractError(f"unknown agent result keys: {unknown_agents}")
    assessment_year = _assessment_year(assessment_as_of)

    prepared = {
        agent: _validate_agent_result(agent, agent_results.get(agent))
        for agent in AGENT_ORDER
    }
    missing_agents = [agent for agent in AGENT_ORDER if prepared[agent] is None]
    source_states: dict[str, list[str]] = {code: [] for code in DEFECT_ORDER}
    raw_findings: list[dict] = []

    for defect_code, sources in CRITERION_SOURCES.items():
        for agent, criterion_id, blocking_levels in sources:
            state, findings = _criterion_source(
                fields,
                prepared,
                defect_code,
                agent,
                criterion_id,
                blocking_levels,
            )
            source_states[defect_code].append(state)
            raw_findings.extend(findings)

    for code, agent in (("A5", "content_quality"), ("A6", "compliance")):
        state, findings = _policy_source(fields, prepared, code, agent)
        source_states[code].append(state)
        raw_findings.extend(findings)

    state, findings = _a7_source(fields, prepared)
    source_states["A7"].append(state)
    raw_findings.extend(findings)

    for code, (state, findings) in _field_sources(fields, assessment_year).items():
        source_states[code].append(state)
        raw_findings.extend(findings)

    effective_findings = _dedupe_findings(raw_findings)
    coverage = _coverage(source_states, effective_findings)
    blocking_codes = [
        code
        for code in DEFECT_ORDER
        if any(finding["defect_code"] == code for finding in effective_findings)
    ]
    has_a = any(code.startswith("A") for code in blocking_codes)
    has_b = any(code.startswith("B") for code in blocking_codes)
    if has_a:
        decision = "rejected"
        highest_group = "A"
        reason = "defect"
    elif has_b:
        decision = "needs_revision"
        highest_group = "B"
        reason = "defect"
    elif not coverage["complete"]:
        decision = "needs_revision"
        highest_group = "none"
        reason = "incomplete_assessment"
    else:
        decision = "publish"
        highest_group = "none"
        reason = "clean"

    return {
        "policy_version": POLICY_V2,
        "decision": decision,
        "final_score": final_score,
        "effective_findings": effective_findings,
        "advisory_findings": _advisory_findings(fields, prepared),
        "decision_basis": {
            "highest_group": highest_group,
            "blocking_codes": blocking_codes,
            "reason": reason,
        },
        "coverage": coverage,
        "incomplete_assessment": not coverage["complete"],
        "missing_agents": missing_agents,
        "drift": [],
    }

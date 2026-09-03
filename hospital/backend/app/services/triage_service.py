"""Deterministic and Gemini-assisted prototype triage for VITAVIA."""

import logging
from typing import Optional

from app.services.gemini_service import analyze_vitals_with_gemini
from app.models.schemas import TriageResult, VitalSigns


logger = logging.getLogger(__name__)

SEVERITY_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}


def analyze_vitals(vitals: VitalSigns) -> TriageResult:
    """Analyze simulated vitals using prototype simulation rules only — not for real clinical use."""
    critical_findings = []
    if vitals.spo2 <= 82:
        critical_findings.append("very low oxygen saturation")
    if vitals.systolic_bp < 80:
        critical_findings.append("very low systolic blood pressure")
    if vitals.heart_rate >= 160:
        critical_findings.append("very elevated heart rate")

    if critical_findings:
        return _triage_result(
            severity="CRITICAL",
            required_infrastructure=["emergency_bed", "icu", "ventilator", "emergency_team"],
            findings=critical_findings,
        )

    high_findings = []
    if vitals.spo2 < 92:
        high_findings.append("low oxygen saturation")
    if vitals.heart_rate >= 120:
        high_findings.append("elevated heart rate")
    if vitals.systolic_bp <= 90:
        high_findings.append("low systolic blood pressure")

    if high_findings:
        return _triage_result(
            severity="HIGH",
            required_infrastructure=["emergency_bed", "icu", "emergency_team"],
            findings=high_findings,
        )

    moderate_findings = []
    if vitals.spo2 < 95:
        moderate_findings.append("mildly reduced oxygen saturation")
    if vitals.heart_rate >= 100:
        moderate_findings.append("increased heart rate")
    if vitals.systolic_bp <= 100:
        moderate_findings.append("reduced systolic blood pressure")
    if vitals.temperature >= 38.5:
        moderate_findings.append("elevated temperature")

    if moderate_findings:
        return _triage_result(
            severity="MODERATE",
            required_infrastructure=["emergency_bed", "emergency_team"],
            findings=moderate_findings,
        )

    return TriageResult(
        severity="LOW",
        required_infrastructure=["emergency_bed"],
        explanation="Prototype rule-based analysis found no simulated high-priority abnormalities.",
        source="deterministic",
    )


def analyze_vitals_assisted(
    vitals: VitalSigns, emergency_type: Optional[str] = None
) -> TriageResult:
    """Use optional Gemini support while preserving deterministic minimum safety requirements."""
    deterministic_result = analyze_vitals(vitals)
    try:
        gemini_result = analyze_vitals_with_gemini(vitals, emergency_type)
    except Exception:
        logger.warning("Gemini analysis unavailable; using deterministic fallback.")
        return deterministic_result

    if gemini_result is None:
        return deterministic_result
    return _apply_deterministic_guard(deterministic_result, gemini_result)


def _triage_result(severity: str, required_infrastructure: list[str], findings: list[str]) -> TriageResult:
    """Create an understandable explanation for a deterministic prototype result."""
    return TriageResult(
        severity=severity,
        required_infrastructure=required_infrastructure,
        explanation=(
            "Prototype rule-based analysis identified "
            f"{_format_findings(findings)}."
        ),
        source="deterministic",
    )


def _apply_deterministic_guard(
    deterministic_result: TriageResult, gemini_result: TriageResult
) -> TriageResult:
    """Ensure Gemini can add support but cannot weaken deterministic severity or requirements."""
    final_severity = max(
        (deterministic_result.severity, gemini_result.severity),
        key=lambda severity: SEVERITY_ORDER[severity],
    )
    final_requirements = list(deterministic_result.required_infrastructure)
    for resource in gemini_result.required_infrastructure:
        if resource not in final_requirements:
            final_requirements.append(resource)

    safeguard_applied = (
        final_severity != gemini_result.severity
        or final_requirements != gemini_result.required_infrastructure
    )
    explanation = gemini_result.explanation
    if safeguard_applied:
        explanation = f"{explanation} Deterministic safeguards preserved minimum requirements."

    return TriageResult(
        severity=final_severity,
        required_infrastructure=final_requirements,
        explanation=explanation,
        source="gemini",
    )


def _format_findings(findings: list[str]) -> str:
    """Join finding text into a concise, natural-language explanation."""
    if len(findings) == 1:
        return findings[0]
    if len(findings) == 2:
        return f"{findings[0]} and {findings[1]}"
    return f"{', '.join(findings[:-1])}, and {findings[-1]}"

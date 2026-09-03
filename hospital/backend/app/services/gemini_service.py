"""Optional Gemini interaction and response validation for VITAVIA triage."""

import json
import logging
from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import TriageResult, VitalSigns


logger = logging.getLogger(__name__)

ALLOWED_SEVERITIES = {"LOW", "MODERATE", "HIGH", "CRITICAL"}
ALLOWED_INFRASTRUCTURE = {
    "emergency_bed",
    "icu",
    "ventilator",
    "emergency_team",
}
GEMINI_TIMEOUT_MS = 10_000


class GeminiTriagePayload(BaseModel):
    """The constrained structured response expected from Gemini."""

    severity: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    required_infrastructure: list[
        Literal["emergency_bed", "icu", "ventilator", "emergency_team"]
    ]
    explanation: str


def is_gemini_configured() -> bool:
    """Return whether an API key is available without exposing its value."""
    return bool(settings.gemini_api_key and settings.gemini_api_key.strip())


def analyze_vitals_with_gemini(
    vitals: VitalSigns, emergency_type: Optional[str] = None
) -> Optional[TriageResult]:
    """Request optional structured Gemini decision support, returning None on any failure."""
    if not is_gemini_configured():
        return None

    try:
        client, types = _create_gemini_client()
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=_build_prompt(vitals, emergency_type),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiTriagePayload,
                temperature=0,
            ),
        )
        payload = _extract_response_payload(response)
        normalized = normalize_gemini_response(payload)
        if normalized is None:
            logger.warning("Gemini output validation failed; using deterministic fallback.")
        return normalized
    except Exception:
        logger.warning("Gemini analysis unavailable; using deterministic fallback.")
        return None


def normalize_gemini_response(payload: Any) -> Optional[TriageResult]:
    """Validate and normalize untrusted Gemini output into VITAVIA's shared triage model."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump()
    if not isinstance(payload, dict):
        return None

    severity = payload.get("severity")
    required_infrastructure = payload.get("required_infrastructure")
    explanation = payload.get("explanation")

    if not isinstance(severity, str) or severity not in ALLOWED_SEVERITIES:
        return None
    if not isinstance(required_infrastructure, list) or not required_infrastructure:
        return None
    if not isinstance(explanation, str) or not explanation.strip() or len(explanation.strip()) > 500:
        return None

    normalized_infrastructure = []
    for resource in required_infrastructure:
        if not isinstance(resource, str) or resource not in ALLOWED_INFRASTRUCTURE:
            return None
        if resource not in normalized_infrastructure:
            normalized_infrastructure.append(resource)

    return TriageResult(
        severity=severity,
        required_infrastructure=normalized_infrastructure,
        explanation=explanation.strip(),
        source="gemini",
    )


def _create_gemini_client():
    """Create the SDK client lazily so no-key fallback needs no Gemini initialization."""
    from google import genai
    from google.genai import types

    return (
        genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        ),
        types,
    )


def _build_prompt(vitals: VitalSigns, emergency_type: Optional[str]) -> str:
    """Build a constrained simulation-only prompt without any hospital-selection data."""
    return f"""
VITAVIA is an educational ambulance-routing simulation/prototype, not a real medical system.
The patient data below is simulated. Analyze only the simulated vitals for decision support.
Do not select or recommend a hospital. Do not provide treatment instructions. Do not diagnose a disease.
Return only the requested structured fields: severity, required_infrastructure, and explanation.
Severity must be one of LOW, MODERATE, HIGH, or CRITICAL.
Infrastructure entries must be only emergency_bed, icu, ventilator, or emergency_team.

Simulated emergency type: {emergency_type or "Not specified"}
SpO2: {vitals.spo2}%
Heart rate: {vitals.heart_rate} BPM
Blood pressure: {vitals.systolic_bp}/{vitals.diastolic_bp} mmHg
Temperature: {vitals.temperature}°C
""".strip()


def _extract_response_payload(response: Any) -> Any:
    """Prefer SDK-parsed structured output, with safe JSON text parsing as a fallback."""
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        return parsed

    response_text = getattr(response, "text", None)
    if not isinstance(response_text, str) or not response_text.strip():
        return None
    return json.loads(response_text)

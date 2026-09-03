"""
Gemini AI Clinical Decision Support Service.
Provides patient vital sign analysis to determine triage urgency,
required hospital infrastructure, and clinical summary.
Features robust heuristic fallback if GEMINI_API_KEY is not configured or offline.
"""

import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv, find_dotenv

from backend.models import PatientVitals, PatientInfo, GeminiAnalysis

logger = logging.getLogger("VitaVia.GeminiService")


def _heuristic_clinical_triage(vitals: PatientVitals, patient: Optional[PatientInfo] = None) -> GeminiAnalysis:
    """
    Deterministic rule-based clinical triage heuristic.
    Guarantees reliable decision support even when offline or without an API key.
    """
    spo2 = vitals.spo2
    hr = vitals.heart_rate
    sbp = vitals.systolic_bp
    temp = vitals.temperature
    
    required_infra = ["Emergency Bed", "Emergency Doctor"]
    
    # Critical condition
    if spo2 < 88.0 or sbp < 80 or (hr > 135 and sbp < 90) or temp >= 40.0:
        urgency = "CRITICAL"
        required_infra.extend(["ICU", "Ventilator"])
        summary = f"Severe hemodynamic/respiratory instability (SpO2 {spo2}%, HR {hr} bpm, BP {sbp}/{vitals.diastolic_bp}). Immediate ICU & ventilator support mandatory."
        notes = "Patient exhibits signs of decompensated shock or severe acute respiratory failure. Requires tertiary Level-1 trauma/ICU capability."
    # High urgency
    elif spo2 < 92.0 or hr > 115 or sbp < 90 or sbp > 180 or temp >= 38.8:
        urgency = "HIGH"
        required_infra.append("ICU")
        if spo2 < 91.0:
            required_infra.append("Ventilator")
        summary = f"Acute distress detected (SpO2 {spo2}%, HR {hr} bpm, Temp {temp}°C). Urgent emergency bed and ICU readiness needed."
        notes = "Signs of compromised oxygenation or cardiovascular stress. Patient requires continuous multi-parameter monitoring."
    # Moderate urgency
    elif spo2 < 95.0 or hr > 100 or temp >= 37.8 or sbp > 140:
        urgency = "MODERATE"
        summary = f"Moderate physiological deviation (SpO2 {spo2}%, HR {hr} bpm). Standard emergency stabilization required."
        notes = "Patient requires acute emergency physician assessment and supplemental oxygen therapy."
    # Low urgency / Stable
    else:
        urgency = "LOW"
        summary = f"Vital parameters within acceptable range (SpO2 {spo2}%, HR {hr} bpm, BP {sbp}/{vitals.diastolic_bp})."
        notes = "Routine emergency observation and physician consultation."

    # Remove duplicates while preserving order
    deduped_infra = list(dict.fromkeys(required_infra))

    return GeminiAnalysis(
        urgency=urgency,
        required_infrastructure=deduped_infra,
        summary=summary,
        clinical_notes=notes,
        source="HEURISTIC_FALLBACK"
    )


def analyze_patient_vitals(vitals: PatientVitals, patient: Optional[PatientInfo] = None) -> GeminiAnalysis:
    """
    Analyzes patient vitals using Google Gemini API if available,
    otherwise smoothly falls back to the deterministic clinical heuristic.
    """
    dotenv_file = find_dotenv()
    if dotenv_file:
        load_dotenv(dotenv_file, override=True)
        
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if not api_key:
        logger.info("GEMINI_API_KEY not configured. Using intelligent heuristic triage fallback.")
        return _heuristic_clinical_triage(vitals, patient)

    prompt = f"""
You are a clinical decision-support AI assisting an emergency ambulance dispatch system.
Analyze the following live patient telemetry:

PATIENT VITALS:
- SpO2 (Oxygen Saturation): {vitals.spo2}%
- Heart Rate: {vitals.heart_rate} BPM
- Blood Pressure: {vitals.systolic_bp}/{vitals.diastolic_bp} mmHg
- Body Temperature: {vitals.temperature} °C
- Chief Complaint: {patient.chief_complaint if patient else 'Emergency transit'}
- Patient Age: {patient.age if patient else 'Unknown'}

Return ONLY a valid JSON object with the following exact structure:
{{
  "urgency": "CRITICAL" | "HIGH" | "MODERATE" | "LOW",
  "required_infrastructure": ["Emergency Bed", "ICU", "Ventilator", "Emergency Doctor"],
  "summary": "Concise 1-2 sentence clinical summary of patient condition.",
  "clinical_notes": "Key clinical reasoning for required infrastructure."
}}

Criteria for required_infrastructure:
- Include "Emergency Bed" and "Emergency Doctor" for all acute cases.
- Include "ICU" if the patient shows shock, hypoxemia (SpO2 < 92%), severe hypertension/hypotension, or severe tachycardia.
- Include "Ventilator" if the patient has severe hypoxia (SpO2 < 89%) or respiratory failure.
Do not output markdown code blocks. Output plain JSON.
"""

    # Attempt GenAI SDK call
    try:
        raw_text = None
        
        # 1. Primary: modern google-genai SDK
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            # Try gemini-2.5-flash or gemini-2.0-flash
            for model_name in ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash']:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    if response and response.text:
                        raw_text = response.text
                        break
                except Exception:
                    continue
        except Exception:
            pass

        # 2. Secondary fallback: google.generativeai SDK
        if not raw_text:
            import google.generativeai as gai
            gai.configure(api_key=api_key)
            for m_name in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
                try:
                    model = gai.GenerativeModel(m_name)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        raw_text = response.text
                        break
                except Exception:
                    continue

        if not raw_text:
            raise RuntimeError("Gemini API call returned empty response across available models.")

        # Clean JSON response from markdown wrappers if present
        clean_text = raw_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        data = json.loads(clean_text)

        urgency = str(data.get("urgency", "HIGH")).upper()
        if urgency not in ["CRITICAL", "HIGH", "MODERATE", "LOW"]:
            urgency = "HIGH"

        req_infra = data.get("required_infrastructure", ["Emergency Bed", "Emergency Doctor"])
        if not isinstance(req_infra, list):
            req_infra = ["Emergency Bed", "Emergency Doctor"]

        return GeminiAnalysis(
            urgency=urgency,
            required_infrastructure=req_infra,
            summary=data.get("summary", "Patient requires emergency medical evaluation."),
            clinical_notes=data.get("clinical_notes", "Evaluated by Gemini Clinical Decision Support."),
            source="GEMINI_API"
        )

    except Exception as exc:
        logger.warning(f"Gemini API invocation failed or error parsing response ({exc}). Falling back to heuristic triage.")
        fallback = _heuristic_clinical_triage(vitals, patient)
        fallback.clinical_notes = f"Fallback active (API error: {type(exc).__name__})"
        return fallback

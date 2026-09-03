"""Deterministic selection and acknowledgement for the VITAVIA prototype."""

from typing import Optional

from app.models.schemas import (
    Acknowledgement,
    EmergencySnapshot,
    Hospital,
    HospitalDecision,
    HospitalEvaluation,
    TriageResult,
)
from app.services.hospital_service import evaluate_hospitals
from app.services.routing_service import calculate_route
from app.services.triage_service import analyze_vitals_assisted


def run_decision_pipeline(
    snapshot: EmergencySnapshot, hospitals: list[Hospital]
) -> tuple[TriageResult, list[HospitalDecision], Optional[HospitalDecision], Acknowledgement]:
    """Apply triage, infrastructure filtering, routes, then ETA-only eligible selection."""
    triage = analyze_vitals_assisted(
        snapshot.vitals, emergency_type=snapshot.patient.emergency_type
    )
    evaluations = evaluate_hospitals(triage.required_infrastructure, hospitals)
    decisions = _build_hospital_decisions(evaluations, hospitals, snapshot.ambulance.location)
    selected_hospital = select_fastest_eligible_hospital(decisions)
    acknowledgement = create_acknowledgement(selected_hospital)

    if selected_hospital is not None:
        decisions = [
            decision.model_copy(
                update={"selected": True, "acknowledgement_status": "ACCEPTED"}
            )
            if decision.hospital_id == selected_hospital.hospital_id
            else decision
            for decision in decisions
        ]
        selected_hospital = next(
            decision for decision in decisions if decision.hospital_id == selected_hospital.hospital_id
        )

    return triage, decisions, selected_hospital, acknowledgement


def select_fastest_eligible_hospital(
    decisions: list[HospitalDecision],
) -> Optional[HospitalDecision]:
    """Choose only from eligible hospitals, using normalized route ETA as the key."""
    eligible_hospitals = [decision for decision in decisions if decision.eligible]
    if not eligible_hospitals:
        return None
    return min(eligible_hospitals, key=lambda decision: decision.eta_minutes or float("inf"))


def create_acknowledgement(selected_hospital: Optional[HospitalDecision]) -> Acknowledgement:
    """Return a synchronous simulated acknowledgement for the final selection."""
    if selected_hospital is None:
        return Acknowledgement(
            status="NO_SUITABLE_HOSPITAL",
            message="No simulated hospital meets the required infrastructure.",
        )
    return Acknowledgement(
        status="ACCEPTED",
        hospital_id=selected_hospital.hospital_id,
        message=f"{selected_hospital.name} acknowledged the incoming ambulance.",
    )


def _build_hospital_decisions(
    evaluations: list[HospitalEvaluation], hospitals: list[Hospital], origin
) -> list[HospitalDecision]:
    """Attach route context without allowing it to affect infrastructure eligibility."""
    hospitals_by_id = {hospital.hospital_id: hospital for hospital in hospitals}
    decisions = []
    for evaluation in evaluations:
        hospital = hospitals_by_id[evaluation.hospital_id]
        route = calculate_route(origin, hospital)
        decisions.append(
            HospitalDecision(
                hospital_id=evaluation.hospital_id,
                name=evaluation.name,
                eligible=evaluation.eligible,
                missing_infrastructure=evaluation.missing_infrastructure,
                distance_km=route.distance_km,
                traffic_condition=route.traffic_condition,
                eta_minutes=route.eta_minutes,
                routing_source=route.routing_source,
                selected=False,
                acknowledgement_status=("NOT_REQUESTED" if evaluation.eligible else "INELIGIBLE"),
            )
        )
    return decisions

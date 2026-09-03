"""Deterministic infrastructure eligibility checks for simulated hospitals."""

from app.models.schemas import Hospital, HospitalEvaluation


def evaluate_hospitals(
    required_infrastructure: list[str], hospitals: list[Hospital]
) -> list[HospitalEvaluation]:
    """Evaluate every hospital before routing; missing infrastructure always rejects it."""
    evaluations = []
    for hospital in hospitals:
        missing_infrastructure = [
            resource
            for resource in required_infrastructure
            if not getattr(hospital.availability, resource, False)
        ]
        evaluations.append(
            HospitalEvaluation(
                hospital_id=hospital.hospital_id,
                name=hospital.name,
                eligible=not missing_infrastructure,
                missing_infrastructure=missing_infrastructure,
            )
        )
    return evaluations

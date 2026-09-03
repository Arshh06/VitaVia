"""Fictional hospital infrastructure data for the VITAVIA simulation."""

from app.models.schemas import GPSLocation, Hospital, HospitalAvailability


_HOSPITALS = (
    Hospital(
        hospital_id="HOSP001",
        name="VitaCare Medical Centre",
        location=GPSLocation(latitude=12.9780, longitude=77.6010),
        availability=HospitalAvailability(
            emergency_bed=True,
            icu=True,
            ventilator=True,
            emergency_team=True,
        ),
    ),
    Hospital(
        hospital_id="HOSP002",
        name="Metro Emergency Institute",
        location=GPSLocation(latitude=12.9648, longitude=77.6052),
        availability=HospitalAvailability(
            emergency_bed=True,
            icu=True,
            ventilator=False,
            emergency_team=True,
        ),
    ),
    Hospital(
        hospital_id="HOSP003",
        name="GreenCross Trauma Centre",
        location=GPSLocation(latitude=12.9745, longitude=77.5830),
        availability=HospitalAvailability(
            emergency_bed=True,
            icu=False,
            ventilator=True,
            emergency_team=True,
        ),
    ),
    Hospital(
        hospital_id="HOSP004",
        name="Sunrise Critical Care",
        location=GPSLocation(latitude=12.9592, longitude=77.5895),
        availability=HospitalAvailability(
            emergency_bed=False,
            icu=True,
            ventilator=True,
            emergency_team=True,
        ),
    ),
)


def get_all_hospitals() -> list[Hospital]:
    """Return copies of every fictional hospital in the simulation."""
    return [hospital.model_copy(deep=True) for hospital in _HOSPITALS]

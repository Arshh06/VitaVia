"""
Hospital Registry and Live Infrastructure Availability Management.
Provides mock in-memory hospital facilities with dynamic beds, ICU, ventilator,
and emergency doctor resources.
"""

from typing import List, Optional, Dict
from copy import deepcopy
from backend.models import Hospital, HospitalInfrastructure, GeoPoint


# Baseline simulated hospital network (Metropolitan Emergency Care Grid)
# Coordinates calibrated for downtown grid vs elevated arterial expressway
INITIAL_HOSPITALS: List[Hospital] = [
    Hospital(
        id="HOSP-A",
        name="Metro City Central Hospital",
        location=GeoPoint(latitude=12.9760, longitude=77.5730, address="MG Road Congested Downtown Grid"),
        contact_number="+91-80-2222-1001",
        trauma_level="Level 1 Comprehensive Trauma Center",
        infrastructure=HospitalInfrastructure(
            emergency_bed_available=True,
            icu_available=True,
            ventilator_available=True,
            emergency_doctor_available=True,
            total_emergency_beds=30,
            available_emergency_beds=4,
            total_icu_beds=12,
            available_icu_beds=2,
            total_ventilators=8,
            available_ventilators=2
        )
    ),
    Hospital(
        id="HOSP-B",
        name="St. Jude Super Specialty Hospital",
        location=GeoPoint(latitude=13.0080, longitude=77.6250, address="Expressway Corridor North (Arterial Green Wave)"),
        contact_number="+91-80-3333-2002",
        trauma_level="Level 1 Advanced Cardiac & Trauma Care",
        infrastructure=HospitalInfrastructure(
            emergency_bed_available=True,
            icu_available=True,
            ventilator_available=True,
            emergency_doctor_available=True,
            total_emergency_beds=25,
            available_emergency_beds=8,
            total_icu_beds=15,
            available_icu_beds=5,
            total_ventilators=10,
            available_ventilators=4
        )
    ),
    Hospital(
        id="HOSP-C",
        name="Apex Community Medical Center",
        location=GeoPoint(latitude=12.9630, longitude=77.5880, address="South Avenue Local Sector"),
        contact_number="+91-80-4444-3003",
        trauma_level="Level 3 Urgent Care Clinic",
        infrastructure=HospitalInfrastructure(
            emergency_bed_available=True,
            icu_available=False,        # ICU Full / Unavailable
            ventilator_available=False, # Ventilators Full
            emergency_doctor_available=True,
            total_emergency_beds=15,
            available_emergency_beds=3,
            total_icu_beds=4,
            available_icu_beds=0,
            total_ventilators=2,
            available_ventilators=0
        )
    ),
    Hospital(
        id="HOSP-D",
        name="Lifeline Memorial Health",
        location=GeoPoint(latitude=12.9350, longitude=77.6150, address="Ring Road Outer Belt"),
        contact_number="+91-80-5555-4004",
        trauma_level="Level 2 Regional Hospital",
        infrastructure=HospitalInfrastructure(
            emergency_bed_available=True,
            icu_available=True,
            ventilator_available=False, # Ventilator unavailable
            emergency_doctor_available=True,
            total_emergency_beds=20,
            available_emergency_beds=5,
            total_icu_beds=6,
            available_icu_beds=1,
            total_ventilators=4,
            available_ventilators=0
        )
    ),
    Hospital(
        id="HOSP-E",
        name="Grace Emergency & Trauma Institute",
        location=GeoPoint(latitude=13.0250, longitude=77.5650, address="Tech Park Arterial Bypass"),
        contact_number="+91-80-6666-5005",
        trauma_level="Level 1 Tertiary Emergency",
        infrastructure=HospitalInfrastructure(
            emergency_bed_available=True,
            icu_available=True,
            ventilator_available=True,
            emergency_doctor_available=True,
            total_emergency_beds=40,
            available_emergency_beds=12,
            total_icu_beds=20,
            available_icu_beds=7,
            total_ventilators=15,
            available_ventilators=6
        )
    )
]

# Active in-memory hospital database
_hospitals_db: Dict[str, Hospital] = {h.id: deepcopy(h) for h in INITIAL_HOSPITALS}


def get_all_hospitals() -> List[Hospital]:
    """Return all registered hospitals with current live infrastructure."""
    return list(_hospitals_db.values())


def get_hospital_by_id(hospital_id: str) -> Optional[Hospital]:
    """Lookup a hospital by ID."""
    return _hospitals_db.get(hospital_id)


def update_hospital_infrastructure(
    hospital_id: str,
    emergency_bed: Optional[bool] = None,
    icu: Optional[bool] = None,
    ventilator: Optional[bool] = None,
    doctor: Optional[bool] = None,
    available_emergency_beds: Optional[int] = None,
    available_icu_beds: Optional[int] = None,
    available_ventilators: Optional[int] = None
) -> Optional[Hospital]:
    """Dynamically update a hospital's resource availability."""
    h = _hospitals_db.get(hospital_id)
    if not h:
        return None
    
    if emergency_bed is not None:
        h.infrastructure.emergency_bed_available = emergency_bed
    if icu is not None:
        h.infrastructure.icu_available = icu
    if ventilator is not None:
        h.infrastructure.ventilator_available = ventilator
    if doctor is not None:
        h.infrastructure.emergency_doctor_available = doctor
    
    if available_emergency_beds is not None:
        h.infrastructure.available_emergency_beds = available_emergency_beds
        h.infrastructure.emergency_bed_available = available_emergency_beds > 0
        
    if available_icu_beds is not None:
        h.infrastructure.available_icu_beds = available_icu_beds
        h.infrastructure.icu_available = available_icu_beds > 0
        
    if available_ventilators is not None:
        h.infrastructure.available_ventilators = available_ventilators
        h.infrastructure.ventilator_available = available_ventilators > 0

    return h


def reset_mock_hospitals() -> List[Hospital]:
    """Reset the in-memory hospital database to the initial configuration."""
    global _hospitals_db
    _hospitals_db = {h.id: deepcopy(h) for h in INITIAL_HOSPITALS}
    return list(_hospitals_db.values())

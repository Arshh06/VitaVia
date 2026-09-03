"""SQLAlchemy ORM tables for simulated VITAVIA emergency-history data only."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EmergencyRecord(Base):
    """One persisted simulated emergency session; live state remains in memory."""

    __tablename__ = "emergency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emergency_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    ambulance_id: Mapped[str] = mapped_column(String(32), index=True)
    patient_id: Mapped[str] = mapped_column(String(32), index=True)
    emergency_type: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_hospital_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    selected_hospital_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    acknowledgement_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    triage_severity: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    triage_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    required_infrastructure: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    triage_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    routing_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    initial_eta_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class VitalReadingRecord(Base):
    """One simulated vital-sign reading saved for an emergency timeline."""

    __tablename__ = "vital_reading_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emergency_id: Mapped[str] = mapped_column(
        ForeignKey("emergency_records.emergency_id"), index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    spo2: Mapped[float] = mapped_column(Float)
    heart_rate: Mapped[int] = mapped_column(Integer)
    systolic_bp: Mapped[int] = mapped_column(Integer)
    diastolic_bp: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[float] = mapped_column(Float)


class AmbulanceLocationRecord(Base):
    """One simulated ambulance GPS and journey-state reading in the audit timeline."""

    __tablename__ = "ambulance_location_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emergency_id: Mapped[str] = mapped_column(
        ForeignKey("emergency_records.emergency_id"), index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ambulance_status: Mapped[str] = mapped_column(String(64))
    journey_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    progress_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    remaining_eta_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class HospitalEvaluationRecord(Base):
    """Latest deterministic candidate evaluation snapshot for a simulated emergency."""

    __tablename__ = "hospital_evaluation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    emergency_id: Mapped[str] = mapped_column(
        ForeignKey("emergency_records.emergency_id"), index=True
    )
    hospital_id: Mapped[str] = mapped_column(String(32))
    hospital_name: Mapped[str] = mapped_column(String(128))
    eligible: Mapped[bool] = mapped_column(Boolean)
    missing_infrastructure: Mapped[list] = mapped_column(JSON)
    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    traffic_condition: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    eta_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    routing_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean)
    acknowledgement_status: Mapped[str] = mapped_column(String(64))

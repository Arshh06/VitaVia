package com.vitavia.domain.model;

import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Emergency Mission Aggregate Root.
 * Demonstrates:
 * - Strict Encapsulation: Protects internal mission lifecycle states, coordinates, and telemetry.
 * - Enforces business state transitions: CREATED -> DISPATCHED -> ACKNOWLEDGED -> EN_ROUTE -> ARRIVED -> COMPLETED.
 */
public class EmergencyMission implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String emergencyId;
    private final String ambulanceId;
    private PatientInfo patientInfo;
    private PatientVitals currentVitals;
    private GeoPoint startLocation;
    private GeoPoint currentLocation;
    private EmergencyStatus status;

    private TriageAssessment triageAssessment;
    private Hospital selectedHospital;
    private RouteEvaluation selectedRoute;
    private HospitalAcknowledgment acknowledgment;
    private final List<RouteEvaluation> allEvaluations = new ArrayList<>();

    private double progressRatio;
    private double currentEtaMinutes;
    private final Instant startedAt;
    private Instant completedAt;
    private Instant lastUpdated;

    public EmergencyMission(String emergencyId, String ambulanceId, PatientInfo patientInfo,
                            PatientVitals initialVitals, GeoPoint startLocation) {
        this.emergencyId = Objects.requireNonNull(emergencyId, "emergencyId must not be null");
        this.ambulanceId = Objects.requireNonNull(ambulanceId, "ambulanceId must not be null");
        this.patientInfo = Objects.requireNonNull(patientInfo, "patientInfo must not be null");
        this.currentVitals = Objects.requireNonNull(initialVitals, "initialVitals must not be null");
        this.startLocation = Objects.requireNonNull(startLocation, "startLocation must not be null");
        this.currentLocation = startLocation;
        this.status = EmergencyStatus.CREATED;
        this.progressRatio = 0.0;
        this.currentEtaMinutes = 10.0;
        this.startedAt = Instant.now();
        this.lastUpdated = this.startedAt;
    }

    public synchronized void dispatchTo(Hospital hospital, RouteEvaluation route,
                                       TriageAssessment triage, HospitalAcknowledgment ack,
                                       List<RouteEvaluation> evaluations) {
        if (!status.canTransitionTo(EmergencyStatus.DISPATCHED)) {
            throw new IllegalStateException("Cannot dispatch mission from state: " + status);
        }
        this.selectedHospital = Objects.requireNonNull(hospital, "hospital must not be null");
        this.selectedRoute = Objects.requireNonNull(route, "route must not be null");
        this.triageAssessment = Objects.requireNonNull(triage, "triage must not be null");
        this.acknowledgment = ack;
        this.allEvaluations.clear();
        if (evaluations != null) {
            this.allEvaluations.addAll(evaluations);
        }
        this.currentEtaMinutes = route.getEtaMinutes();
        this.progressRatio = 0.0;
        this.status = EmergencyStatus.DISPATCHED;
        this.lastUpdated = Instant.now();
    }

    public synchronized void confirmHospitalAcknowledgment(HospitalAcknowledgment ack) {
        if (!status.canTransitionTo(EmergencyStatus.ACKNOWLEDGED) && status != EmergencyStatus.DISPATCHED && status != EmergencyStatus.EN_ROUTE) {
            throw new IllegalStateException("Cannot acknowledge mission from state: " + status);
        }
        this.acknowledgment = Objects.requireNonNull(ack, "acknowledgment must not be null");
        if (this.status == EmergencyStatus.DISPATCHED) {
            this.status = EmergencyStatus.ACKNOWLEDGED;
        }
        this.lastUpdated = Instant.now();
    }

    public synchronized void advanceTransit(double stepFraction, PatientVitals driftedVitals) {
        if (status != EmergencyStatus.DISPATCHED && status != EmergencyStatus.ACKNOWLEDGED && status != EmergencyStatus.EN_ROUTE) {
            throw new IllegalStateException("Cannot advance transit when mission is in state: " + status);
        }

        this.currentVitals = driftedVitals != null ? driftedVitals : this.currentVitals;
        this.progressRatio = Math.min(1.0, Math.round((this.progressRatio + stepFraction) * 10000.0) / 10000.0);

        if (selectedHospital != null) {
            GeoPoint dest = selectedHospital.getLocation();
            double sLat = startLocation.getLatitude();
            double sLon = startLocation.getLongitude();
            double dLat = dest.getLatitude();
            double dLon = dest.getLongitude();

            double currLat = Math.round((sLat + (dLat - sLat) * progressRatio) * 100000.0) / 100000.0;
            double currLon = Math.round((sLon + (dLon - sLon) * progressRatio) * 100000.0) / 100000.0;
            int pct = (int) (progressRatio * 100);

            if (progressRatio >= 1.0) {
                this.status = EmergencyStatus.ARRIVED;
                this.currentEtaMinutes = 0.0;
                this.currentLocation = new GeoPoint(currLat, currLon, "ARRIVED at " + selectedHospital.getName());
            } else {
                this.status = EmergencyStatus.EN_ROUTE;
                double initialEta = selectedRoute != null ? selectedRoute.getEtaMinutes() : 10.0;
                this.currentEtaMinutes = Math.round(Math.max(0.1, initialEta * (1.0 - progressRatio)) * 10.0) / 10.0;
                this.currentLocation = new GeoPoint(currLat, currLon, String.format("In Transit - %d%% to %s", pct, selectedHospital.getName()));
            }
        }
        this.lastUpdated = Instant.now();
    }

    public synchronized void completeMission() {
        if (!status.canTransitionTo(EmergencyStatus.COMPLETED)) {
            throw new IllegalStateException("Cannot complete mission from status: " + status);
        }
        this.status = EmergencyStatus.COMPLETED;
        this.completedAt = Instant.now();
        this.lastUpdated = this.completedAt;
    }

    public synchronized void updateVitalsOnly(PatientVitals vitals) {
        this.currentVitals = Objects.requireNonNull(vitals, "vitals must not be null");
        this.lastUpdated = Instant.now();
    }

    public synchronized void updatePatientInfo(PatientInfo info) {
        this.patientInfo = Objects.requireNonNull(info, "patientInfo must not be null");
        this.lastUpdated = Instant.now();
    }

    // Getters
    public String getEmergencyId() { return emergencyId; }
    public String getAmbulanceId() { return ambulanceId; }
    public synchronized PatientInfo getPatientInfo() { return patientInfo; }
    public synchronized PatientVitals getCurrentVitals() { return currentVitals; }
    public synchronized GeoPoint getStartLocation() { return startLocation; }
    public synchronized GeoPoint getCurrentLocation() { return currentLocation; }
    public synchronized EmergencyStatus getStatus() { return status; }
    public synchronized TriageAssessment getTriageAssessment() { return triageAssessment; }
    public synchronized Hospital getSelectedHospital() { return selectedHospital; }
    public synchronized RouteEvaluation getSelectedRoute() { return selectedRoute; }
    public synchronized HospitalAcknowledgment getAcknowledgment() { return acknowledgment; }
    public synchronized List<RouteEvaluation> getAllEvaluations() { return Collections.unmodifiableList(allEvaluations); }
    public synchronized double getProgressRatio() { return progressRatio; }
    public synchronized double getCurrentEtaMinutes() { return currentEtaMinutes; }
    public Instant getStartedAt() { return startedAt; }
    public synchronized Instant getCompletedAt() { return completedAt; }
    public synchronized Instant getLastUpdated() { return lastUpdated; }

    @Override
    public String toString() {
        return String.format("EmergencyMission[ID=%s, Ambulance=%s, Status=%s, Hospital=%s, ETA=%.1fm]",
                emergencyId, ambulanceId, status, selectedHospital != null ? selectedHospital.getName() : "None", currentEtaMinutes);
    }
}

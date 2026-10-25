package com.vitavia.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * JPA Entity for Persisted Emergency Sessions and Audit History.
 */
@Entity
@Table(name = "emergency_records", indexes = {
        @Index(name = "idx_emerg_id", columnList = "emergencyId"),
        @Index(name = "idx_amb_id", columnList = "ambulanceId"),
        @Index(name = "idx_hosp_id", columnList = "selectedHospitalId")
})
public class EmergencyRecordEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 64)
    private String emergencyId;

    @Column(nullable = false, length = 32)
    private String ambulanceId;

    @Column(nullable = false, length = 32)
    private String patientId;

    @Column(length = 128)
    private String patientName;

    private Integer patientAge;

    @Column(length = 32)
    private String patientGender;

    @Column(length = 512)
    private String chiefComplaint;

    @Column(nullable = false, length = 32)
    private String status;

    private Instant startedAt;
    private Instant completedAt;

    @Column(length = 32)
    private String selectedHospitalId;

    @Column(length = 128)
    private String selectedHospitalName;

    @Column(length = 64)
    private String acknowledgmentStatus;

    @Column(length = 64)
    private String acknowledgmentId;

    @Column(length = 64)
    private String assignedBay;

    private Boolean teamReady;

    @Column(length = 32)
    private String triageSeverity;

    @Column(length = 64)
    private String triageSource;

    @Column(length = 255)
    private String requiredInfrastructure;

    @Column(columnDefinition = "TEXT")
    private String triageSummary;

    @Column(length = 64)
    private String routingSource;

    private Double initialEtaMinutes;
    private Double distanceKm;

    public EmergencyRecordEntity() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getEmergencyId() { return emergencyId; }
    public void setEmergencyId(String emergencyId) { this.emergencyId = emergencyId; }

    public String getAmbulanceId() { return ambulanceId; }
    public void setAmbulanceId(String ambulanceId) { this.ambulanceId = ambulanceId; }

    public String getPatientId() { return patientId; }
    public void setPatientId(String patientId) { this.patientId = patientId; }

    public String getPatientName() { return patientName; }
    public void setPatientName(String patientName) { this.patientName = patientName; }

    public Integer getPatientAge() { return patientAge; }
    public void setPatientAge(Integer patientAge) { this.patientAge = patientAge; }

    public String getPatientGender() { return patientGender; }
    public void setPatientGender(String patientGender) { this.patientGender = patientGender; }

    public String getChiefComplaint() { return chiefComplaint; }
    public void setChiefComplaint(String chiefComplaint) { this.chiefComplaint = chiefComplaint; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Instant getStartedAt() { return startedAt; }
    public void setStartedAt(Instant startedAt) { this.startedAt = startedAt; }

    public Instant getCompletedAt() { return completedAt; }
    public void setCompletedAt(Instant completedAt) { this.completedAt = completedAt; }

    public String getSelectedHospitalId() { return selectedHospitalId; }
    public void setSelectedHospitalId(String selectedHospitalId) { this.selectedHospitalId = selectedHospitalId; }

    public String getSelectedHospitalName() { return selectedHospitalName; }
    public void setSelectedHospitalName(String selectedHospitalName) { this.selectedHospitalName = selectedHospitalName; }

    public String getAcknowledgmentStatus() { return acknowledgmentStatus; }
    public void setAcknowledgmentStatus(String acknowledgmentStatus) { this.acknowledgmentStatus = acknowledgmentStatus; }

    public String getAcknowledgmentId() { return acknowledgmentId; }
    public void setAcknowledgmentId(String acknowledgmentId) { this.acknowledgmentId = acknowledgmentId; }

    public String getAssignedBay() { return assignedBay; }
    public void setAssignedBay(String assignedBay) { this.assignedBay = assignedBay; }

    public Boolean getTeamReady() { return teamReady; }
    public void setTeamReady(Boolean teamReady) { this.teamReady = teamReady; }

    public String getTriageSeverity() { return triageSeverity; }
    public void setTriageSeverity(String triageSeverity) { this.triageSeverity = triageSeverity; }

    public String getTriageSource() { return triageSource; }
    public void setTriageSource(String triageSource) { this.triageSource = triageSource; }

    public String getRequiredInfrastructure() { return requiredInfrastructure; }
    public void setRequiredInfrastructure(String requiredInfrastructure) { this.requiredInfrastructure = requiredInfrastructure; }

    public String getTriageSummary() { return triageSummary; }
    public void setTriageSummary(String triageSummary) { this.triageSummary = triageSummary; }

    public String getRoutingSource() { return routingSource; }
    public void setRoutingSource(String routingSource) { this.routingSource = routingSource; }

    public Double getInitialEtaMinutes() { return initialEtaMinutes; }
    public void setInitialEtaMinutes(Double initialEtaMinutes) { this.initialEtaMinutes = initialEtaMinutes; }

    public Double getDistanceKm() { return distanceKm; }
    public void setDistanceKm(Double distanceKm) { this.distanceKm = distanceKm; }
}

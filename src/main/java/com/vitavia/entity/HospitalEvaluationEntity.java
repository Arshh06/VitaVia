package com.vitavia.entity;

import jakarta.persistence.*;

/**
 * JPA Entity for Evaluated Hospital Candidates per Emergency Dispatch.
 */
@Entity
@Table(name = "hospital_evaluation_records", indexes = {
        @Index(name = "idx_eval_emerg_id", columnList = "emergencyId")
})
public class HospitalEvaluationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String emergencyId;

    @Column(nullable = false, length = 32)
    private String hospitalId;

    @Column(length = 128)
    private String hospitalName;

    private Boolean eligible;

    @Column(length = 255)
    private String missingInfrastructure;

    private Double distanceKm;

    @Column(length = 32)
    private String trafficCondition;

    private Double etaMinutes;

    @Column(length = 64)
    private String routingSource;

    private Boolean selected;

    @Column(length = 255)
    private String rejectionReason;

    public HospitalEvaluationEntity() {}

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getEmergencyId() { return emergencyId; }
    public void setEmergencyId(String emergencyId) { this.emergencyId = emergencyId; }

    public String getHospitalId() { return hospitalId; }
    public void setHospitalId(String hospitalId) { this.hospitalId = hospitalId; }

    public String getHospitalName() { return hospitalName; }
    public void setHospitalName(String hospitalName) { this.hospitalName = hospitalName; }

    public Boolean getEligible() { return eligible; }
    public void setEligible(Boolean eligible) { this.eligible = eligible; }

    public String getMissingInfrastructure() { return missingInfrastructure; }
    public void setMissingInfrastructure(String missingInfrastructure) { this.missingInfrastructure = missingInfrastructure; }

    public Double getDistanceKm() { return distanceKm; }
    public void setDistanceKm(Double distanceKm) { this.distanceKm = distanceKm; }

    public String getTrafficCondition() { return trafficCondition; }
    public void setTrafficCondition(String trafficCondition) { this.trafficCondition = trafficCondition; }

    public Double getEtaMinutes() { return etaMinutes; }
    public void setEtaMinutes(Double etaMinutes) { this.etaMinutes = etaMinutes; }

    public String getRoutingSource() { return routingSource; }
    public void setRoutingSource(String routingSource) { this.routingSource = routingSource; }

    public Boolean getSelected() { return selected; }
    public void setSelected(Boolean selected) { this.selected = selected; }

    public String getRejectionReason() { return rejectionReason; }
    public void setRejectionReason(String rejectionReason) { this.rejectionReason = rejectionReason; }
}

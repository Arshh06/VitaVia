package com.vitavia.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * JPA Entity for Persisted Patient Vital Sign Readings.
 */
@Entity
@Table(name = "vital_reading_records", indexes = {
        @Index(name = "idx_vital_emerg_id", columnList = "emergencyId")
})
public class VitalReadingEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String emergencyId;

    private Instant recordedAt;
    private Double spo2;
    private Integer heartRate;
    private Integer systolicBp;
    private Integer diastolicBp;
    private Double temperature;

    public VitalReadingEntity() {}

    public VitalReadingEntity(String emergencyId, Instant recordedAt, Double spo2, Integer heartRate,
                              Integer systolicBp, Integer diastolicBp, Double temperature) {
        this.emergencyId = emergencyId;
        this.recordedAt = recordedAt;
        this.spo2 = spo2;
        this.heartRate = heartRate;
        this.systolicBp = systolicBp;
        this.diastolicBp = diastolicBp;
        this.temperature = temperature;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getEmergencyId() { return emergencyId; }
    public void setEmergencyId(String emergencyId) { this.emergencyId = emergencyId; }

    public Instant getRecordedAt() { return recordedAt; }
    public void setRecordedAt(Instant recordedAt) { this.recordedAt = recordedAt; }

    public Double getSpo2() { return spo2; }
    public void setSpo2(Double spo2) { this.spo2 = spo2; }

    public Integer getHeartRate() { return heartRate; }
    public void setHeartRate(Integer heartRate) { this.heartRate = heartRate; }

    public Integer getSystolicBp() { return systolicBp; }
    public void setSystolicBp(Integer systolicBp) { this.systolicBp = systolicBp; }

    public Integer getDiastolicBp() { return diastolicBp; }
    public void setDiastolicBp(Integer diastolicBp) { this.diastolicBp = diastolicBp; }

    public Double getTemperature() { return temperature; }
    public void setTemperature(Double temperature) { this.temperature = temperature; }
}

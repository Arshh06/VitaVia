package com.vitavia.entity;

import jakarta.persistence.*;
import java.time.Instant;

/**
 * JPA Entity for Continuous Ambulance GPS and Journey Tracking.
 */
@Entity
@Table(name = "ambulance_location_records", indexes = {
        @Index(name = "idx_loc_emerg_id", columnList = "emergencyId")
})
public class AmbulanceLocationEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 64)
    private String emergencyId;

    private Instant recordedAt;
    private Double latitude;
    private Double longitude;

    @Column(length = 255)
    private String address;

    @Column(length = 32)
    private String status;

    private Double progressPercent;
    private Double remainingEtaMinutes;

    public AmbulanceLocationEntity() {}

    public AmbulanceLocationEntity(String emergencyId, Instant recordedAt, Double latitude, Double longitude,
                                  String address, String status, Double progressPercent, Double remainingEtaMinutes) {
        this.emergencyId = emergencyId;
        this.recordedAt = recordedAt;
        this.latitude = latitude;
        this.longitude = longitude;
        this.address = address;
        this.status = status;
        this.progressPercent = progressPercent;
        this.remainingEtaMinutes = remainingEtaMinutes;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getEmergencyId() { return emergencyId; }
    public void setEmergencyId(String emergencyId) { this.emergencyId = emergencyId; }

    public Instant getRecordedAt() { return recordedAt; }
    public void setRecordedAt(Instant recordedAt) { this.recordedAt = recordedAt; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getAddress() { return address; }
    public void setAddress(String address) { this.address = address; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Double getProgressPercent() { return progressPercent; }
    public void setProgressPercent(Double progressPercent) { this.progressPercent = progressPercent; }

    public Double getRemainingEtaMinutes() { return remainingEtaMinutes; }
    public void setRemainingEtaMinutes(Double remainingEtaMinutes) { this.remainingEtaMinutes = remainingEtaMinutes; }
}

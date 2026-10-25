package com.vitavia.entity;

import jakarta.persistence.*;

/**
 * JPA Entity for Hospital Configuration & Capacity Persistence.
 */
@Entity
@Table(name = "hospitals")
public class HospitalEntity {

    @Id
    @Column(nullable = false, unique = true, length = 32)
    private String id;

    @Column(nullable = false, length = 128)
    private String name;

    private Double latitude;
    private Double longitude;

    @Column(length = 255)
    private String address;

    @Column(length = 32)
    private String contactNumber;

    @Column(length = 128)
    private String traumaLevel;

    private Integer totalEmergencyBeds;
    private Integer availableEmergencyBeds;
    private Integer totalIcuBeds;
    private Integer availableIcuBeds;
    private Integer totalVentilators;
    private Integer availableVentilators;
    private Boolean emergencyDoctorAvailable;

    public HospitalEntity() {}

    public HospitalEntity(String id, String name, Double latitude, Double longitude, String address,
                          String contactNumber, String traumaLevel, Integer totalEmergencyBeds,
                          Integer availableEmergencyBeds, Integer totalIcuBeds, Integer availableIcuBeds,
                          Integer totalVentilators, Integer availableVentilators, Boolean emergencyDoctorAvailable) {
        this.id = id;
        this.name = name;
        this.latitude = latitude;
        this.longitude = longitude;
        this.address = address;
        this.contactNumber = contactNumber;
        this.traumaLevel = traumaLevel;
        this.totalEmergencyBeds = totalEmergencyBeds;
        this.availableEmergencyBeds = availableEmergencyBeds;
        this.totalIcuBeds = totalIcuBeds;
        this.availableIcuBeds = availableIcuBeds;
        this.totalVentilators = totalVentilators;
        this.availableVentilators = availableVentilators;
        this.emergencyDoctorAvailable = emergencyDoctorAvailable;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Double getLatitude() { return latitude; }
    public void setLatitude(Double latitude) { this.latitude = latitude; }

    public Double getLongitude() { return longitude; }
    public void setLongitude(Double longitude) { this.longitude = longitude; }

    public String getAddress() { return address; }
    public void setAddress(String address) { this.address = address; }

    public String getContactNumber() { return contactNumber; }
    public void setContactNumber(String contactNumber) { this.contactNumber = contactNumber; }

    public String getTraumaLevel() { return traumaLevel; }
    public void setTraumaLevel(String traumaLevel) { this.traumaLevel = traumaLevel; }

    public Integer getTotalEmergencyBeds() { return totalEmergencyBeds; }
    public void setTotalEmergencyBeds(Integer totalEmergencyBeds) { this.totalEmergencyBeds = totalEmergencyBeds; }

    public Integer getAvailableEmergencyBeds() { return availableEmergencyBeds; }
    public void setAvailableEmergencyBeds(Integer availableEmergencyBeds) { this.availableEmergencyBeds = availableEmergencyBeds; }

    public Integer getTotalIcuBeds() { return totalIcuBeds; }
    public void setTotalIcuBeds(Integer totalIcuBeds) { this.totalIcuBeds = totalIcuBeds; }

    public Integer getAvailableIcuBeds() { return availableIcuBeds; }
    public void setAvailableIcuBeds(Integer availableIcuBeds) { this.availableIcuBeds = availableIcuBeds; }

    public Integer getTotalVentilators() { return totalVentilators; }
    public void setTotalVentilators(Integer totalVentilators) { this.totalVentilators = totalVentilators; }

    public Integer getAvailableVentilators() { return availableVentilators; }
    public void setAvailableVentilators(Integer availableVentilators) { this.availableVentilators = availableVentilators; }

    public Boolean getEmergencyDoctorAvailable() { return emergencyDoctorAvailable; }
    public void setEmergencyDoctorAvailable(Boolean emergencyDoctorAvailable) { this.emergencyDoctorAvailable = emergencyDoctorAvailable; }
}

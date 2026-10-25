package com.vitavia.domain.model;

import com.vitavia.domain.resource.BedResource;
import com.vitavia.domain.resource.MedicalResource;
import com.vitavia.domain.resource.SpecialistStaffResource;
import com.vitavia.domain.resource.VentilatorResource;

import java.io.Serializable;
import java.util.*;

/**
 * Hospital Medical Facility Domain Model.
 * Encapsulates location, infrastructure capabilities, and polymorphic medical resources.
 */
public class Hospital implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String id;
    private final String name;
    private final GeoPoint location;
    private final String contactNumber;
    private final String traumaLevel;
    private final List<MedicalResource> resources = new ArrayList<>();

    public Hospital(String id, String name, GeoPoint location, String contactNumber, String traumaLevel) {
        this.id = Objects.requireNonNull(id, "id must not be null");
        this.name = Objects.requireNonNull(name, "name must not be null");
        this.location = Objects.requireNonNull(location, "location must not be null");
        this.contactNumber = contactNumber != null ? contactNumber : "108";
        this.traumaLevel = traumaLevel != null ? traumaLevel : "Level 1 Trauma Center";
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public GeoPoint getLocation() {
        return location;
    }

    public String getContactNumber() {
        return contactNumber;
    }

    public String getTraumaLevel() {
        return traumaLevel;
    }

    public synchronized List<MedicalResource> getResources() {
        return Collections.unmodifiableList(resources);
    }

    public synchronized void addResource(MedicalResource resource) {
        if (resource != null) {
            resources.add(resource);
        }
    }

    /**
     * Checks if this hospital satisfies 100% of the patient's required clinical infrastructure.
     * @return List of missing capability names (empty if fully eligible).
     */
    public synchronized List<String> checkEligibility(List<String> requiredCapabilities) {
        List<String> missing = new ArrayList<>();
        if (requiredCapabilities == null || requiredCapabilities.isEmpty()) {
            return missing;
        }

        for (String req : requiredCapabilities) {
            String lower = req.toLowerCase();
            boolean matched = false;

            for (MedicalResource res : resources) {
                String resType = res.getResourceType().toLowerCase();
                if ((lower.contains("icu") && resType.contains("icu")) ||
                    (lower.contains("ventilator") && resType.contains("ventilator")) ||
                    ((lower.contains("bed") || lower.contains("emergency")) && !lower.contains("doctor") && resType.contains("bed")) ||
                    (lower.contains("doctor") && resType.contains("doctor"))) {

                    if (res.isAvailable()) {
                        matched = true;
                        break;
                    }
                }
            }

            if (!matched) {
                missing.add(req);
            }
        }
        return missing;
    }

    public synchronized boolean isEligibleFor(List<String> requiredCapabilities) {
        return checkEligibility(requiredCapabilities).isEmpty();
    }

    public synchronized int getAvailableBeds() {
        return resources.stream()
                .filter(r -> r instanceof BedResource && !"ICU".equalsIgnoreCase(((BedResource) r).getWardType()))
                .mapToInt(MedicalResource::getAvailableUnits)
                .sum();
    }

    public synchronized int getAvailableIcuBeds() {
        return resources.stream()
                .filter(r -> r instanceof BedResource && "ICU".equalsIgnoreCase(((BedResource) r).getWardType()))
                .mapToInt(MedicalResource::getAvailableUnits)
                .sum();
    }

    public synchronized int getAvailableVentilators() {
        return resources.stream()
                .filter(r -> r instanceof VentilatorResource)
                .mapToInt(MedicalResource::getAvailableUnits)
                .sum();
    }

    public synchronized boolean isDoctorAvailable() {
        return resources.stream()
                .filter(r -> r instanceof SpecialistStaffResource)
                .anyMatch(MedicalResource::isAvailable);
    }

    public synchronized void updateCapacity(Boolean emergencyBed, Boolean icu, Boolean ventilator, Boolean doctor,
                                           Integer availableEmergencyBeds, Integer availableIcuBeds, Integer availableVentilators) {
        for (MedicalResource r : resources) {
            if (r instanceof BedResource br) {
                if ("ICU".equalsIgnoreCase(br.getWardType())) {
                    if (availableIcuBeds != null) br.setAvailableUnits(availableIcuBeds);
                    else if (icu != null) br.setAvailableUnits(icu ? Math.max(1, br.getAvailableUnits()) : 0);
                } else {
                    if (availableEmergencyBeds != null) br.setAvailableUnits(availableEmergencyBeds);
                    else if (emergencyBed != null) br.setAvailableUnits(emergencyBed ? Math.max(1, br.getAvailableUnits()) : 0);
                }
            } else if (r instanceof VentilatorResource vr) {
                if (availableVentilators != null) vr.setAvailableUnits(availableVentilators);
                else if (ventilator != null) vr.setAvailableUnits(ventilator ? Math.max(1, vr.getAvailableUnits()) : 0);
            } else if (r instanceof SpecialistStaffResource sr) {
                if (doctor != null) sr.setAvailableUnits(doctor ? 1 : 0);
            }
        }
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Hospital hospital)) return false;
        return Objects.equals(id, hospital.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return String.format("Hospital[ID='%s', Name='%s', Trauma='%s']", id, name, traumaLevel);
    }
}

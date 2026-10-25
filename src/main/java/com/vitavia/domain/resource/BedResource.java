package com.vitavia.domain.resource;

/**
 * Concrete Bed Medical Resource (ICU Beds, Emergency Trauma Bays, Standard Beds).
 * Demonstrates:
 * - Inheritance: Extends MedicalResource.
 * - Polymorphism: Overrides allocate(), release(), and getResourceType().
 */
public class BedResource extends MedicalResource {

    private static final long serialVersionUID = 1L;

    private final String wardType; // e.g. "ICU", "TRAUMA_BAY", "EMERGENCY_BED"

    public BedResource(String resourceId, String name, int totalCapacity, int availableUnits, String wardType) {
        super(resourceId, name, totalCapacity, availableUnits);
        this.wardType = wardType != null ? wardType.toUpperCase() : "EMERGENCY_BED";
    }

    public String getWardType() {
        return wardType;
    }

    @Override
    public synchronized boolean allocate() {
        if (availableUnits > 0) {
            availableUnits--;
            return true;
        }
        return false;
    }

    @Override
    public synchronized boolean release() {
        if (availableUnits < getTotalCapacity()) {
            availableUnits++;
            return true;
        }
        return false;
    }

    @Override
    public String getResourceType() {
        return "ICU".equalsIgnoreCase(wardType) ? "ICU" : "Emergency Bed";
    }

    public void setAvailableUnits(int units) {
        if (units >= 0 && units <= getTotalCapacity()) {
            this.availableUnits = units;
        }
    }
}

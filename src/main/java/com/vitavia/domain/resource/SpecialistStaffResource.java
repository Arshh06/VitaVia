package com.vitavia.domain.resource;

/**
 * Concrete Medical Specialist Staff Resource (Emergency Physicians, Trauma Surgeons).
 * Demonstrates:
 * - Inheritance: Extends MedicalResource.
 * - Polymorphism: Overrides allocate(), release(), and getResourceType().
 */
public class SpecialistStaffResource extends MedicalResource {

    private static final long serialVersionUID = 1L;

    private final String specialty;
    private final String onCallDoctorName;
    private boolean onDuty;

    public SpecialistStaffResource(String resourceId, String name, int totalCapacity, int availableUnits,
                                   String specialty, String onCallDoctorName) {
        super(resourceId, name, totalCapacity, availableUnits);
        this.specialty = specialty != null ? specialty : "Emergency Medicine";
        this.onCallDoctorName = onCallDoctorName != null ? onCallDoctorName : "Dr. On Call";
        this.onDuty = availableUnits > 0;
    }

    public String getSpecialty() {
        return specialty;
    }

    public String getOnCallDoctorName() {
        return onCallDoctorName;
    }

    public boolean isOnDuty() {
        return onDuty;
    }

    @Override
    public synchronized boolean allocate() {
        if (availableUnits > 0) {
            availableUnits--;
            this.onDuty = availableUnits > 0;
            return true;
        }
        return false;
    }

    @Override
    public synchronized boolean release() {
        if (availableUnits < getTotalCapacity()) {
            availableUnits++;
            this.onDuty = true;
            return true;
        }
        return false;
    }

    @Override
    public String getResourceType() {
        return "Emergency Doctor";
    }

    public void setAvailableUnits(int units) {
        if (units >= 0 && units <= getTotalCapacity()) {
            this.availableUnits = units;
            this.onDuty = units > 0;
        }
    }
}

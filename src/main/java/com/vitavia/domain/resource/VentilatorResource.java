package com.vitavia.domain.resource;

/**
 * Concrete Mechanical Ventilator Medical Resource.
 * Demonstrates:
 * - Inheritance: Extends MedicalResource.
 * - Polymorphism: Overrides allocate(), release(), and getResourceType().
 */
public class VentilatorResource extends MedicalResource {

    private static final long serialVersionUID = 1L;

    private final String modelType;
    private final boolean highFlowCapable;

    public VentilatorResource(String resourceId, String name, int totalCapacity, int availableUnits,
                              String modelType, boolean highFlowCapable) {
        super(resourceId, name, totalCapacity, availableUnits);
        this.modelType = modelType != null ? modelType : "Standard Mechanical Ventilator";
        this.highFlowCapable = highFlowCapable;
    }

    public String getModelType() {
        return modelType;
    }

    public boolean isHighFlowCapable() {
        return highFlowCapable;
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
        return "Ventilator";
    }

    public void setAvailableUnits(int units) {
        if (units >= 0 && units <= getTotalCapacity()) {
            this.availableUnits = units;
        }
    }
}

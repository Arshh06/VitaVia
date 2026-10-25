package com.vitavia.domain.resource;

import java.io.Serializable;
import java.util.Objects;

/**
 * Abstract Base Class for Hospital Medical Infrastructure.
 * Demonstrates:
 * - Abstraction: Defines contract for allocating and releasing vital resources.
 * - Encapsulation: Protects internal capacity counters and availability states.
 * - Inheritance: Subclasses specialize into Bed, Ventilator, and Staff resources.
 */
public abstract class MedicalResource implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String resourceId;
    private final String name;
    private final int totalCapacity;
    protected int availableUnits;

    protected MedicalResource(String resourceId, String name, int totalCapacity, int availableUnits) {
        this.resourceId = Objects.requireNonNull(resourceId, "resourceId must not be null");
        this.name = Objects.requireNonNull(name, "name must not be null");
        if (totalCapacity < 0) {
            throw new IllegalArgumentException("Total capacity cannot be negative: " + totalCapacity);
        }
        if (availableUnits < 0 || availableUnits > totalCapacity) {
            throw new IllegalArgumentException(String.format("Available units (%d) must be between 0 and total capacity (%d)",
                    availableUnits, totalCapacity));
        }
        this.totalCapacity = totalCapacity;
        this.availableUnits = availableUnits;
    }

    public String getResourceId() {
        return resourceId;
    }

    public String getName() {
        return name;
    }

    public int getTotalCapacity() {
        return totalCapacity;
    }

    public synchronized int getAvailableUnits() {
        return availableUnits;
    }

    public synchronized boolean isAvailable() {
        return availableUnits > 0;
    }

    /**
     * Abstract Polymorphic allocation method.
     * Each subclass enforces specific domain verification before allocation.
     * @return true if successfully allocated, false otherwise.
     */
    public abstract boolean allocate();

    /**
     * Abstract Polymorphic release method.
     * @return true if successfully released back to available pool.
     */
    public abstract boolean release();

    /**
     * Discriminator for infrastructure requirement matching.
     */
    public abstract String getResourceType();

    @Override
    public String toString() {
        return String.format("%s[%s, available=%d/%d]", getResourceType(), name, availableUnits, totalCapacity);
    }
}

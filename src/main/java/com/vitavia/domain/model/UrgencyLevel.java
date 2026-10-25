package com.vitavia.domain.model;

public enum UrgencyLevel {
    CRITICAL("P1 - Immediate Resuscitation"),
    HIGH("P2 - Emergent / Rapid Intervention"),
    MODERATE("P3 - Urgent Assessment"),
    LOW("P4 - Non-Urgent / Routine");

    private final String description;

    UrgencyLevel(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }

    public String getPriorityCode() {
        return switch (this) {
            case CRITICAL -> "P1";
            case HIGH -> "P2";
            case MODERATE -> "P3";
            case LOW -> "P4";
        };
    }
}

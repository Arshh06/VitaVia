package com.vitavia.domain.model;

/**
 * Validated Emergency Lifecycle States.
 */
public enum EmergencyStatus {
    CREATED,
    DISPATCHED,
    ACKNOWLEDGED,
    EN_ROUTE,
    ARRIVED,
    COMPLETED,
    CANCELLED;

    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED;
    }

    public boolean canTransitionTo(EmergencyStatus target) {
        if (this == target) return true;
        return switch (this) {
            case CREATED -> target == DISPATCHED || target == CANCELLED;
            case DISPATCHED -> target == ACKNOWLEDGED || target == EN_ROUTE || target == CANCELLED;
            case ACKNOWLEDGED -> target == EN_ROUTE || target == ARRIVED || target == CANCELLED;
            case EN_ROUTE -> target == ARRIVED || target == CANCELLED;
            case ARRIVED -> target == COMPLETED;
            case COMPLETED, CANCELLED -> false;
        };
    }
}

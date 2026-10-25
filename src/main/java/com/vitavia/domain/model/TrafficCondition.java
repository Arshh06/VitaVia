package com.vitavia.domain.model;

public enum TrafficCondition {
    LOW(1.0, 36.0, "Smooth arterial flow / green wave"),
    MODERATE(1.25, 22.0, "Typical urban traffic flow"),
    HEAVY(1.85, 11.0, "Dense congestion / bottleneck gridlock"),
    SEVERE(2.40, 7.0, "Severe arterial blockade / accident delay");

    private final double etaMultiplier;
    private final double averageSpeedKmh;
    private final String description;

    TrafficCondition(double etaMultiplier, double averageSpeedKmh, String description) {
        this.etaMultiplier = etaMultiplier;
        this.averageSpeedKmh = averageSpeedKmh;
        this.description = description;
    }

    public double getEtaMultiplier() {
        return etaMultiplier;
    }

    public double getAverageSpeedKmh() {
        return averageSpeedKmh;
    }

    public String getDescription() {
        return description;
    }
}

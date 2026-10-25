package com.vitavia.domain.model;

import java.io.Serializable;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Encapsulated Evaluation of a Route and Facility for an emergency candidate.
 */
public class RouteEvaluation implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String hospitalId;
    private final String hospitalName;
    private final double distanceKm;
    private final TrafficCondition trafficCondition;
    private final double etaMinutes;
    private final boolean infrastructureEligible;
    private final List<String> missingInfrastructure;
    private final String rejectionReason;
    private final String routeSource;

    public RouteEvaluation(String hospitalId, String hospitalName, double distanceKm,
                           TrafficCondition trafficCondition, double etaMinutes,
                           boolean infrastructureEligible, List<String> missingInfrastructure,
                           String rejectionReason, String routeSource) {
        this.hospitalId = Objects.requireNonNull(hospitalId, "hospitalId must not be null");
        this.hospitalName = hospitalName != null ? hospitalName : hospitalId;
        this.distanceKm = Math.round(distanceKm * 100.0) / 100.0;
        this.trafficCondition = trafficCondition != null ? trafficCondition : TrafficCondition.MODERATE;
        this.etaMinutes = Math.round(etaMinutes * 10.0) / 10.0;
        this.infrastructureEligible = infrastructureEligible;
        this.missingInfrastructure = missingInfrastructure != null
                ? List.copyOf(missingInfrastructure)
                : Collections.emptyList();
        this.rejectionReason = rejectionReason;
        this.routeSource = routeSource != null ? routeSource : "MOCK_TRAFFIC_ENGINE";
    }

    public String getHospitalId() {
        return hospitalId;
    }

    public String getHospitalName() {
        return hospitalName;
    }

    public double getDistanceKm() {
        return distanceKm;
    }

    public TrafficCondition getTrafficCondition() {
        return trafficCondition;
    }

    public double getEtaMinutes() {
        return etaMinutes;
    }

    public boolean isInfrastructureEligible() {
        return infrastructureEligible;
    }

    public List<String> getMissingInfrastructure() {
        return missingInfrastructure;
    }

    public String getRejectionReason() {
        return rejectionReason;
    }

    public String getRouteSource() {
        return routeSource;
    }

    @Override
    public String toString() {
        return String.format("RouteEvaluation[hosp='%s', dist=%.1fkm, eta=%.1fmin, traffic=%s, eligible=%b]",
                hospitalName, distanceKm, etaMinutes, trafficCondition, infrastructureEligible);
    }
}

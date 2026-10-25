package com.vitavia.domain.routing;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.RouteEvaluation;
import com.vitavia.domain.model.TrafficCondition;
import org.springframework.stereotype.Component;

import java.util.Collections;
import java.util.Map;

/**
 * High-Fidelity Mock Traffic Engine Implementation.
 * Demonstrates:
 * - Polymorphism: Implements RoutingEngine with deterministic urban corridor traffic simulation.
 * - Simulates expressway speed corridors, downtown bottlenecks, and road tortuosity factors.
 */
@Component("mockTrafficRoutingEngine")
public class MockTrafficRoutingEngine implements RoutingEngine {

    public static final String PROVIDER_NAME = "MOCK_TRAFFIC_ENGINE";

    private record TrafficProfile(TrafficCondition condition, double speedKmh, double roadFactor) {}

    private static final Map<String, TrafficProfile> CORRIDOR_PROFILES = Map.of(
            "HOSP-A", new TrafficProfile(TrafficCondition.HEAVY, 11.0, 1.35),     // Downtown congested grid
            "HOSP-B", new TrafficProfile(TrafficCondition.LOW, 36.0, 1.18),       // Elevated expressway green wave
            "HOSP-C", new TrafficProfile(TrafficCondition.LOW, 20.0, 1.22),       // Local neighborhood sector
            "HOSP-D", new TrafficProfile(TrafficCondition.MODERATE, 22.0, 1.28),  // Ring road outer corridor
            "HOSP-E", new TrafficProfile(TrafficCondition.LOW, 34.0, 1.20)        // Tech park bypass
    );

    @Override
    public RouteEvaluation calculateRoute(GeoPoint origin, GeoPoint destination, String hospitalId, String hospitalName) {
        double rawDistanceKm = origin.distanceTo(destination);

        TrafficProfile profile = CORRIDOR_PROFILES.getOrDefault(
                hospitalId != null ? hospitalId.toUpperCase() : "",
                new TrafficProfile(TrafficCondition.MODERATE, 22.0, 1.25)
        );

        double roadDistanceKm = Math.round(Math.max(0.5, rawDistanceKm * profile.roadFactor()) * 100.0) / 100.0;
        double travelTimeMinutes = (roadDistanceKm / profile.speedKmh()) * 60.0;
        double etaMinutes = Math.round(Math.max(2.0, travelTimeMinutes) * 10.0) / 10.0;

        return new RouteEvaluation(
                hospitalId,
                hospitalName,
                roadDistanceKm,
                profile.condition(),
                etaMinutes,
                true,
                Collections.emptyList(),
                null,
                PROVIDER_NAME
        );
    }

    @Override
    public String getProviderName() {
        return PROVIDER_NAME;
    }
}

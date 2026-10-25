package com.vitavia.domain.routing;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.RouteEvaluation;

/**
 * Routing Engine Strategy Interface.
 * Demonstrates:
 * - Abstraction: Decouples routing calculations from physical navigation providers.
 * - Polymorphism: Swappable implementations (Google Maps Routes API vs Local High-Fidelity Mock Engine).
 */
public interface RoutingEngine {

    /**
     * Calculates traffic-aware travel time, road distance, and route feasibility.
     *
     * @param origin Starting point (Ambulance position)
     * @param destination Destination point (Hospital position)
     * @param hospitalId Unique hospital identifier for historical corridor calibration
     * @return Evaluated route metrics
     */
    RouteEvaluation calculateRoute(GeoPoint origin, GeoPoint destination, String hospitalId, String hospitalName);

    /**
     * Returns the name of the routing provider engine.
     */
    String getProviderName();
}

package com.vitavia.service;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.RouteEvaluation;
import com.vitavia.domain.routing.RoutingEngine;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

/**
 * Service encapsulating traffic-aware route computations.
 * Delegates polymorphically to the active RoutingEngine implementation.
 */
@Service
public class RoutingService {

    private final RoutingEngine routingEngine;

    public RoutingService(@Qualifier("googleMapsRoutingEngine") RoutingEngine routingEngine) {
        this.routingEngine = routingEngine;
    }

    public RouteEvaluation calculateRoute(GeoPoint origin, GeoPoint destination, String hospitalId, String hospitalName) {
        return routingEngine.calculateRoute(origin, destination, hospitalId, hospitalName);
    }

    public String getActiveEngineName() {
        return routingEngine.getProviderName();
    }
}

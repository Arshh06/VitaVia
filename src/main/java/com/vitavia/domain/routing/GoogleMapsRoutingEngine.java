package com.vitavia.domain.routing;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.RouteEvaluation;
import com.vitavia.domain.model.TrafficCondition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Collections;
import java.util.Map;

/**
 * Google Maps Routes API (Directions v2) Implementation.
 * Demonstrates:
 * - Polymorphism: Swappable implementation of RoutingEngine.
 * - Robust Fallback: Delegates to MockTrafficRoutingEngine if API key is not configured or network error occurs.
 */
@Component("googleMapsRoutingEngine")
public class GoogleMapsRoutingEngine implements RoutingEngine {

    private static final Logger logger = LoggerFactory.getLogger(GoogleMapsRoutingEngine.class);
    public static final String PROVIDER_NAME = "GOOGLE_ROUTES_API";

    private final String apiKey;
    private final MockTrafficRoutingEngine fallbackEngine;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public GoogleMapsRoutingEngine(@Value("${vitavia.google-maps.api-key:}") String apiKey,
                                   MockTrafficRoutingEngine fallbackEngine) {
        this.apiKey = apiKey != null ? apiKey.trim() : "";
        this.fallbackEngine = fallbackEngine;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(3))
                .build();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public RouteEvaluation calculateRoute(GeoPoint origin, GeoPoint destination, String hospitalId, String hospitalName) {
        if (apiKey.isEmpty()) {
            return fallbackEngine.calculateRoute(origin, destination, hospitalId, hospitalName);
        }

        try {
            String requestBody = objectMapper.writeValueAsString(Map.of(
                    "origin", Map.of("location", Map.of("latLng", Map.of(
                            "latitude", origin.getLatitude(),
                            "longitude", origin.getLongitude()))),
                    "destination", Map.of("location", Map.of("latLng", Map.of(
                            "latitude", destination.getLatitude(),
                            "longitude", destination.getLongitude()))),
                    "travelMode", "DRIVE",
                    "routingPreference", "TRAFFIC_AWARE_OPTIMAL"
            ));

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://routes.googleapis.com/directions/v2:computeRoutes"))
                    .header("Content-Type", "application/json")
                    .header("X-Goog-Api-Key", apiKey)
                    .header("X-Goog-FieldMask", "routes.duration,routes.distanceMeters,routes.staticDuration")
                    .timeout(Duration.ofSeconds(4))
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode root = objectMapper.readTree(response.body());
                JsonNode routes = root.get("routes");
                if (routes != null && routes.isArray() && !routes.isEmpty()) {
                    JsonNode primary = routes.get(0);
                    int distMeters = primary.path("distanceMeters").asInt(0);
                    double distKm = Math.round((distMeters / 1000.0) * 100.0) / 100.0;

                    String durationStr = primary.path("duration").asText("0s").replace("s", "");
                    double durationSec = Double.parseDouble(durationStr);
                    double etaMins = Math.round((durationSec / 60.0) * 10.0) / 10.0;

                    String staticStr = primary.path("staticDuration").asText(durationStr).replace("s", "");
                    double staticSec = Double.parseDouble(staticStr);

                    double ratio = staticSec > 0 ? (durationSec / staticSec) : 1.0;
                    TrafficCondition condition = (ratio >= 1.5) ? TrafficCondition.HEAVY
                            : (ratio >= 1.2) ? TrafficCondition.MODERATE : TrafficCondition.LOW;

                    return new RouteEvaluation(
                            hospitalId,
                            hospitalName,
                            distKm,
                            condition,
                            etaMins,
                            true,
                            Collections.emptyList(),
                            null,
                            PROVIDER_NAME
                    );
                }
            }
            logger.warn("Google Routes API returned non-200 code: {}. Falling back to mock engine.", response.statusCode());
        } catch (Exception exc) {
            logger.warn("Google Routes API call failed ({}: {}). Using mock fallback.", exc.getClass().getSimpleName(), exc.getMessage());
        }

        return fallbackEngine.calculateRoute(origin, destination, hospitalId, hospitalName);
    }

    @Override
    public String getProviderName() {
        return PROVIDER_NAME;
    }
}

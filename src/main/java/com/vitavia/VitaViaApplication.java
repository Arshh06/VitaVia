package com.vitavia;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * VitaVia Application Entry Point.
 * Unified Spring Boot application integrating:
 * 1. Real-time IoT ambulance simulation & telemetry ingestion
 * 2. Gemini AI clinical decision support with heuristic fallback
 * 3. Deterministic hospital infrastructure eligibility verification
 * 4. Traffic-aware fastest hospital routing optimization
 * 5. Hospital command room notification, acknowledgement & trauma bay reservation
 * 6. Live bidirectional synchronization between ambulance and hospital dashboards
 */
@SpringBootApplication
public class VitaViaApplication {

    public static void main(String[] args) {
        SpringApplication.run(VitaViaApplication.class, args);
    }
}

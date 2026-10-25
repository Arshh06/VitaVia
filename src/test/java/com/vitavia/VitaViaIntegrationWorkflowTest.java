package com.vitavia;

import com.vitavia.dto.*;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.repository.AmbulanceLocationRepository;
import com.vitavia.repository.EmergencyRecordRepository;
import com.vitavia.repository.VitalReadingRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@DisplayName("VitaVia End-to-End Closed-Loop Workflow Integration Test")
class VitaViaIntegrationWorkflowTest {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private EmergencyRecordRepository emergencyRecordRepository;

    @Autowired
    private VitalReadingRepository vitalReadingRepository;

    @Autowired
    private AmbulanceLocationRepository ambulanceLocationRepository;

    private String url(String path) {
        return "http://localhost:" + port + path;
    }

    @Test
    @DisplayName("Stage C Validation: Complete End-to-End Dispatch -> Handshake -> Transit -> Arrival Workflow")
    void testCompleteEmergencyHandshakeWorkflow() {
        // Step 1: Health check
        ResponseEntity<Map> healthResp = restTemplate.getForEntity(url("/health"), Map.class);
        assertEquals(HttpStatus.OK, healthResp.getStatusCode());
        assertEquals("ok", healthResp.getBody().get("status"));

        // Step 2: Hospital Catalog Retrieval
        ResponseEntity<List> hospResp = restTemplate.getForEntity(url("/api/v1/hospitals"), List.class);
        assertEquals(HttpStatus.OK, hospResp.getStatusCode());
        List hospitals = hospResp.getBody();
        assertNotNull(hospitals);
        assertTrue(hospitals.size() >= 5, "Must load at least 5 registered hospitals");

        // Step 3: Clinical Triage Analysis
        PatientVitalsDto criticalVitals = new PatientVitalsDto(87.5, 128, 92, 58, 38.4, null);
        ResponseEntity<Map> triageResp = restTemplate.postForEntity(url("/api/v1/analyze-vitals"),
                Map.of("vitals", criticalVitals), Map.class);
        assertEquals(HttpStatus.OK, triageResp.getStatusCode());
        assertEquals("CRITICAL", triageResp.getBody().get("urgency"));
        List<String> requiredInfra = (List<String>) triageResp.getBody().get("required_infrastructure");
        assertTrue(requiredInfra.contains("ICU"), "Critical patient must require ICU");
        assertTrue(requiredInfra.contains("Ventilator"), "Severe hypoxia must require Ventilator");

        // Step 4: Dispatch Emergency Request
        DispatchRequest dispatchReq = new DispatchRequest(
                "AMB-07",
                new PatientInfoDto("PAT-8812", "Sarah Jenkins", 58, "Female",
                        "Severe respiratory failure", "A+", "COPD", "NKDA", "+91-98765-43210"),
                criticalVitals,
                new GeoPointDto(12.9700, 77.6000, "Trinity Junction Central")
        );

        ResponseEntity<Map> dispatchResp = restTemplate.postForEntity(url("/api/v1/dispatch"), dispatchReq, Map.class);
        assertEquals(HttpStatus.OK, dispatchResp.getStatusCode());
        Map dispatchBody = dispatchResp.getBody();
        assertNotNull(dispatchBody);
        assertEquals("DISPATCHED", dispatchBody.get("status"));

        Map selection = (Map) dispatchBody.get("selection");
        Map selectedHosp = (Map) selection.get("selected_hospital");
        // Verify deterministic winning hospital is HOSP-B (St. Jude on expressway corridor)
        assertEquals("HOSP-B", selectedHosp.get("id"), "HOSP-B must win fastest feasible route");

        Map missionData = (Map) dispatchBody.get("mission");
        String emergencyId = (String) missionData.get("emergency_id");
        assertNotNull(emergencyId);

        // Step 5: Verify Hospital Inbound Alert Receipt
        ResponseEntity<Map> inboundResp = restTemplate.getForEntity(
                url("/emergency/incoming?hospital_id=HOSP-B"), Map.class);
        assertEquals(HttpStatus.OK, inboundResp.getStatusCode());
        assertTrue((Boolean) inboundResp.getBody().get("exists"));
        assertTrue((Boolean) inboundResp.getBody().get("has_active_request"));

        // Step 6: Hospital Staff Acknowledges & Confirms Readiness
        HospitalAcknowledgmentRequest ackReq = new HospitalAcknowledgmentRequest(
                "HOSP-B", "Emergency Trauma Bay #3", true, "Trauma team standing by with ventilator calibrated."
        );
        ResponseEntity<Map> ackResp = restTemplate.postForEntity(
                url("/api/v1/emergencies/" + emergencyId + "/acknowledge"), ackReq, Map.class);
        assertEquals(HttpStatus.OK, ackResp.getStatusCode());
        assertEquals("ACKNOWLEDGED", ackResp.getBody().get("status"));
        assertEquals("Emergency Trauma Bay #3", ackResp.getBody().get("assignedBay"));

        // Step 7: Advance Transit Movement (+50%)
        SimulationStepRequest stepReq = new SimulationStepRequest(0.50, "fluctuate");
        ResponseEntity<Map> stepResp = restTemplate.postForEntity(url("/api/v1/simulation/step"), stepReq, Map.class);
        assertEquals(HttpStatus.OK, stepResp.getStatusCode());
        assertEquals("EN_ROUTE", stepResp.getBody().get("status"));
        Number progress = (Number) stepResp.getBody().get("progress_percentage");
        assertTrue(progress.doubleValue() >= 49.0 && progress.doubleValue() <= 51.0);

        // Step 8: Complete Transit (+50% to Arrival)
        ResponseEntity<Map> finalStepResp = restTemplate.postForEntity(url("/api/v1/simulation/step"), stepReq, Map.class);
        assertEquals(HttpStatus.OK, finalStepResp.getStatusCode());
        assertEquals("ARRIVED", finalStepResp.getBody().get("status"));
        assertEquals(0.0, ((Number) finalStepResp.getBody().get("current_eta_minutes")).doubleValue());

        // Step 9: Hospital Staff Confirms Patient Received
        ResponseEntity<Map> completeResp = restTemplate.postForEntity(
                url("/api/v1/emergencies/" + emergencyId + "/complete?hospital_id=HOSP-B"), null, Map.class);
        assertEquals(HttpStatus.OK, completeResp.getStatusCode());
        assertEquals("COMPLETED", completeResp.getBody().get("status"));

        // Step 10: Verify Database Audit Persistence
        Optional<EmergencyRecordEntity> dbRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        assertTrue(dbRecord.isPresent(), "Emergency must be persisted in H2 database");
        assertEquals("COMPLETED", dbRecord.get().getStatus());
        assertEquals("HOSP-B", dbRecord.get().getSelectedHospitalId());
        assertEquals("Emergency Trauma Bay #3", dbRecord.get().getAssignedBay());
        assertTrue(dbRecord.get().getTeamReady());
        assertNotNull(dbRecord.get().getCompletedAt(), "completedAt timestamp must be populated");

        // Verify vital readings and GPS trace logs
        var vitalLogs = vitalReadingRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);
        assertTrue(vitalLogs.size() >= 3, "At least 3 vital readings must be saved in timeline");

        var locationLogs = ambulanceLocationRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);
        assertTrue(locationLogs.size() >= 3, "At least 3 location points must be saved in GPS trace");

        // Verify enriched telemetry endpoint
        ResponseEntity<Map> detailResp = restTemplate.getForEntity(url("/api/v1/history/emergencies/" + emergencyId), Map.class);
        assertEquals(HttpStatus.OK, detailResp.getStatusCode());
        assertNotNull(detailResp.getBody().get("vitalReadings"));
        assertNotNull(detailResp.getBody().get("locations"));
    }

    @Test
    @DisplayName("Stage C Validation: API Failure & Error Handling (404 and Fallbacks)")
    void testApiFailureAndNotFoundHandling() {
        // 1. Nonexistent emergency detail must return 404
        ResponseEntity<Map> notFoundDetail = restTemplate.getForEntity(url("/api/v1/history/emergencies/EMERG-NONEXISTENT"), Map.class);
        assertEquals(HttpStatus.NOT_FOUND, notFoundDetail.getStatusCode());

        // 2. Acknowledging nonexistent emergency must return 404
        HospitalAcknowledgmentRequest ackReq = new HospitalAcknowledgmentRequest("HOSP-A", "Bay 1", true, "Note");
        ResponseEntity<Map> notFoundAck = restTemplate.postForEntity(url("/api/v1/emergencies/EMERG-NONEXISTENT/acknowledge"), ackReq, Map.class);
        assertEquals(HttpStatus.NOT_FOUND, notFoundAck.getStatusCode());

        // 3. Completing nonexistent emergency must return 404
        ResponseEntity<Map> notFoundComplete = restTemplate.postForEntity(url("/api/v1/emergencies/EMERG-NONEXISTENT/complete"), null, Map.class);
        assertEquals(HttpStatus.NOT_FOUND, notFoundComplete.getStatusCode());

        // 4. Requesting nonexistent hospital must return 404
        ResponseEntity<Map> notFoundHospital = restTemplate.getForEntity(url("/api/v1/hospitals/HOSP-NONEXISTENT"), Map.class);
        assertEquals(HttpStatus.NOT_FOUND, notFoundHospital.getStatusCode());
    }

    @Test
    @DisplayName("Stage C Validation: Hospital Action Buttons Capacity Update & Reset")
    void testHospitalCapacityUpdateAndReset() {
        // 1. Update HOSP-B capacity via PUT
        HospitalUpdateRequest updateReq = new HospitalUpdateRequest(
                true, true, true, true, 10, 5, 4
        );
        restTemplate.put(url("/api/v1/hospitals/HOSP-B"), updateReq);

        // Verify updated capacity
        ResponseEntity<Map> updatedHospResp = restTemplate.getForEntity(url("/api/v1/hospitals/HOSP-B"), Map.class);
        assertEquals(HttpStatus.OK, updatedHospResp.getStatusCode());
        Map infra = (Map) updatedHospResp.getBody().get("infrastructure");
        assertEquals(10, ((Number) infra.get("available_emergency_beds")).intValue());
        assertEquals(5, ((Number) infra.get("available_icu_beds")).intValue());
        assertEquals(4, ((Number) infra.get("available_ventilators")).intValue());

        // 2. Reset hospitals back to default
        ResponseEntity<List> resetResp = restTemplate.postForEntity(url("/api/v1/hospitals/reset"), null, List.class);
        assertEquals(HttpStatus.OK, resetResp.getStatusCode());
        assertNotNull(resetResp.getBody());
    }
}

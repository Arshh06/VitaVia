package com.vitavia;

import com.vitavia.dto.*;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.repository.EmergencyRecordRepository;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.*;
import java.util.concurrent.*;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@DisplayName("Stage D: Edge Cases, Rerouting, Concurrency, and Validation Verification")
class StageDEdgeCasesTest {

    @LocalServerPort
    private int port;

    @Autowired
    private TestRestTemplate restTemplate;

    @Autowired
    private EmergencyRecordRepository emergencyRecordRepository;

    private String url(String path) {
        return "http://localhost:" + port + path;
    }

    @Test
    @DisplayName("Edge Case 1: Hospital Rejection and Dynamic Rerouting to Alternative Hospital")
    void testHospitalRejectionAndDynamicRerouting() {
        // Dispatch emergency where HOSP-B is initially selected
        DispatchRequest req = new DispatchRequest(
                "AMB-11",
                new PatientInfoDto("PAT-701", "Marcus Vance", 62, "Male", "Unstable Angina", "O+", "Hypertension", "NKDA", "+91-98765-43220"),
                new PatientVitalsDto(89.0, 130, 95, 60, 37.5, null),
                new GeoPointDto(12.9716, 77.5946, "City Center")
        );

        ResponseEntity<Map> dispatchResp = restTemplate.postForEntity(url("/api/v1/dispatch"), req, Map.class);
        assertEquals(HttpStatus.OK, dispatchResp.getStatusCode());
        Map mission = (Map) dispatchResp.getBody().get("mission");
        String emergencyId = (String) mission.get("emergency_id");
        Map selection = (Map) dispatchResp.getBody().get("selection");
        String initialHospitalId = (String) ((Map) selection.get("selected_hospital")).get("id");
        assertEquals("HOSP-B", initialHospitalId);

        // HOSP-B rejects and diverts incoming ambulance
        ResponseEntity<Map> rejectResp = restTemplate.postForEntity(
                url("/api/v1/emergencies/" + emergencyId + "/reject?hospital_id=HOSP-B&reason=Critical+Surge"), null, Map.class);
        assertEquals(HttpStatus.OK, rejectResp.getStatusCode());
        assertEquals("REROUTED", rejectResp.getBody().get("status"));

        String newHospitalId = (String) rejectResp.getBody().get("newHospitalId");
        assertNotNull(newHospitalId);
        assertNotEquals("HOSP-B", newHospitalId, "Rerouted hospital must NOT be the rejecting hospital");

        // Verify database reflects the rerouted hospital
        Optional<EmergencyRecordEntity> dbRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        assertTrue(dbRecord.isPresent());
        assertEquals("REROUTED", dbRecord.get().getStatus());
        assertEquals(newHospitalId, dbRecord.get().getSelectedHospitalId());
    }

    @Test
    @DisplayName("Edge Case 2: Zero Capacity Infrastructure Exclusion")
    void testZeroCapacityExclusion() {
        // Patient requiring ICU & Ventilator
        PatientVitalsDto severeVitals = new PatientVitalsDto(86.0, 135, 85, 50, 38.0, null);
        DispatchRequest req = new DispatchRequest(
                "AMB-12",
                new PatientInfoDto("PAT-702", "Elena Rostova", 49, "Female", "Acute Respiratory Distress", "A-", "Asthma", "NKDA", "+91-98765-43221"),
                severeVitals,
                new GeoPointDto(12.9630, 77.5880, "South Avenue")
        );

        ResponseEntity<Map> recResp = restTemplate.postForEntity(url("/api/v1/recommend-hospital"), req, Map.class);
        assertEquals(HttpStatus.OK, recResp.getStatusCode());

        List<Map<String, Object>> evaluations = (List<Map<String, Object>>) recResp.getBody().get("all_evaluations");
        assertNotNull(evaluations);

        // HOSP-C has 0 ICU beds and 0 ventilators in default catalog
        Optional<Map<String, Object>> hospCEval = evaluations.stream()
                .filter(e -> "HOSP-C".equals(e.get("hospitalId")))
                .findFirst();

        assertTrue(hospCEval.isPresent());
        assertFalse((Boolean) hospCEval.get().get("infrastructureEligible"), "HOSP-C with 0 ICU/Ventilators must be ineligible");
        assertNotNull(hospCEval.get().get("rejectionReason"), "Rejection reason must be documented");
    }

    @Test
    @DisplayName("Edge Case 3: Invalid Request Validation (Physiological Limits)")
    void testInvalidRequestsValidation() {
        // SpO2 > 100.0% must return 400 Bad Request
        DispatchRequest invalidSpo2Req = new DispatchRequest(
                "AMB-99",
                PatientInfoDto.defaultPatient(),
                new PatientVitalsDto(150.0, 80, 120, 80, 37.0, null),
                new GeoPointDto(12.9700, 77.6000, "Origin")
        );

        ResponseEntity<Map> resp1 = restTemplate.postForEntity(url("/api/v1/dispatch"), invalidSpo2Req, Map.class);
        assertEquals(HttpStatus.BAD_REQUEST, resp1.getStatusCode(), "Impossible SpO2 must return HTTP 400");
        assertEquals("BAD_REQUEST", resp1.getBody().get("error"));
        assertTrue(resp1.getBody().get("message").toString().contains("SpO2"));

        // Heart rate < 0 must return 400 Bad Request
        DispatchRequest negativeHrReq = new DispatchRequest(
                "AMB-99",
                PatientInfoDto.defaultPatient(),
                new PatientVitalsDto(98.0, -25, 120, 80, 37.0, null),
                new GeoPointDto(12.9700, 77.6000, "Origin")
        );

        ResponseEntity<Map> resp2 = restTemplate.postForEntity(url("/api/v1/dispatch"), negativeHrReq, Map.class);
        assertEquals(HttpStatus.BAD_REQUEST, resp2.getStatusCode(), "Negative HR must return HTTP 400");
        assertTrue(resp2.getBody().get("message").toString().contains("Heart rate"));
    }

    @Test
    @DisplayName("Edge Case 4: Duplicate Actions & State Conflict (HTTP 409)")
    void testDuplicateActionsAndStateConflict() {
        // Dispatch emergency
        DispatchRequest req = new DispatchRequest(
                "AMB-14",
                PatientInfoDto.defaultPatient(),
                new PatientVitalsDto(95.0, 90, 125, 82, 36.9, null),
                new GeoPointDto(12.9700, 77.6000, "Origin")
        );
        ResponseEntity<Map> dispatchResp = restTemplate.postForEntity(url("/api/v1/dispatch"), req, Map.class);
        String emergencyId = (String) ((Map) dispatchResp.getBody().get("mission")).get("emergency_id");

        // First completion succeeds
        ResponseEntity<Map> complete1 = restTemplate.postForEntity(
                url("/api/v1/emergencies/" + emergencyId + "/complete?hospital_id=HOSP-B"), null, Map.class);
        assertEquals(HttpStatus.OK, complete1.getStatusCode());
        assertEquals("COMPLETED", complete1.getBody().get("status"));

        // Duplicate completion must return 409 Conflict
        ResponseEntity<Map> complete2 = restTemplate.postForEntity(
                url("/api/v1/emergencies/" + emergencyId + "/complete?hospital_id=HOSP-B"), null, Map.class);
        assertEquals(HttpStatus.CONFLICT, complete2.getStatusCode(), "Duplicate completion must return HTTP 409 Conflict");
        assertEquals("CONFLICT_OR_ILLEGAL_STATE", complete2.getBody().get("error"));
    }

    @Test
    @DisplayName("Edge Case 5: Concurrent Emergencies Handling (No Data Races)")
    void testConcurrentEmergencies() throws InterruptedException, ExecutionException {
        int threads = 5;
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        List<Callable<ResponseEntity<Map>>> tasks = new ArrayList<>();

        for (int i = 1; i <= threads; i++) {
            final int idx = i;
            tasks.add(() -> {
                DispatchRequest req = new DispatchRequest(
                        "AMB-" + (20 + idx),
                        new PatientInfoDto("PAT-" + (800 + idx), "Patient " + idx, 45 + idx, "Male", "Concurrent Emergency " + idx, "B+", "None", "NKDA", "+91-99999-0000" + idx),
                        new PatientVitalsDto(92.0 + (idx % 4), 110 + idx, 130, 85, 37.0, null),
                        new GeoPointDto(12.9700 + (idx * 0.005), 77.6000 + (idx * 0.005), "Sector " + idx)
                );
                return restTemplate.postForEntity(url("/api/v1/dispatch"), req, Map.class);
            });
        }

        List<Future<ResponseEntity<Map>>> futures = executor.invokeAll(tasks);
        Set<String> generatedEmergencyIds = new HashSet<>();

        for (Future<ResponseEntity<Map>> f : futures) {
            ResponseEntity<Map> resp = f.get();
            assertEquals(HttpStatus.OK, resp.getStatusCode());
            Map mission = (Map) resp.getBody().get("mission");
            String emergencyId = (String) mission.get("emergency_id");
            assertNotNull(emergencyId);
            assertTrue(generatedEmergencyIds.add(emergencyId), "Each concurrent emergency must generate a distinct UUID ID");
        }

        executor.shutdown();
        assertEquals(threads, generatedEmergencyIds.size());
    }
}

package com.vitavia.controller;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.service.ClinicalTriageService;
import com.vitavia.service.EmergencyDispatchService;
import com.vitavia.service.HospitalNotificationService;
import com.vitavia.service.RoutingService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * Hospital Notification and Status API Controller.
 * Provides backwards-compatible endpoints matching the hospital frontend expectations,
 * backed by live relational persistence and real-time event broadcasting.
 */
@RestController
@CrossOrigin(origins = "*")
public class HospitalNotificationApiController {

    private final HospitalNotificationService notificationService;
    private final EmergencyDispatchService dispatchService;
    private final ClinicalTriageService triageService;
    private final RoutingService routingService;

    public HospitalNotificationApiController(HospitalNotificationService notificationService,
                                            EmergencyDispatchService dispatchService,
                                            ClinicalTriageService triageService,
                                            RoutingService routingService) {
        this.notificationService = notificationService;
        this.dispatchService = dispatchService;
        this.triageService = triageService;
        this.routingService = routingService;
    }

    @PostMapping({"/emergency/incoming", "/api/v1/emergency/incoming"})
    public ResponseEntity<Map<String, Object>> receiveIncomingEmergency(@RequestBody Map<String, Object> body) {
        String ambulanceId = Objects.toString(body.get("ambulance_id"), "AMB-07");
        String patientId = Objects.toString(body.get("patient_id"), "PAT-101");
        String patientName = Objects.toString(body.get("patient_name"), "Emergency Patient");
        int age = body.containsKey("age") ? ((Number) body.get("age")).intValue() : 45;
        String gender = Objects.toString(body.get("gender"), "Unknown");
        String complaint = Objects.toString(body.get("chief_complaint"), "Acute distress");

        PatientInfo patient = new PatientInfo(
                patientId, patientName, age, gender, complaint,
                Objects.toString(body.get("blood_group"), "Unknown"),
                Objects.toString(body.get("medical_history"), "None"),
                Objects.toString(body.get("allergies"), "NKDA"),
                Objects.toString(body.get("emergency_contact"), "Not provided")
        );

        PatientVitals vitals = new PatientVitals(
                toDouble(body.get("spo2"), 98.0),
                toInt(body.get("heart_rate"), 75),
                toInt(body.get("systolic_bp"), 120),
                toInt(body.get("diastolic_bp"), 80),
                toDouble(body.get("temperature"), 37.0)
        );

        GeoPoint location = new GeoPoint(
                toDouble(body.get("ambulance_latitude"), 12.9700),
                toDouble(body.get("ambulance_longitude"), 77.6000),
                Objects.toString(body.get("dispatch_origin"), "Ambulance Origin")
        );

        var dispatchResult = dispatchService.dispatch(location, vitals, patient, ambulanceId);

        return ResponseEntity.ok(Map.of(
                "exists", true,
                "has_active_request", true,
                "selected_hospital_id", dispatchResult.selectedHospital() != null ? dispatchResult.selectedHospital().getId() : "",
                "incoming_request", body,
                "received_at", new Date().toString()
        ));
    }

    @GetMapping({"/emergency/incoming", "/api/v1/emergency/incoming"})
    public ResponseEntity<Map<String, Object>> getIncomingEmergency(
            @RequestParam(value = "hospital_id", required = false) String hospitalId) {

        Optional<EmergencyRecordEntity> optRecord = notificationService.getLatestIncomingForHospital(hospitalId);

        if (optRecord.isEmpty()) {
            return ResponseEntity.ok(Map.of(
                    "exists", false,
                    "has_active_request", false
            ));
        }

        EmergencyRecordEntity record = optRecord.get();
        boolean matchesHospital = hospitalId == null || hospitalId.isBlank()
                || hospitalId.equalsIgnoreCase(record.getSelectedHospitalId())
                || toHospitalId(hospitalId).equalsIgnoreCase(record.getSelectedHospitalId());

        Map<String, Object> requestPayload = new LinkedHashMap<>();
        requestPayload.put("ambulance_id", record.getAmbulanceId());
        requestPayload.put("patient_id", record.getPatientId());
        requestPayload.put("patient_name", record.getPatientName() != null ? record.getPatientName() : "Emergency Patient");
        requestPayload.put("age", record.getPatientAge() != null ? record.getPatientAge() : 50);
        requestPayload.put("gender", record.getPatientGender() != null ? record.getPatientGender() : "Unknown");
        requestPayload.put("chief_complaint", record.getChiefComplaint() != null ? record.getChiefComplaint() : "Acute distress");
        requestPayload.put("selected_hospital_id", record.getSelectedHospitalId() != null ? record.getSelectedHospitalId() : "");
        requestPayload.put("selected_hospital_name", record.getSelectedHospitalName() != null ? record.getSelectedHospitalName() : "");
        requestPayload.put("triage_level", record.getTriageSeverity() != null ? record.getTriageSeverity() : "HIGH");
        requestPayload.put("triage_summary", record.getTriageSummary() != null ? record.getTriageSummary() : "");
        requestPayload.put("eta_minutes", record.getInitialEtaMinutes() != null ? record.getInitialEtaMinutes() : 10.0);
        requestPayload.put("distance_km", record.getDistanceKm() != null ? record.getDistanceKm() : 5.0);
        requestPayload.put("assigned_bay", record.getAssignedBay() != null ? record.getAssignedBay() : "Trauma Bay #1");
        requestPayload.put("team_ready", record.getTeamReady() != null ? record.getTeamReady() : true);
        requestPayload.put("acknowledgment_id", record.getAcknowledgmentId() != null ? record.getAcknowledgmentId() : "");
        requestPayload.put("acknowledgment_status", record.getAcknowledgmentStatus() != null ? record.getAcknowledgmentStatus() : "ACCEPTED");
        requestPayload.put("priority_code", "CRITICAL".equalsIgnoreCase(record.getTriageSeverity()) ? "P1" : ("HIGH".equalsIgnoreCase(record.getTriageSeverity()) ? "P2" : "P3"));
        requestPayload.put("status", record.getStatus());

        return ResponseEntity.ok(Map.of(
                "exists", matchesHospital,
                "has_active_request", true,
                "selected_hospital_id", record.getSelectedHospitalId() != null ? record.getSelectedHospitalId() : "",
                "incoming_request", matchesHospital ? requestPayload : Collections.emptyMap(),
                "received_at", record.getStartedAt() != null ? record.getStartedAt().toString() : new Date().toString()
        ));
    }

    @GetMapping("/ai/status")
    public Map<String, Object> getAiStatus() {
        return Map.of(
                "gemini_configured", !triageService.getActiveAssessorName().equals("HEURISTIC_FALLBACK"),
                "mode", triageService.getActiveAssessorName()
        );
    }

    @GetMapping("/routing/status")
    public Map<String, Object> getRoutingStatus() {
        return Map.of(
                "google_maps_configured", routingService.getActiveEngineName().equals("GOOGLE_ROUTES_API"),
                "active_mode", routingService.getActiveEngineName()
        );
    }

    @GetMapping("/database/status")
    public Map<String, Object> getDatabaseStatus() {
        return Map.of(
                "database", "H2 JPA Relational Database",
                "configured", true,
                "status", "ready"
        );
    }

    private String toHospitalId(String legacyId) {
        return switch (legacyId) {
            case "HOSP001" -> "HOSP-A";
            case "HOSP002" -> "HOSP-B";
            case "HOSP003" -> "HOSP-C";
            case "HOSP004" -> "HOSP-D";
            case "HOSP005" -> "HOSP-E";
            default -> legacyId;
        };
    }

    private double toDouble(Object obj, double fallback) {
        if (obj instanceof Number n) return n.doubleValue();
        if (obj != null) {
            try { return Double.parseDouble(obj.toString()); } catch (Exception ignored) {}
        }
        return fallback;
    }

    private int toInt(Object obj, int fallback) {
        if (obj instanceof Number n) return n.intValue();
        if (obj != null) {
            try { return Integer.parseInt(obj.toString()); } catch (Exception ignored) {}
        }
        return fallback;
    }
}

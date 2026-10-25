package com.vitavia.controller;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.domain.model.TriageAssessment;
import com.vitavia.dto.DispatchRequest;
import com.vitavia.dto.HospitalAcknowledgmentRequest;
import com.vitavia.dto.PatientInfoDto;
import com.vitavia.dto.PatientVitalsDto;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.service.AmbulanceSimulationService;
import com.vitavia.service.ClinicalTriageService;
import com.vitavia.service.EmergencyDispatchService;
import com.vitavia.service.HospitalNotificationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@CrossOrigin(origins = "*")
public class EmergencyApiController {

    private final EmergencyDispatchService dispatchService;
    private final ClinicalTriageService triageService;
    private final AmbulanceSimulationService simulationService;
    private final HospitalNotificationService notificationService;

    public EmergencyApiController(EmergencyDispatchService dispatchService,
                                  ClinicalTriageService triageService,
                                  AmbulanceSimulationService simulationService,
                                  HospitalNotificationService notificationService) {
        this.dispatchService = dispatchService;
        this.triageService = triageService;
        this.simulationService = simulationService;
        this.notificationService = notificationService;
    }

    @GetMapping("/")
    public Map<String, Object> root() {
        return Map.of(
                "system", "VitaVia Emergency Dispatch API (Spring Boot)",
                "status", "OPERATIONAL",
                "version", "2.0.0-Java",
                "docs_url", "/api/v1/health"
        );
    }

    @GetMapping({"/health", "/api/v1/health"})
    public Map<String, Object> health() {
        return Map.of(
                "status", "ok",
                "service", "VitaVia Unified Spring Boot Backend",
                "database", "H2 JPA",
                "ai_mode", triageService.getActiveAssessorName()
        );
    }

    @PostMapping({"/api/v1/dispatch", "/api/dispatch"})
    public ResponseEntity<Map<String, Object>> dispatchEmergency(@RequestBody DispatchRequest request) {
        PatientVitals vitals = parseVitals(request.vitals());
        PatientInfo patient = parsePatient(request.patientInfo());
        GeoPoint location = (request.location() != null && request.location().latitude() != null && request.location().longitude() != null)
                ? new GeoPoint(request.location().latitude(), request.location().longitude(), request.location().address())
                : AmbulanceSimulationService.DEFAULT_DISPATCH_ORIGIN;
        String ambulanceId = (request.ambulanceId() != null && !request.ambulanceId().isBlank())
                ? request.ambulanceId()
                : "AMB-07";

        var result = dispatchService.dispatch(location, vitals, patient, ambulanceId);
        simulationService.setActiveMission(result.mission());

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "DISPATCHED");
        response.put("decision_summary", result.decisionSummary());
        response.put("selection", Map.of(
                "selected_hospital", formatHospital(result.selectedHospital()),
                "selected_route", result.selectedRoute(),
                "gemini_analysis", Map.of(
                        "urgency", result.triageAssessment().getUrgency().name(),
                        "required_infrastructure", result.triageAssessment().getRequiredInfrastructure(),
                        "summary", result.triageAssessment().getSummary(),
                        "clinical_notes", result.triageAssessment().getClinicalNotes(),
                        "source", result.triageAssessment().getSource()
                ),
                "all_evaluations", result.allEvaluations(),
                "decision_summary", result.decisionSummary()
        ));
        response.put("acknowledgment", result.acknowledgment());
        response.put("mission", Map.of(
                "emergency_id", result.mission().getEmergencyId(),
                "ambulance_id", result.mission().getAmbulanceId(),
                "status", result.mission().getStatus().name(),
                "current_eta_minutes", result.mission().getCurrentEtaMinutes(),
                "progress_percentage", result.mission().getProgressRatio() * 100.0
        ));

        return ResponseEntity.ok(response);
    }

    @PostMapping({"/api/v1/recommend-hospital", "/api/recommend-hospital"})
    public ResponseEntity<Map<String, Object>> recommendHospital(@RequestBody DispatchRequest request) {
        PatientVitals vitals = parseVitals(request.vitals());
        PatientInfo patient = parsePatient(request.patientInfo());
        GeoPoint location = (request.location() != null && request.location().latitude() != null)
                ? new GeoPoint(request.location().latitude(), request.location().longitude(), request.location().address())
                : AmbulanceSimulationService.DEFAULT_DISPATCH_ORIGIN;
        String ambulanceId = request.ambulanceId() != null ? request.ambulanceId() : "AMB-07";

        var result = dispatchService.evaluateOptions(location, vitals, patient, ambulanceId);

        return ResponseEntity.ok(Map.of(
                "selected_hospital", formatHospital(result.selectedHospital()),
                "selected_route", result.selectedRoute(),
                "gemini_analysis", Map.of(
                        "urgency", result.triageAssessment().getUrgency().name(),
                        "required_infrastructure", result.triageAssessment().getRequiredInfrastructure(),
                        "summary", result.triageAssessment().getSummary(),
                        "source", result.triageAssessment().getSource()
                ),
                "all_evaluations", result.allEvaluations(),
                "decision_summary", result.decisionSummary()
        ));
    }

    @PostMapping({"/api/v1/analyze-vitals", "/api/analyze-vitals", "/analysis"})
    public ResponseEntity<Map<String, Object>> analyzeVitals(@RequestBody Map<String, Object> body) {
        PatientVitals vitals;
        if (body.containsKey("vitals")) {
            @SuppressWarnings("unchecked")
            Map<String, Object> vMap = (Map<String, Object>) body.get("vitals");
            vitals = new PatientVitals(
                    toDouble(vMap.get("spo2"), 98.0),
                    toInt(vMap.get("heart_rate"), 75),
                    toInt(vMap.get("systolic_bp"), 120),
                    toInt(vMap.get("diastolic_bp"), 80),
                    toDouble(vMap.get("temperature"), 37.0)
            );
        } else {
            vitals = new PatientVitals(
                    toDouble(body.get("spo2"), 98.0),
                    toInt(body.get("heart_rate"), 75),
                    toInt(body.get("systolic_bp"), 120),
                    toInt(body.get("diastolic_bp"), 80),
                    toDouble(body.get("temperature"), 37.0)
            );
        }

        TriageAssessment triage = triageService.assessPatient(vitals, null);
        return ResponseEntity.ok(Map.of(
                "urgency", triage.getUrgency().name(),
                "severity", triage.getUrgency().name(),
                "required_infrastructure", triage.getRequiredInfrastructure(),
                "summary", triage.getSummary(),
                "explanation", triage.getSummary(),
                "clinical_notes", triage.getClinicalNotes(),
                "source", triage.getSource()
        ));
    }

    @PostMapping("/api/v1/emergencies/{id}/acknowledge")
    public ResponseEntity<?> acknowledgeEmergency(@PathVariable("id") String emergencyId,
                                                  @RequestBody(required = false) HospitalAcknowledgmentRequest req) {
        String hospitalId = req != null ? req.hospitalId() : null;
        String assignedBay = req != null ? req.assignedBay() : "Trauma Bay #1";
        boolean teamReady = req == null || req.teamReady() == null || req.teamReady();
        String notes = req != null ? req.notes() : "Trauma team standing by";

        Optional<EmergencyRecordEntity> updated = notificationService.acknowledgeEmergency(emergencyId, hospitalId, assignedBay, teamReady, notes);
        if (updated.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(Map.of(
                "status", "ACKNOWLEDGED",
                "emergencyId", emergencyId,
                "assignedBay", updated.get().getAssignedBay(),
                "teamReady", updated.get().getTeamReady()
        ));
    }

    @PostMapping("/api/v1/emergencies/{id}/complete")
    public ResponseEntity<?> completeEmergency(@PathVariable("id") String emergencyId,
                                               @RequestParam(value = "hospital_id", required = false) String hospitalId) {
        Optional<EmergencyRecordEntity> updated = notificationService.markPatientReceived(emergencyId, hospitalId);
        if (updated.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(Map.of(
                "status", "COMPLETED",
                "emergencyId", emergencyId,
                "completedAt", updated.get().getCompletedAt().toString()
        ));
    }

    @PostMapping("/api/v1/emergencies/{id}/reject")
    public ResponseEntity<?> rejectAndRerouteEmergency(@PathVariable("id") String emergencyId,
                                                      @RequestParam(value = "hospital_id", required = false) String hospitalId,
                                                      @RequestParam(value = "reason", defaultValue = "Capacity Saturated") String reason) {
        var optResult = dispatchService.rerouteEmergency(emergencyId, hospitalId, reason);
        if (optResult.isEmpty()) {
            return ResponseEntity.ok(Map.of(
                    "status", "DIVERSION_FAILED",
                    "message", "No alternative hospital with available capacity found",
                    "emergencyId", emergencyId
            ));
        }
        var result = optResult.get();
        return ResponseEntity.ok(Map.of(
                "status", "REROUTED",
                "emergencyId", emergencyId,
                "previousHospitalId", hospitalId != null ? hospitalId : "",
                "newHospitalId", result.selectedHospital() != null ? result.selectedHospital().getId() : "",
                "newHospitalName", result.selectedHospital() != null ? result.selectedHospital().getName() : "",
                "etaMinutes", result.selectedRoute() != null ? result.selectedRoute().getEtaMinutes() : 0.0,
                "decisionSummary", result.decisionSummary()
        ));
    }

    @GetMapping({"/api/v1/history/emergencies", "/history/emergencies"})
    public ResponseEntity<List<EmergencyRecordEntity>> getEmergencyHistory(@RequestParam(value = "limit", defaultValue = "20") int limit) {
        return ResponseEntity.ok(dispatchService.getRecentHistory(limit));
    }

    @GetMapping({"/api/v1/history/emergencies/{id}", "/history/emergencies/{id}"})
    public ResponseEntity<?> getEmergencyDetail(@PathVariable("id") String emergencyId) {
        Map<String, Object> details = dispatchService.getEmergencyDetailsWithTelemetry(emergencyId);
        if (details.isEmpty()) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(details);
    }

    private PatientVitals parseVitals(PatientVitalsDto dto) {
        if (dto == null) {
            return new PatientVitals(88.0, 125, 90, 60, 38.2);
        }
        return new PatientVitals(
                dto.spo2() != null ? dto.spo2() : 98.0,
                dto.heart_rate() != null ? dto.heart_rate() : 75,
                dto.systolic_bp() != null ? dto.systolic_bp() : 120,
                dto.diastolic_bp() != null ? dto.diastolic_bp() : 80,
                dto.temperature() != null ? dto.temperature() : 37.0
        );
    }

    private PatientInfo parsePatient(PatientInfoDto dto) {
        if (dto == null) {
            return PatientInfo.defaultPatient();
        }
        return new PatientInfo(
                dto.patient_id() != null ? dto.patient_id() : "PAT-101",
                dto.name() != null ? dto.name() : "Emergency Patient",
                dto.age() != null ? dto.age() : 45,
                dto.gender() != null ? dto.gender() : "Unknown",
                dto.chief_complaint() != null ? dto.chief_complaint() : "Acute Emergency",
                dto.blood_group(), dto.medical_history(), dto.allergies(), dto.emergency_contact()
        );
    }

    private Map<String, Object> formatHospital(com.vitavia.domain.model.Hospital h) {
        if (h == null) return Collections.emptyMap();
        return Map.of(
                "id", h.getId(),
                "name", h.getName(),
                "location", Map.of(
                        "latitude", h.getLocation().getLatitude(),
                        "longitude", h.getLocation().getLongitude(),
                        "address", h.getLocation().getAddress()
                ),
                "infrastructure", Map.of(
                        "emergency_bed_available", h.getAvailableBeds() > 0,
                        "icu_available", h.getAvailableIcuBeds() > 0,
                        "ventilator_available", h.getAvailableVentilators() > 0,
                        "emergency_doctor_available", h.isDoctorAvailable(),
                        "available_emergency_beds", h.getAvailableBeds(),
                        "available_icu_beds", h.getAvailableIcuBeds(),
                        "available_ventilators", h.getAvailableVentilators()
                ),
                "contact_number", h.getContactNumber(),
                "trauma_level", h.getTraumaLevel()
        );
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

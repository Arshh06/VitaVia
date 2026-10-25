package com.vitavia.controller;

import com.vitavia.domain.model.EmergencyMission;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.dto.SimulationStepRequest;
import com.vitavia.service.AmbulanceSimulationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

@RestController
@CrossOrigin(origins = "*")
public class SimulationApiController {

    private final AmbulanceSimulationService simulationService;

    public SimulationApiController(AmbulanceSimulationService simulationService) {
        this.simulationService = simulationService;
    }

    @GetMapping({"/api/v1/simulation/snapshot", "/simulation/snapshot", "/api/telemetry"})
    public Map<String, Object> getSnapshot() {
        EmergencyMission mission = simulationService.getActiveMission();
        return formatMissionState(mission);
    }

    @PostMapping({"/api/v1/simulation/step", "/api/v1/simulation/update", "/simulation/update"})
    public Map<String, Object> stepSimulation(@RequestBody(required = false) SimulationStepRequest request) {
        double stepFraction = (request != null && request.stepFraction() != null) ? request.stepFraction() : 0.10;
        String trend = (request != null && request.trend() != null) ? request.trend() : "fluctuate";
        EmergencyMission updated = simulationService.stepSimulation(stepFraction, trend);
        return formatMissionState(updated);
    }

    @PostMapping({"/api/v1/simulation/vitals", "/simulation/vitals"})
    public Map<String, Object> updateVitalsOnly(@RequestBody(required = false) Map<String, Object> vitalsMap) {
        PatientVitals vitals;
        if (vitalsMap != null && vitalsMap.containsKey("spo2")) {
            vitals = new PatientVitals(
                    ((Number) vitalsMap.get("spo2")).doubleValue(),
                    ((Number) vitalsMap.get("heart_rate")).intValue(),
                    ((Number) vitalsMap.get("systolic_bp")).intValue(),
                    ((Number) vitalsMap.get("diastolic_bp")).intValue(),
                    ((Number) vitalsMap.get("temperature")).doubleValue()
            );
            simulationService.getActiveMission().updateVitalsOnly(vitals);
        } else {
            vitals = simulationService.fluctuateVitalsOnly();
        }
        return formatMissionState(simulationService.getActiveMission());
    }

    @PostMapping({"/api/v1/simulation/reset", "/simulation/reset"})
    public Map<String, Object> resetSimulation() {
        simulationService.resetToScenario(simulationService.getActiveScenarioKey());
        return formatMissionState(simulationService.getActiveMission());
    }

    @PostMapping("/api/v1/simulation/scenario/{key}")
    public Map<String, Object> selectScenario(@PathVariable("key") String scenarioKey) {
        simulationService.resetToScenario(scenarioKey);
        return formatMissionState(simulationService.getActiveMission());
    }

    @GetMapping("/api/v1/simulation/scenarios")
    public Map<String, Object> listScenarios() {
        Map<String, Object> result = new LinkedHashMap<>();
        for (var entry : simulationService.getPresetScenarios().entrySet()) {
            var s = entry.getValue();
            result.put(s.key(), Map.of(
                    "description", s.description(),
                    "patient", Map.of(
                            "patient_id", s.patient().getPatientId(),
                            "name", s.patient().getName(),
                            "age", s.patient().getAge(),
                            "gender", s.patient().getGender(),
                            "chief_complaint", s.patient().getChiefComplaint()
                    ),
                    "vitals", Map.of(
                            "spo2", s.vitals().getSpo2(),
                            "heart_rate", s.vitals().getHeartRate(),
                            "systolic_bp", s.vitals().getSystolicBp(),
                            "diastolic_bp", s.vitals().getDiastolicBp(),
                            "temperature", s.vitals().getTemperature()
                    )
            ));
        }
        return result;
    }

    @PostMapping("/api/telemetry/update")
    public ResponseEntity<Map<String, Object>> updateTelemetryDirect(@RequestBody Map<String, Object> body) {
        EmergencyMission mission = simulationService.getActiveMission();
        if (body.containsKey("status")) {
            // Echo back state
        }
        return ResponseEntity.ok(formatMissionState(mission));
    }

    // Backwards compatibility for journey endpoints
    @GetMapping({"/api/v1/journey/status", "/journey/status"})
    public Map<String, Object> getJourneyStatus() {
        EmergencyMission mission = simulationService.getActiveMission();
        return Map.of(
                "active", mission.getStatus().name().equals("EN_ROUTE") || mission.getStatus().name().equals("DISPATCHED"),
                "status", mission.getStatus().name(),
                "progress_percent", mission.getProgressRatio() * 100.0,
                "remaining_eta_minutes", mission.getCurrentEtaMinutes(),
                "current_location", Map.of(
                        "latitude", mission.getCurrentLocation().getLatitude(),
                        "longitude", mission.getCurrentLocation().getLongitude()
                ),
                "selected_hospital_id", mission.getSelectedHospital() != null ? mission.getSelectedHospital().getId() : "HOSP-B",
                "selected_hospital_name", mission.getSelectedHospital() != null ? mission.getSelectedHospital().getName() : "St. Jude Super Specialty Hospital"
        );
    }

    private Map<String, Object> formatMissionState(EmergencyMission m) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("ambulance_id", m.getAmbulanceId());
        data.put("status", m.getStatus().name());
        data.put("current_eta_minutes", m.getCurrentEtaMinutes());
        data.put("progress_percentage", m.getProgressRatio() * 100.0);
        data.put("progress_ratio", m.getProgressRatio());

        data.put("patient_info", Map.of(
                "patient_id", m.getPatientInfo().getPatientId(),
                "name", m.getPatientInfo().getName(),
                "age", m.getPatientInfo().getAge(),
                "gender", m.getPatientInfo().getGender(),
                "chief_complaint", m.getPatientInfo().getChiefComplaint()
        ));

        // Compatible with both schemas: patient object directly
        data.put("patient", Map.of(
                "patient_id", m.getPatientInfo().getPatientId(),
                "age", m.getPatientInfo().getAge(),
                "gender", m.getPatientInfo().getGender(),
                "emergency_type", m.getPatientInfo().getChiefComplaint()
        ));

        // Compatible with both schemas: ambulance object directly
        data.put("ambulance", Map.of(
                "ambulance_id", m.getAmbulanceId(),
                "status", m.getStatus().name(),
                "location", Map.of(
                        "latitude", m.getCurrentLocation().getLatitude(),
                        "longitude", m.getCurrentLocation().getLongitude()
                )
        ));

        data.put("current_vitals", Map.of(
                "spo2", m.getCurrentVitals().getSpo2(),
                "heart_rate", m.getCurrentVitals().getHeartRate(),
                "systolic_bp", m.getCurrentVitals().getSystolicBp(),
                "diastolic_bp", m.getCurrentVitals().getDiastolicBp(),
                "temperature", m.getCurrentVitals().getTemperature(),
                "recorded_at", m.getCurrentVitals().getRecordedAt().toString()
        ));
        data.put("vitals", data.get("current_vitals"));

        data.put("current_location", Map.of(
                "latitude", m.getCurrentLocation().getLatitude(),
                "longitude", m.getCurrentLocation().getLongitude(),
                "address", m.getCurrentLocation().getAddress()
        ));

        if (m.getSelectedHospital() != null) {
            data.put("destination_hospital_id", m.getSelectedHospital().getId());
            data.put("destination_hospital_name", m.getSelectedHospital().getName());
        }
        if (m.getAcknowledgment() != null) {
            data.put("acknowledgment", m.getAcknowledgment());
        }

        data.put("last_updated", m.getLastUpdated().toString());
        return data;
    }
}

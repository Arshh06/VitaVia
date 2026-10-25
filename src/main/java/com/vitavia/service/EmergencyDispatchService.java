package com.vitavia.service;

import com.vitavia.domain.model.*;
import com.vitavia.entity.*;
import com.vitavia.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;

/**
 * Core Emergency Dispatch & Fastest-Suitable Hospital Selection Engine.
 * Integrates:
 * 1. AI Clinical Decision Support (Gemini / Heuristic)
 * 2. Deterministic Hospital Infrastructure Eligibility Check
 * 3. Traffic-Aware Routing Engine (Google Routes / Mock Traffic)
 * 4. Hospital Handshake Acknowledgment & Trauma Bay Reservation
 * 5. Database Persistence & Real-time Event Streaming
 */
@Service
public class EmergencyDispatchService {

    private static final Logger logger = LoggerFactory.getLogger(EmergencyDispatchService.class);

    private final HospitalService hospitalService;
    private final ClinicalTriageService triageService;
    private final RoutingService routingService;
    private final RealtimeEventService eventService;

    private final EmergencyRecordRepository emergencyRecordRepository;
    private final VitalReadingRepository vitalReadingRepository;
    private final AmbulanceLocationRepository ambulanceLocationRepository;
    private final HospitalEvaluationRepository hospitalEvaluationRepository;

    public record DispatchResult(
            EmergencyMission mission,
            Hospital selectedHospital,
            RouteEvaluation selectedRoute,
            TriageAssessment triageAssessment,
            HospitalAcknowledgment acknowledgment,
            List<RouteEvaluation> allEvaluations,
            String decisionSummary
    ) {}

    public EmergencyDispatchService(HospitalService hospitalService,
                                   ClinicalTriageService triageService,
                                   RoutingService routingService,
                                   RealtimeEventService eventService,
                                   EmergencyRecordRepository emergencyRecordRepository,
                                   VitalReadingRepository vitalReadingRepository,
                                   AmbulanceLocationRepository ambulanceLocationRepository,
                                   HospitalEvaluationRepository hospitalEvaluationRepository) {
        this.hospitalService = hospitalService;
        this.triageService = triageService;
        this.routingService = routingService;
        this.eventService = eventService;
        this.emergencyRecordRepository = emergencyRecordRepository;
        this.vitalReadingRepository = vitalReadingRepository;
        this.ambulanceLocationRepository = ambulanceLocationRepository;
        this.hospitalEvaluationRepository = hospitalEvaluationRepository;
    }

    /**
     * Complete Deterministic Selection Workflow without changing database state.
     */
    public DispatchResult evaluateOptions(GeoPoint ambulanceLocation, PatientVitals vitals,
                                         PatientInfo patient, String ambulanceId) {
        // 1. Clinical Triage Analysis
        TriageAssessment triage = triageService.assessPatient(vitals, patient);

        // 2. Fetch all candidate hospitals
        List<Hospital> hospitals = hospitalService.getAllHospitals();

        List<RouteEvaluation> allEvaluations = new ArrayList<>();
        List<RouteEvaluation> eligibleEvaluations = new ArrayList<>();
        Map<String, Hospital> hospitalMap = new HashMap<>();

        for (Hospital hosp : hospitals) {
            hospitalMap.put(hosp.getId(), hosp);

            // Infrastructure matching check
            List<String> missing = hosp.checkEligibility(triage.getRequiredInfrastructure());
            boolean isEligible = missing.isEmpty();

            // Traffic-aware route calculation
            RouteEvaluation route = routingService.calculateRoute(
                    ambulanceLocation, hosp.getLocation(), hosp.getId(), hosp.getName()
            );

            String rejectionReason = isEligible ? null : "Lacks required infrastructure: " + String.join(", ", missing);

            RouteEvaluation evaluated = new RouteEvaluation(
                    hosp.getId(),
                    hosp.getName(),
                    route.getDistanceKm(),
                    route.getTrafficCondition(),
                    route.getEtaMinutes(),
                    isEligible,
                    missing,
                    rejectionReason,
                    route.getRouteSource()
            );

            allEvaluations.add(evaluated);
            if (isEligible) {
                eligibleEvaluations.add(evaluated);
            }
        }

        // Sort: Eligible first, then lowest ETA ascending
        allEvaluations.sort(Comparator.comparing((RouteEvaluation e) -> !e.isInfrastructureEligible())
                .thenComparingDouble(RouteEvaluation::getEtaMinutes));

        Hospital selectedHospital;
        RouteEvaluation selectedRoute;
        String decisionSummary;

        if (!eligibleEvaluations.isEmpty()) {
            eligibleEvaluations.sort(Comparator.comparingDouble(RouteEvaluation::getEtaMinutes));
            selectedRoute = eligibleEvaluations.get(0);
            selectedHospital = hospitalMap.get(selectedRoute.getHospitalId());

            decisionSummary = String.format("Selected '%s' (ETA: %.1f min, Dist: %.1f km, Traffic: %s). All required clinical capabilities (%s) verified available.",
                    selectedHospital.getName(), selectedRoute.getEtaMinutes(), selectedRoute.getDistanceKm(),
                    selectedRoute.getTrafficCondition(), String.join(", ", triage.getRequiredInfrastructure()));
        } else {
            selectedRoute = allEvaluations.isEmpty() ? null : allEvaluations.get(0);
            selectedHospital = selectedRoute != null ? hospitalMap.get(selectedRoute.getHospitalId()) : null;

            decisionSummary = "WARNING: No candidate hospital met 100% of required infrastructure. Routing to fastest available facility: "
                    + (selectedHospital != null ? selectedHospital.getName() : "None");
        }

        HospitalAcknowledgment ack = (selectedHospital != null)
                ? HospitalAcknowledgment.generate(selectedHospital.getId(), selectedHospital.getName(),
                ambulanceId, patient.getPatientId(), triage.getRequiredInfrastructure())
                : null;

        String missionId = "EMERG-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        EmergencyMission mission = new EmergencyMission(missionId, ambulanceId, patient, vitals, ambulanceLocation);
        if (selectedHospital != null && selectedRoute != null) {
            mission.dispatchTo(selectedHospital, selectedRoute, triage, ack, allEvaluations);
        }

        return new DispatchResult(mission, selectedHospital, selectedRoute, triage, ack, allEvaluations, decisionSummary);
    }

    /**
     * Executes the dispatch pipeline, persists audit history, and broadcasts real-time events.
     */
    @Transactional
    public DispatchResult dispatch(GeoPoint ambulanceLocation, PatientVitals vitals,
                                  PatientInfo patient, String ambulanceId) {
        DispatchResult result = evaluateOptions(ambulanceLocation, vitals, patient, ambulanceId);
        EmergencyMission mission = result.mission();

        // 1. Persist Emergency Record Entity
        EmergencyRecordEntity record = new EmergencyRecordEntity();
        record.setEmergencyId(mission.getEmergencyId());
        record.setAmbulanceId(mission.getAmbulanceId());
        record.setPatientId(patient.getPatientId());
        record.setPatientName(patient.getName());
        record.setPatientAge(patient.getAge());
        record.setPatientGender(patient.getGender());
        record.setChiefComplaint(patient.getChiefComplaint());
        record.setStatus(mission.getStatus().name());
        record.setStartedAt(mission.getStartedAt());
        record.setSelectedHospitalId(result.selectedHospital() != null ? result.selectedHospital().getId() : null);
        record.setSelectedHospitalName(result.selectedHospital() != null ? result.selectedHospital().getName() : null);

        if (result.acknowledgment() != null) {
            record.setAcknowledgmentId(result.acknowledgment().getAcknowledgmentId());
            record.setAcknowledgmentStatus(result.acknowledgment().isAcknowledged() ? "ACCEPTED" : "PENDING");
            record.setAssignedBay(result.acknowledgment().getAssignedBay());
            record.setTeamReady(result.acknowledgment().isTeamReady());
        }

        record.setTriageSeverity(result.triageAssessment().getUrgency().name());
        record.setTriageSource(result.triageAssessment().getSource());
        record.setRequiredInfrastructure(String.join(", ", result.triageAssessment().getRequiredInfrastructure()));
        record.setTriageSummary(result.triageAssessment().getSummary());

        if (result.selectedRoute() != null) {
            record.setRoutingSource(result.selectedRoute().getRouteSource());
            record.setInitialEtaMinutes(result.selectedRoute().getEtaMinutes());
            record.setDistanceKm(result.selectedRoute().getDistanceKm());
        }

        emergencyRecordRepository.save(record);

        // 2. Persist Initial Vitals Reading
        vitalReadingRepository.save(new VitalReadingEntity(
                mission.getEmergencyId(), vitals.getRecordedAt(), vitals.getSpo2(),
                vitals.getHeartRate(), vitals.getSystolicBp(), vitals.getDiastolicBp(), vitals.getTemperature()
        ));

        // 3. Persist Initial GPS Trace
        ambulanceLocationRepository.save(new AmbulanceLocationEntity(
                mission.getEmergencyId(), Instant.now(), ambulanceLocation.getLatitude(),
                ambulanceLocation.getLongitude(), ambulanceLocation.getAddress(),
                mission.getStatus().name(), 0.0,
                result.selectedRoute() != null ? result.selectedRoute().getEtaMinutes() : 0.0
        ));

        // 4. Persist Evaluated Candidates
        for (RouteEvaluation eval : result.allEvaluations()) {
            HospitalEvaluationEntity evalEntity = new HospitalEvaluationEntity();
            evalEntity.setEmergencyId(mission.getEmergencyId());
            evalEntity.setHospitalId(eval.getHospitalId());
            evalEntity.setHospitalName(eval.getHospitalName());
            evalEntity.setEligible(eval.isInfrastructureEligible());
            evalEntity.setMissingInfrastructure(String.join(", ", eval.getMissingInfrastructure()));
            evalEntity.setDistanceKm(eval.getDistanceKm());
            evalEntity.setTrafficCondition(eval.getTrafficCondition().name());
            evalEntity.setEtaMinutes(eval.getEtaMinutes());
            evalEntity.setRoutingSource(eval.getRouteSource());
            evalEntity.setSelected(result.selectedHospital() != null && eval.getHospitalId().equals(result.selectedHospital().getId()));
            evalEntity.setRejectionReason(eval.getRejectionReason());
            hospitalEvaluationRepository.save(evalEntity);
        }

        // 5. Broadcast Real-Time Event to Hospital Control Rooms & Ambulance
        eventService.broadcast("EMERGENCY_DISPATCHED", Map.of(
                "emergencyId", mission.getEmergencyId(),
                "ambulanceId", mission.getAmbulanceId(),
                "selectedHospitalId", result.selectedHospital() != null ? result.selectedHospital().getId() : "",
                "selectedHospitalName", result.selectedHospital() != null ? result.selectedHospital().getName() : "",
                "triageLevel", result.triageAssessment().getUrgency().name(),
                "etaMinutes", result.selectedRoute() != null ? result.selectedRoute().getEtaMinutes() : 0.0,
                "assignedBay", result.acknowledgment() != null ? result.acknowledgment().getAssignedBay() : "",
                "status", mission.getStatus().name()
        ));

        logger.info("Emergency {} successfully dispatched to {}", mission.getEmergencyId(),
                result.selectedHospital() != null ? result.selectedHospital().getName() : "None");

        return result;
    }

    public List<EmergencyRecordEntity> getRecentHistory(int limit) {
        return emergencyRecordRepository.findTop20ByOrderByStartedAtDesc();
    }

    public Optional<EmergencyRecordEntity> getEmergencyRecord(String emergencyId) {
        return emergencyRecordRepository.findByEmergencyId(emergencyId);
    }

    public Map<String, Object> getEmergencyDetailsWithTelemetry(String emergencyId) {
        Optional<EmergencyRecordEntity> optRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        if (optRecord.isEmpty()) {
            return Collections.emptyMap();
        }
        EmergencyRecordEntity record = optRecord.get();
        List<VitalReadingEntity> vitals = vitalReadingRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);
        List<AmbulanceLocationEntity> locations = ambulanceLocationRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);

        Map<String, Object> map = new LinkedHashMap<>();
        map.put("emergencyId", record.getEmergencyId());
        map.put("ambulanceId", record.getAmbulanceId());
        map.put("patientId", record.getPatientId());
        map.put("patientName", record.getPatientName());
        map.put("patientAge", record.getPatientAge());
        map.put("patientGender", record.getPatientGender());
        map.put("chiefComplaint", record.getChiefComplaint());
        map.put("status", record.getStatus());
        map.put("startedAt", record.getStartedAt());
        map.put("completedAt", record.getCompletedAt());
        map.put("selectedHospitalId", record.getSelectedHospitalId());
        map.put("selectedHospitalName", record.getSelectedHospitalName());
        map.put("assignedBay", record.getAssignedBay());
        map.put("teamReady", record.getTeamReady());
        map.put("triageSeverity", record.getTriageSeverity());
        map.put("triageSummary", record.getTriageSummary());
        map.put("initialEtaMinutes", record.getInitialEtaMinutes());
        map.put("distanceKm", record.getDistanceKm());
        map.put("vitalReadings", vitals);
        map.put("locations", locations);
        return map;
    }

    @Transactional
    public Optional<DispatchResult> rerouteEmergency(String emergencyId, String rejectedHospitalId, String reason) {
        Optional<EmergencyRecordEntity> optRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        if (optRecord.isEmpty()) {
            return Optional.empty();
        }
        EmergencyRecordEntity record = optRecord.get();

        if ("COMPLETED".equalsIgnoreCase(record.getStatus())) {
            throw new IllegalStateException("Cannot reroute an emergency mission that has already been completed.");
        }

        PatientInfo patient = new PatientInfo(
                record.getPatientId() != null ? record.getPatientId() : "PAT-999",
                record.getPatientName() != null ? record.getPatientName() : "Emergency Patient",
                record.getPatientAge() != null ? record.getPatientAge() : 45,
                record.getPatientGender() != null ? record.getPatientGender() : "Unknown",
                record.getChiefComplaint() != null ? record.getChiefComplaint() : "Acute Distress",
                "Unknown", "None", "NKDA", "Contact"
        );

        var locations = ambulanceLocationRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);
        GeoPoint currentAmbulanceLoc = locations.isEmpty()
                ? AmbulanceSimulationService.DEFAULT_DISPATCH_ORIGIN
                : new GeoPoint(locations.get(locations.size() - 1).getLatitude(), locations.get(locations.size() - 1).getLongitude());

        var vitalLogs = vitalReadingRepository.findByEmergencyIdOrderByRecordedAtAsc(emergencyId);
        PatientVitals currentVitals = vitalLogs.isEmpty()
                ? new PatientVitals(90.0, 120, 100, 60, 37.0)
                : new PatientVitals(
                        vitalLogs.get(vitalLogs.size() - 1).getSpo2(),
                        vitalLogs.get(vitalLogs.size() - 1).getHeartRate(),
                        vitalLogs.get(vitalLogs.size() - 1).getSystolicBp(),
                        vitalLogs.get(vitalLogs.size() - 1).getDiastolicBp(),
                        vitalLogs.get(vitalLogs.size() - 1).getTemperature()
                );

        TriageAssessment triage = triageService.assessPatient(currentVitals, patient);

        // Find candidate hospitals excluding the rejected one
        List<Hospital> candidates = hospitalService.getAllHospitals().stream()
                .filter(h -> rejectedHospitalId == null || !h.getId().equalsIgnoreCase(rejectedHospitalId))
                .filter(h -> h.isEligibleFor(triage.getRequiredInfrastructure()))
                .toList();

        if (candidates.isEmpty()) {
            record.setStatus("UNASSIGNED_CAPACITY_DEPLETED");
            emergencyRecordRepository.save(record);
            eventService.broadcast("EMERGENCY_REROUTE_FAILED", Map.of(
                    "emergencyId", emergencyId,
                    "reason", "No eligible hospital available after rejection by " + rejectedHospitalId
            ));
            return Optional.empty();
        }

        // Calculate routes to candidate hospitals and pick lowest ETA
        List<RouteEvaluation> evaluations = candidates.stream()
                .map(h -> routingService.calculateRoute(currentAmbulanceLoc, h.getLocation(), h.getId(), h.getName()))
                .sorted(Comparator.comparingDouble(RouteEvaluation::getEtaMinutes))
                .toList();

        RouteEvaluation bestRoute = evaluations.get(0);
        Hospital newHospital = hospitalService.getHospitalById(bestRoute.getHospitalId()).orElse(null);

        record.setSelectedHospitalId(newHospital != null ? newHospital.getId() : null);
        record.setSelectedHospitalName(newHospital != null ? newHospital.getName() : null);
        record.setStatus("REROUTED");
        record.setAcknowledgmentStatus("PENDING");
        record.setAssignedBay(null);
        record.setTeamReady(false);
        record.setInitialEtaMinutes(bestRoute.getEtaMinutes());
        record.setDistanceKm(bestRoute.getDistanceKm());
        emergencyRecordRepository.save(record);

        HospitalAcknowledgment ack = (newHospital != null)
                ? HospitalAcknowledgment.generate(newHospital.getId(), newHospital.getName(),
                record.getAmbulanceId(), patient.getPatientId(), triage.getRequiredInfrastructure())
                : null;

        EmergencyMission mission = new EmergencyMission(
                emergencyId, record.getAmbulanceId(), patient, currentVitals, currentAmbulanceLoc
        );
        if (newHospital != null) {
            mission.dispatchTo(newHospital, bestRoute, triage, ack, evaluations);
        }

        eventService.broadcast("EMERGENCY_REROUTED", Map.of(
                "emergencyId", emergencyId,
                "ambulanceId", record.getAmbulanceId(),
                "previousHospitalId", rejectedHospitalId != null ? rejectedHospitalId : "",
                "newHospitalId", newHospital != null ? newHospital.getId() : "",
                "newHospitalName", newHospital != null ? newHospital.getName() : "",
                "newEtaMinutes", bestRoute.getEtaMinutes(),
                "distanceKm", bestRoute.getDistanceKm(),
                "status", "REROUTED",
                "reason", reason != null ? reason : "Hospital diverted"
        ));

        logger.info("Emergency {} successfully rerouted from {} to {}",
                emergencyId, rejectedHospitalId, newHospital != null ? newHospital.getName() : "None");

        return Optional.of(new DispatchResult(
                mission, newHospital, bestRoute, triage, ack, evaluations,
                "Dynamic Reroute: Transferred to " + (newHospital != null ? newHospital.getName() : "")
                        + " following diversion at " + rejectedHospitalId
        ));
    }
}

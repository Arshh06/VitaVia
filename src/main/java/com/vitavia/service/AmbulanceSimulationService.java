package com.vitavia.service;

import com.vitavia.domain.model.*;
import com.vitavia.entity.AmbulanceLocationEntity;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.entity.VitalReadingEntity;
import com.vitavia.repository.AmbulanceLocationRepository;
import com.vitavia.repository.EmergencyRecordRepository;
import com.vitavia.repository.VitalReadingRepository;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Ambulance IoT Telemetry & Transit Simulator Service.
 * Simulates connected ambulance IoT devices, continuous physiological vitals drift,
 * transit movement interpolation, and real-time synchronization with database and hospital dashboard.
 */
@Service
public class AmbulanceSimulationService {

    private static final Logger logger = LoggerFactory.getLogger(AmbulanceSimulationService.class);

    public static final GeoPoint DEFAULT_DISPATCH_ORIGIN = new GeoPoint(
            12.9700, 77.6000, "Trinity Junction Central (Dispatch Origin)"
    );

    private final EmergencyDispatchService dispatchService;
    private final EmergencyRecordRepository emergencyRecordRepository;
    private final VitalReadingRepository vitalReadingRepository;
    private final AmbulanceLocationRepository ambulanceLocationRepository;
    private final RealtimeEventService eventService;

    private EmergencyMission activeMission;
    private String activeScenarioKey;

    public record Scenario(String key, String description, PatientInfo patient, PatientVitals vitals) {}

    private final Map<String, Scenario> presetScenarios = new LinkedHashMap<>();

    public AmbulanceSimulationService(EmergencyDispatchService dispatchService,
                                     EmergencyRecordRepository emergencyRecordRepository,
                                     VitalReadingRepository vitalReadingRepository,
                                     AmbulanceLocationRepository ambulanceLocationRepository,
                                     RealtimeEventService eventService) {
        this.dispatchService = dispatchService;
        this.emergencyRecordRepository = emergencyRecordRepository;
        this.vitalReadingRepository = vitalReadingRepository;
        this.ambulanceLocationRepository = ambulanceLocationRepository;
        this.eventService = eventService;
    }

    @PostConstruct
    public void init() {
        initScenarios();
        resetToScenario("1. Acute Respiratory Distress & Hypoxia (Critical)");
    }

    private void initScenarios() {
        presetScenarios.put("1. Acute Respiratory Distress & Hypoxia (Critical)", new Scenario(
                "1. Acute Respiratory Distress & Hypoxia (Critical)",
                "Patient experiencing severe dyspnea, falling oxygen levels, and tachycardia. Requires ICU + Ventilator.",
                new PatientInfo("PAT-8812", "Sarah Jenkins", 58, "Female",
                        "Severe shortness of breath, acute cyanosis, wheezing",
                        "A+", "COPD, Hypertension", "Penicillin", "+91-98765-43210"),
                new PatientVitals(87.5, 128, 92, 58, 38.4)
        ));

        presetScenarios.put("2. Acute Coronary Syndrome / Cardiogenic Stress (High)", new Scenario(
                "2. Acute Coronary Syndrome / Cardiogenic Stress (High)",
                "Crushing retrosternal chest pain with diaphoresis and hypotension. Requires ICU + Emergency Doctor.",
                new PatientInfo("PAT-4029", "Robert Chen", 63, "Male",
                        "Crushing retrosternal chest pain radiating to left arm",
                        "O+", "Type 2 Diabetes", "NKDA", "+91-98765-43211"),
                new PatientVitals(91.0, 118, 88, 54, 37.2)
        ));

        presetScenarios.put("3. Moderate Trauma / Extremity Injury (Moderate)", new Scenario(
                "3. Moderate Trauma / Extremity Injury (Moderate)",
                "Closed tibia fracture with moderate pain. Vitals stable. Standard Emergency Bed required.",
                new PatientInfo("PAT-1194", "David Kumar", 29, "Male",
                        "Right lower leg trauma following bike collision",
                        "B+", "None", "NKDA", "+91-98765-43212"),
                new PatientVitals(98.0, 84, 124, 78, 36.8)
        ));

        presetScenarios.put("4. Severe Sepsis / High Grade Pyrexia (Critical)", new Scenario(
                "4. Severe Sepsis / High Grade Pyrexia (Critical)",
                "Septic shock presentation with hyperthermia and severe tachycardia. Requires ICU + Emergency Bed.",
                new PatientInfo("PAT-7731", "Maria Rodriguez", 71, "Female",
                        "High fever, altered mental status, suspected septic shock",
                        "AB+", "Chronic Kidney Disease", "Sulfa drugs", "+91-98765-43213"),
                new PatientVitals(89.5, 136, 82, 48, 40.2)
        ));
    }

    public synchronized void resetToScenario(String scenarioKey) {
        Scenario scenario = presetScenarios.getOrDefault(scenarioKey, presetScenarios.values().iterator().next());
        this.activeScenarioKey = scenario.key();
        String emergencyId = "EMERG-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        this.activeMission = new EmergencyMission(
                emergencyId,
                "AMB-07",
                scenario.patient(),
                scenario.vitals(),
                DEFAULT_DISPATCH_ORIGIN
        );
    }

    public synchronized EmergencyMission getActiveMission() {
        return activeMission;
    }

    public Map<String, Scenario> getPresetScenarios() {
        return Collections.unmodifiableMap(presetScenarios);
    }

    public String getActiveScenarioKey() {
        return activeScenarioKey;
    }

    /**
     * Advances the simulation by a step fraction (e.g. 0.10 for +10% movement),
     * applies physiologic vital variations, updates database audit trail, and broadcasts SSE event.
     */
    @Transactional
    public synchronized EmergencyMission stepSimulation(double stepFraction, String trend) {
        if (activeMission == null) {
            resetToScenario(activeScenarioKey);
        }

        // 1. Generate drifted vitals
        PatientVitals current = activeMission.getCurrentVitals();
        PatientVitals drifted = generateDriftedVitals(current, trend);

        // 2. Advance transit state machine & coordinates
        activeMission.advanceTransit(stepFraction, drifted);

        // 3. Persist Vital Reading to database
        vitalReadingRepository.save(new VitalReadingEntity(
                activeMission.getEmergencyId(), drifted.getRecordedAt(), drifted.getSpo2(),
                drifted.getHeartRate(), drifted.getSystolicBp(), drifted.getDiastolicBp(), drifted.getTemperature()
        ));

        // 4. Persist Location to database
        ambulanceLocationRepository.save(new AmbulanceLocationEntity(
                activeMission.getEmergencyId(), Instant.now(),
                activeMission.getCurrentLocation().getLatitude(),
                activeMission.getCurrentLocation().getLongitude(),
                activeMission.getCurrentLocation().getAddress(),
                activeMission.getStatus().name(),
                activeMission.getProgressRatio() * 100.0,
                activeMission.getCurrentEtaMinutes()
        ));

        // 5. Update Emergency Record in database
        Optional<EmergencyRecordEntity> optRecord = emergencyRecordRepository.findByEmergencyId(activeMission.getEmergencyId());
        optRecord.ifPresent(record -> {
            record.setStatus(activeMission.getStatus().name());
            if (activeMission.getStatus() == EmergencyStatus.ARRIVED) {
                record.setStatus("ARRIVED");
            }
            emergencyRecordRepository.save(record);
        });

        // 6. Broadcast Real-Time Update to Hospital Control Room & Ambulance Dashboard
        eventService.broadcast("TELEMETRY_UPDATED", Map.of(
                "emergencyId", activeMission.getEmergencyId(),
                "ambulanceId", activeMission.getAmbulanceId(),
                "status", activeMission.getStatus().name(),
                "progressRatio", activeMission.getProgressRatio(),
                "progressPercent", (int) (activeMission.getProgressRatio() * 100),
                "remainingEtaMinutes", activeMission.getCurrentEtaMinutes(),
                "latitude", activeMission.getCurrentLocation().getLatitude(),
                "longitude", activeMission.getCurrentLocation().getLongitude(),
                "address", activeMission.getCurrentLocation().getAddress(),
                "vitals", Map.of(
                        "spo2", drifted.getSpo2(),
                        "heartRate", drifted.getHeartRate(),
                        "systolicBp", drifted.getSystolicBp(),
                        "diastolicBp", drifted.getDiastolicBp(),
                        "temperature", drifted.getTemperature(),
                        "recordedAt", drifted.getRecordedAt().toString()
                )
        ));

        return activeMission;
    }

    public synchronized PatientVitals fluctuateVitalsOnly() {
        if (activeMission == null) {
            resetToScenario(activeScenarioKey);
        }
        PatientVitals drifted = generateDriftedVitals(activeMission.getCurrentVitals(), "fluctuate");
        activeMission.updateVitalsOnly(drifted);

        vitalReadingRepository.save(new VitalReadingEntity(
                activeMission.getEmergencyId(), drifted.getRecordedAt(), drifted.getSpo2(),
                drifted.getHeartRate(), drifted.getSystolicBp(), drifted.getDiastolicBp(), drifted.getTemperature()
        ));

        eventService.broadcast("VITALS_UPDATED", Map.of(
                "emergencyId", activeMission.getEmergencyId(),
                "vitals", Map.of(
                        "spo2", drifted.getSpo2(),
                        "heartRate", drifted.getHeartRate(),
                        "systolicBp", drifted.getSystolicBp(),
                        "diastolicBp", drifted.getDiastolicBp(),
                        "temperature", drifted.getTemperature(),
                        "recordedAt", drifted.getRecordedAt().toString()
                )
        ));

        return drifted;
    }

    public synchronized void setActiveMission(EmergencyMission mission) {
        this.activeMission = mission;
    }

    private PatientVitals generateDriftedVitals(PatientVitals v, String trend) {
        ThreadLocalRandom rnd = ThreadLocalRandom.current();
        double dSpo2;
        int dHr;
        int dSbp;
        int dDbp;
        double dTemp;

        if ("deteriorate".equalsIgnoreCase(trend)) {
            dSpo2 = -0.5;
            dHr = rnd.nextInt(1, 4);
            dSbp = -rnd.nextInt(1, 4);
            dDbp = -rnd.nextInt(1, 3);
            dTemp = 0.1;
        } else if ("improve".equalsIgnoreCase(trend)) {
            dSpo2 = 0.4;
            dHr = -rnd.nextInt(1, 4);
            dSbp = rnd.nextInt(1, 3);
            dDbp = rnd.nextInt(1, 3);
            dTemp = -0.05;
        } else { // fluctuate
            double[] spo2Deltas = {-0.3, -0.1, 0.0, 0.1, 0.2};
            dSpo2 = spo2Deltas[rnd.nextInt(spo2Deltas.length)];
            dHr = rnd.nextInt(-2, 3);
            dSbp = rnd.nextInt(-2, 3);
            dDbp = rnd.nextInt(-1, 2);
            double[] tempDeltas = {-0.05, 0.0, 0.05};
            dTemp = tempDeltas[rnd.nextInt(tempDeltas.length)];
        }

        return v.withDrift(dSpo2, dHr, dSbp, dDbp, dTemp);
    }
}

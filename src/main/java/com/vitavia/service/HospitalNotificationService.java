package com.vitavia.service;

import com.vitavia.domain.model.EmergencyStatus;
import com.vitavia.domain.model.HospitalAcknowledgment;
import com.vitavia.entity.EmergencyRecordEntity;
import com.vitavia.repository.EmergencyRecordRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;

/**
 * Hospital Control Room Action Service.
 * Connects hospital staff actions back to the active emergency mission and database.
 */
@Service
public class HospitalNotificationService {

    private static final Logger logger = LoggerFactory.getLogger(HospitalNotificationService.class);

    private final EmergencyRecordRepository emergencyRecordRepository;
    private final RealtimeEventService eventService;

    public HospitalNotificationService(EmergencyRecordRepository emergencyRecordRepository,
                                       RealtimeEventService eventService) {
        this.emergencyRecordRepository = emergencyRecordRepository;
        this.eventService = eventService;
    }

    /**
     * Hospital staff accepts and prepares trauma bay / clinical team.
     */
    @Transactional
    public Optional<EmergencyRecordEntity> acknowledgeEmergency(String emergencyId, String hospitalId,
                                                               String assignedBay, boolean teamReady, String notes) {
        Optional<EmergencyRecordEntity> optRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        if (optRecord.isEmpty()) {
            return Optional.empty();
        }

        EmergencyRecordEntity record = optRecord.get();
        record.setStatus(EmergencyStatus.ACKNOWLEDGED.name());
        record.setAcknowledgmentStatus("ACCEPTED");
        if (assignedBay != null && !assignedBay.isBlank()) {
            record.setAssignedBay(assignedBay.trim());
        }
        record.setTeamReady(teamReady);
        emergencyRecordRepository.save(record);

        // Broadcast real-time handshake confirmation to ambulance dashboard!
        eventService.broadcast("HOSPITAL_ACKNOWLEDGED", Map.of(
                "emergencyId", emergencyId,
                "hospitalId", hospitalId,
                "hospitalName", record.getSelectedHospitalName(),
                "status", "ACKNOWLEDGED",
                "assignedBay", record.getAssignedBay() != null ? record.getAssignedBay() : "Trauma Bay #1",
                "teamReady", teamReady,
                "notes", notes != null ? notes : "Team standing by"
        ));

        logger.info("Hospital {} acknowledged emergency {}. Bay: {}, Team Ready: {}",
                hospitalId, emergencyId, record.getAssignedBay(), teamReady);

        return Optional.of(record);
    }

    /**
     * Hospital marks patient arrival / admission completed.
     */
    @Transactional
    public Optional<EmergencyRecordEntity> markPatientReceived(String emergencyId, String hospitalId) {
        Optional<EmergencyRecordEntity> optRecord = emergencyRecordRepository.findByEmergencyId(emergencyId);
        if (optRecord.isEmpty()) {
            return Optional.empty();
        }

        EmergencyRecordEntity record = optRecord.get();
        if (EmergencyStatus.COMPLETED.name().equalsIgnoreCase(record.getStatus())) {
            throw new IllegalStateException("Duplicate action: Emergency " + emergencyId + " is already marked COMPLETED.");
        }
        record.setStatus(EmergencyStatus.COMPLETED.name());
        record.setCompletedAt(Instant.now());
        emergencyRecordRepository.save(record);

        eventService.broadcast("PATIENT_RECEIVED", Map.of(
                "emergencyId", emergencyId,
                "hospitalId", hospitalId,
                "status", "COMPLETED",
                "completedAt", record.getCompletedAt().toString()
        ));

        logger.info("Patient for emergency {} formally received at hospital {}", emergencyId, hospitalId);
        return Optional.of(record);
    }

    public Optional<EmergencyRecordEntity> getLatestIncomingForHospital(String hospitalId) {
        if (hospitalId == null || hospitalId.isBlank()) {
            var list = emergencyRecordRepository.findTop20ByOrderByStartedAtDesc();
            return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
        }
        var list = emergencyRecordRepository.findBySelectedHospitalIdOrderByStartedAtDesc(hospitalId);
        return list.isEmpty() ? Optional.empty() : Optional.of(list.get(0));
    }
}

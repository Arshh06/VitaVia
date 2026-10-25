package com.vitavia.domain.model;

import java.io.Serializable;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Formal Hospital Dispatch Handshake & Resource Reservation Acknowledgment.
 */
public class HospitalAcknowledgment implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String acknowledgmentId;
    private final String hospitalId;
    private final String hospitalName;
    private final String ambulanceId;
    private final String patientId;
    private final boolean acknowledged;
    private final String assignedBay;
    private final boolean teamReady;
    private final String message;
    private final Instant timestamp;

    public HospitalAcknowledgment(String acknowledgmentId, String hospitalId, String hospitalName,
                                  String ambulanceId, String patientId, boolean acknowledged,
                                  String assignedBay, boolean teamReady, String message, Instant timestamp) {
        this.acknowledgmentId = acknowledgmentId != null ? acknowledgmentId : "ACK-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        this.hospitalId = Objects.requireNonNull(hospitalId, "hospitalId must not be null");
        this.hospitalName = hospitalName != null ? hospitalName : hospitalId;
        this.ambulanceId = ambulanceId != null ? ambulanceId : "AMB-01";
        this.patientId = patientId != null ? patientId : "PAT-01";
        this.acknowledged = acknowledged;
        this.assignedBay = assignedBay != null ? assignedBay : "Trauma Bay #1";
        this.teamReady = teamReady;
        this.message = message != null ? message : "Emergency notification received.";
        this.timestamp = timestamp != null ? timestamp : Instant.now();
    }

    public static HospitalAcknowledgment generate(String hospitalId, String hospitalName, String ambulanceId,
                                                   String patientId, List<String> requiredInfra) {
        int bayNumber = Math.abs(Objects.hash(hospitalId, patientId)) % 6 + 1;
        String assignedBay = "Emergency Trauma Bay #" + bayNumber;
        String infraStr = (requiredInfra != null && !requiredInfra.isEmpty())
                ? String.join(", ", requiredInfra)
                : "Standard Emergency Bed";

        String message = String.format("%s Central Emergency Control acknowledges inbound %s. %s reserved. Clinical emergency team on standby with %s prepared.",
                hospitalName, ambulanceId, assignedBay, infraStr);

        return new HospitalAcknowledgment(
                "ACK-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase(),
                hospitalId,
                hospitalName,
                ambulanceId,
                patientId,
                true,
                assignedBay,
                true,
                message,
                Instant.now()
        );
    }

    public String getAcknowledgmentId() {
        return acknowledgmentId;
    }

    public String getHospitalId() {
        return hospitalId;
    }

    public String getHospitalName() {
        return hospitalName;
    }

    public String getAmbulanceId() {
        return ambulanceId;
    }

    public String getPatientId() {
        return patientId;
    }

    public boolean isAcknowledged() {
        return acknowledged;
    }

    public String getAssignedBay() {
        return assignedBay;
    }

    public boolean isTeamReady() {
        return teamReady;
    }

    public String getMessage() {
        return message;
    }

    public Instant getTimestamp() {
        return timestamp;
    }
}

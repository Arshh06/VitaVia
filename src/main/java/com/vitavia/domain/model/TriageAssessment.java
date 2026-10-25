package com.vitavia.domain.model;

import java.io.Serializable;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Encapsulated Clinical Triage Assessment result.
 */
public class TriageAssessment implements Serializable {

    private static final long serialVersionUID = 1L;

    private final UrgencyLevel urgency;
    private final List<String> requiredInfrastructure;
    private final String summary;
    private final String clinicalNotes;
    private final String source;

    public TriageAssessment(UrgencyLevel urgency, List<String> requiredInfrastructure,
                            String summary, String clinicalNotes, String source) {
        this.urgency = Objects.requireNonNull(urgency, "urgency must not be null");
        this.requiredInfrastructure = requiredInfrastructure != null
                ? List.copyOf(requiredInfrastructure)
                : Collections.emptyList();
        this.summary = summary != null ? summary : "Clinical evaluation completed.";
        this.clinicalNotes = clinicalNotes != null ? clinicalNotes : "";
        this.source = source != null ? source : "DETERMINISTIC_HEURISTIC";
    }

    public UrgencyLevel getUrgency() {
        return urgency;
    }

    public List<String> getRequiredInfrastructure() {
        return requiredInfrastructure;
    }

    public String getSummary() {
        return summary;
    }

    public String getClinicalNotes() {
        return clinicalNotes;
    }

    public String getSource() {
        return source;
    }

    public boolean requiresIcu() {
        return requiredInfrastructure.stream().anyMatch(s -> s.equalsIgnoreCase("ICU"));
    }

    public boolean requiresVentilator() {
        return requiredInfrastructure.stream().anyMatch(s -> s.equalsIgnoreCase("Ventilator"));
    }

    @Override
    public String toString() {
        return String.format("TriageAssessment[urgency=%s, infra=%s, source=%s]",
                urgency, requiredInfrastructure, source);
    }
}

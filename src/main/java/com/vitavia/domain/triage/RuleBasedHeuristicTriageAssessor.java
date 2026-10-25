package com.vitavia.domain.triage;

import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.domain.model.TriageAssessment;
import com.vitavia.domain.model.UrgencyLevel;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * Deterministic Rule-Based Clinical Triage Assessor.
 * Demonstrates:
 * - Polymorphism: Implements TriageAssessor with medically calibrated deterministic heuristics.
 * - Guarantees 100% offline reliability without external cloud credentials.
 */
@Component("ruleBasedHeuristicTriageAssessor")
public class RuleBasedHeuristicTriageAssessor implements TriageAssessor {

    public static final String ASSESSOR_NAME = "HEURISTIC_FALLBACK";

    @Override
    public TriageAssessment assess(PatientVitals vitals, PatientInfo patient) {
        double spo2 = vitals.getSpo2();
        int hr = vitals.getHeartRate();
        int sbp = vitals.getSystolicBp();
        int dbp = vitals.getDiastolicBp();
        double temp = vitals.getTemperature();

        List<String> requiredInfra = new ArrayList<>();
        requiredInfra.add("Emergency Bed");
        requiredInfra.add("Emergency Doctor");

        UrgencyLevel urgency;
        String summary;
        String notes;

        // Critical condition
        if (spo2 < 88.0 || sbp < 80 || (hr > 135 && sbp < 90) || temp >= 40.0) {
            urgency = UrgencyLevel.CRITICAL;
            requiredInfra.add("ICU");
            requiredInfra.add("Ventilator");
            summary = String.format("Severe hemodynamic/respiratory instability (SpO2 %.1f%%, HR %d bpm, BP %d/%d). Immediate ICU & ventilator support mandatory.",
                    spo2, hr, sbp, dbp);
            notes = "Patient exhibits signs of decompensated shock or acute respiratory failure. Requires tertiary Level-1 trauma/ICU capability.";
        }
        // High urgency
        else if (spo2 < 92.0 || hr > 115 || sbp < 90 || sbp > 180 || temp >= 38.8) {
            urgency = UrgencyLevel.HIGH;
            requiredInfra.add("ICU");
            if (spo2 < 91.0) {
                requiredInfra.add("Ventilator");
            }
            summary = String.format("Acute distress detected (SpO2 %.1f%%, HR %d bpm, Temp %.1f°C). Urgent emergency bed and ICU readiness needed.",
                    spo2, hr, temp);
            notes = "Signs of compromised oxygenation or cardiovascular stress. Patient requires continuous multi-parameter monitoring.";
        }
        // Moderate urgency
        else if (spo2 < 95.0 || hr > 100 || temp >= 37.8 || sbp > 140) {
            urgency = UrgencyLevel.MODERATE;
            summary = String.format("Moderate physiological deviation (SpO2 %.1f%%, HR %d bpm). Standard emergency stabilization required.",
                    spo2, hr);
            notes = "Patient requires acute emergency physician assessment and supplemental oxygen therapy.";
        }
        // Low urgency / Stable
        else {
            urgency = UrgencyLevel.LOW;
            summary = String.format("Vital parameters within acceptable range (SpO2 %.1f%%, HR %d bpm, BP %d/%d).",
                    spo2, hr, sbp, dbp);
            notes = "Routine emergency observation and physician consultation.";
        }

        List<String> deduped = new ArrayList<>(new LinkedHashSet<>(requiredInfra));

        return new TriageAssessment(
                urgency,
                deduped,
                summary,
                notes,
                ASSESSOR_NAME
        );
    }

    @Override
    public String getAssessorName() {
        return ASSESSOR_NAME;
    }
}

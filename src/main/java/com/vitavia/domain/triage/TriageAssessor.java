package com.vitavia.domain.triage;

import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.domain.model.TriageAssessment;

/**
 * Clinical Triage Strategy Interface.
 * Demonstrates:
 * - Abstraction: Separates clinical evaluation requirements from AI or heuristic implementation.
 * - Polymorphism: Swappable AI decision support vs deterministic rule-based matrix.
 */
public interface TriageAssessor {

    /**
     * Evaluates patient telemetry and demographics to compute triage urgency level
     * and required hospital infrastructure capabilities.
     */
    TriageAssessment assess(PatientVitals vitals, PatientInfo patient);

    /**
     * Returns the name of the triage assessment engine.
     */
    String getAssessorName();
}

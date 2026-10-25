package com.vitavia.service;

import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.domain.model.TriageAssessment;
import com.vitavia.domain.triage.TriageAssessor;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

/**
 * Service encapsulating clinical decision support and triage analysis.
 * Delegates polymorphically to TriageAssessor (Gemini AI with automatic deterministic fallback).
 */
@Service
public class ClinicalTriageService {

    private final TriageAssessor triageAssessor;

    public ClinicalTriageService(@Qualifier("geminiClinicalTriageAssessor") TriageAssessor triageAssessor) {
        this.triageAssessor = triageAssessor;
    }

    public TriageAssessment assessPatient(PatientVitals vitals, PatientInfo patient) {
        return triageAssessor.assess(vitals, patient);
    }

    public String getActiveAssessorName() {
        return triageAssessor.getAssessorName();
    }
}

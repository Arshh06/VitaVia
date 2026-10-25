package com.vitavia.dto;

public record PatientInfoDto(
        String patient_id,
        String name,
        Integer age,
        String gender,
        String chief_complaint,
        String blood_group,
        String medical_history,
        String allergies,
        String emergency_contact
) {
    public static PatientInfoDto defaultPatient() {
        return new PatientInfoDto("PAT-101", "Emergency Patient", 45, "Unknown", "Acute Distress", "Unknown", "None", "NKDA", "+91-98765-43210");
    }
}

package com.vitavia.dto;

public record PatientVitalsDto(
        Double spo2,
        Integer heart_rate,
        Integer systolic_bp,
        Integer diastolic_bp,
        Double temperature,
        String recorded_at
) {}

package com.vitavia.dto;

import com.fasterxml.jackson.annotation.JsonAlias;

public record HospitalUpdateRequest(
        @JsonAlias({"emergency_bed_available", "emergencyBedAvailable"})
        Boolean emergencyBedAvailable,

        @JsonAlias({"icu_available", "icuAvailable"})
        Boolean icuAvailable,

        @JsonAlias({"ventilator_available", "ventilatorAvailable"})
        Boolean ventilatorAvailable,

        @JsonAlias({"emergency_doctor_available", "emergencyDoctorAvailable"})
        Boolean emergencyDoctorAvailable,

        @JsonAlias({"available_emergency_beds", "availableEmergencyBeds"})
        Integer availableEmergencyBeds,

        @JsonAlias({"available_icu_beds", "availableIcuBeds"})
        Integer availableIcuBeds,

        @JsonAlias({"available_ventilators", "availableVentilators"})
        Integer availableVentilators
) {}

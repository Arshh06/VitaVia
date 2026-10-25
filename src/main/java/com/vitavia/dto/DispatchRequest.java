package com.vitavia.dto;

import com.fasterxml.jackson.annotation.JsonAlias;

public record DispatchRequest(
        @JsonAlias({"ambulance_id", "ambulanceId"})
        String ambulanceId,

        @JsonAlias({"patient_info", "patientInfo"})
        PatientInfoDto patientInfo,

        PatientVitalsDto vitals,
        GeoPointDto location
) {}

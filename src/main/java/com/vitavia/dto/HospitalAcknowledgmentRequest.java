package com.vitavia.dto;

import com.fasterxml.jackson.annotation.JsonAlias;

public record HospitalAcknowledgmentRequest(
        @JsonAlias({"hospital_id", "hospitalId"})
        String hospitalId,

        @JsonAlias({"assigned_bay", "assignedBay"})
        String assignedBay,

        @JsonAlias({"team_ready", "teamReady"})
        Boolean teamReady,

        String notes
) {}

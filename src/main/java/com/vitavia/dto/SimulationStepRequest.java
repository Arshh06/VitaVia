package com.vitavia.dto;

import com.fasterxml.jackson.annotation.JsonAlias;

public record SimulationStepRequest(
        @JsonAlias({"step_fraction", "stepFraction"})
        Double stepFraction,

        String trend
) {}

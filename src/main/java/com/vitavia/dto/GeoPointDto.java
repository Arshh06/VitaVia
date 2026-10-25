package com.vitavia.dto;

public record GeoPointDto(
        Double latitude,
        Double longitude,
        String address
) {}

package com.vitavia.domain.model;

import java.io.Serializable;
import java.util.Objects;

/**
 * Encapsulated Geographic Coordinate representation.
 * Demonstrates Encapsulation with strict coordinate boundary validation
 * and embedded Haversine geodesic calculation.
 */
public class GeoPoint implements Serializable {

    private static final long serialVersionUID = 1L;
    private static final double EARTH_RADIUS_KM = 6371.0;

    private final double latitude;
    private final double longitude;
    private final String address;

    public GeoPoint(double latitude, double longitude, String address) {
        if (latitude < -90.0 || latitude > 90.0) {
            throw new IllegalArgumentException("Latitude must be between -90 and 90 degrees. Received: " + latitude);
        }
        if (longitude < -180.0 || longitude > 180.0) {
            throw new IllegalArgumentException("Longitude must be between -180 and 180 degrees. Received: " + longitude);
        }
        this.latitude = latitude;
        this.longitude = longitude;
        this.address = address != null ? address.trim() : "Unspecified Coordinate";
    }

    public GeoPoint(double latitude, double longitude) {
        this(latitude, longitude, null);
    }

    public double getLatitude() {
        return latitude;
    }

    public double getLongitude() {
        return longitude;
    }

    public String getAddress() {
        return address;
    }

    /**
     * Calculates the Great-Circle Haversine distance in kilometers to another coordinate.
     */
    public double distanceTo(GeoPoint other) {
        Objects.requireNonNull(other, "Target coordinate must not be null");

        double dLat = Math.toRadians(other.latitude - this.latitude);
        double dLon = Math.toRadians(other.longitude - this.longitude);

        double a = Math.sin(dLat / 2.0) * Math.sin(dLat / 2.0)
                + Math.cos(Math.toRadians(this.latitude)) * Math.cos(Math.toRadians(other.latitude))
                * Math.sin(dLon / 2.0) * Math.sin(dLon / 2.0);

        double c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
        return Math.round(EARTH_RADIUS_KM * c * 100.0) / 100.0;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof GeoPoint geoPoint)) return false;
        return Double.compare(geoPoint.latitude, latitude) == 0 &&
               Double.compare(geoPoint.longitude, longitude) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(latitude, longitude);
    }

    @Override
    public String toString() {
        return String.format("GeoPoint[lat=%.5f, lon=%.5f, addr='%s']", latitude, longitude, address);
    }
}

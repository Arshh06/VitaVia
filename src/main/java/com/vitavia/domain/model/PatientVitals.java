package com.vitavia.domain.model;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;

/**
 * Encapsulated Patient Vitals domain object.
 * Demonstrates Encapsulation with strict physiological validation rules,
 * clinical evaluation helper methods, and safe immutable state mutation.
 */
public class PatientVitals implements Serializable {

    private static final long serialVersionUID = 1L;

    private final double spo2;
    private final int heartRate;
    private final int systolicBp;
    private final int diastolicBp;
    private final double temperature;
    private final Instant recordedAt;

    public PatientVitals(double spo2, int heartRate, int systolicBp, int diastolicBp, double temperature, Instant recordedAt) {
        if (spo2 < 0.0 || spo2 > 100.0) {
            throw new IllegalArgumentException("SpO2 must be between 0.0 and 100.0%. Received: " + spo2);
        }
        if (heartRate < 0 || heartRate > 300) {
            throw new IllegalArgumentException("Heart rate must be between 0 and 300 BPM. Received: " + heartRate);
        }
        if (systolicBp < 0 || systolicBp > 300) {
            throw new IllegalArgumentException("Systolic BP must be between 0 and 300 mmHg. Received: " + systolicBp);
        }
        if (diastolicBp < 0 || diastolicBp > 200) {
            throw new IllegalArgumentException("Diastolic BP must be between 0 and 200 mmHg. Received: " + diastolicBp);
        }
        if (temperature < 25.0 || temperature > 45.0) {
            throw new IllegalArgumentException("Temperature must be between 25.0 and 45.0 °C. Received: " + temperature);
        }
        this.spo2 = Math.round(spo2 * 10.0) / 10.0;
        this.heartRate = heartRate;
        this.systolicBp = systolicBp;
        this.diastolicBp = diastolicBp;
        this.temperature = Math.round(temperature * 10.0) / 10.0;
        this.recordedAt = recordedAt != null ? recordedAt : Instant.now();
    }

    public PatientVitals(double spo2, int heartRate, int systolicBp, int diastolicBp, double temperature) {
        this(spo2, heartRate, systolicBp, diastolicBp, temperature, Instant.now());
    }

    public double getSpo2() {
        return spo2;
    }

    public int getHeartRate() {
        return heartRate;
    }

    public int getSystolicBp() {
        return systolicBp;
    }

    public int getDiastolicBp() {
        return diastolicBp;
    }

    public double getTemperature() {
        return temperature;
    }

    public Instant getRecordedAt() {
        return recordedAt;
    }

    public boolean isSevereHypoxic() {
        return spo2 < 89.0;
    }

    public boolean isHypoxic() {
        return spo2 < 93.0;
    }

    public boolean isHypotensive() {
        return systolicBp < 90;
    }

    public boolean isHypertensiveCrisis() {
        return systolicBp > 180 || diastolicBp > 110;
    }

    public boolean isTachycardic() {
        return heartRate > 100;
    }

    public boolean isHighPyrexia() {
        return temperature >= 38.8;
    }

    /**
     * Creates a new PatientVitals instance with bounded physiologic drift.
     */
    public PatientVitals withDrift(double dSpo2, int dHr, int dSbp, int dDbp, double dTemp) {
        double newSpo2 = Math.max(65.0, Math.min(100.0, this.spo2 + dSpo2));
        int newHr = Math.max(40, Math.min(220, this.heartRate + dHr));
        int newSbp = Math.max(55, Math.min(240, this.systolicBp + dSbp));
        int newDbp = Math.max(35, Math.min(140, this.diastolicBp + dDbp));
        double newTemp = Math.max(35.0, Math.min(42.0, this.temperature + dTemp));
        return new PatientVitals(newSpo2, newHr, newSbp, newDbp, newTemp, Instant.now());
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof PatientVitals that)) return false;
        return Double.compare(that.spo2, spo2) == 0 &&
               heartRate == that.heartRate &&
               systolicBp == that.systolicBp &&
               diastolicBp == that.diastolicBp &&
               Double.compare(that.temperature, temperature) == 0;
    }

    @Override
    public int hashCode() {
        return Objects.hash(spo2, heartRate, systolicBp, diastolicBp, temperature);
    }

    @Override
    public String toString() {
        return String.format("Vitals[SpO2=%.1f%%, HR=%d bpm, BP=%d/%d mmHg, Temp=%.1f°C]",
                spo2, heartRate, systolicBp, diastolicBp, temperature);
    }
}

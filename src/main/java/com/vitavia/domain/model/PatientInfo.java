package com.vitavia.domain.model;

import java.io.Serializable;
import java.util.Objects;

/**
 * Encapsulated Patient Emergency Profile.
 */
public class PatientInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    private final String patientId;
    private final String name;
    private final int age;
    private final String gender;
    private final String chiefComplaint;
    private final String bloodGroup;
    private final String medicalHistory;
    private final String allergies;
    private final String emergencyContact;

    public PatientInfo(String patientId, String name, int age, String gender, String chiefComplaint,
                       String bloodGroup, String medicalHistory, String allergies, String emergencyContact) {
        this.patientId = Objects.requireNonNull(patientId, "patientId must not be null").trim();
        this.name = (name != null && !name.isBlank()) ? name.trim() : "Emergency Patient";
        this.age = Math.max(0, age);
        this.gender = (gender != null && !gender.isBlank()) ? gender.trim() : "Unknown";
        this.chiefComplaint = (chiefComplaint != null && !chiefComplaint.isBlank()) ? chiefComplaint.trim() : "Acute Medical Emergency";
        this.bloodGroup = bloodGroup != null ? bloodGroup.trim() : "Unknown";
        this.medicalHistory = medicalHistory != null ? medicalHistory.trim() : "None reported";
        this.allergies = allergies != null ? allergies.trim() : "NKDA";
        this.emergencyContact = emergencyContact != null ? emergencyContact.trim() : "Not provided";
    }

    public PatientInfo(String patientId, String name, int age, String gender, String chiefComplaint) {
        this(patientId, name, age, gender, chiefComplaint, "Unknown", "None reported", "NKDA", "Not provided");
    }

    public static PatientInfo defaultPatient() {
        return new PatientInfo("PAT-9021", "Alex Mercer", 52, "Male", "Acute severe chest tightness and dyspnea");
    }

    public String getPatientId() {
        return patientId;
    }

    public String getName() {
        return name;
    }

    public int getAge() {
        return age;
    }

    public String getGender() {
        return gender;
    }

    public String getChiefComplaint() {
        return chiefComplaint;
    }

    public String getBloodGroup() {
        return bloodGroup;
    }

    public String getMedicalHistory() {
        return medicalHistory;
    }

    public String getAllergies() {
        return allergies;
    }

    public String getEmergencyContact() {
        return emergencyContact;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof PatientInfo that)) return false;
        return age == that.age && Objects.equals(patientId, that.patientId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(patientId, age);
    }

    @Override
    public String toString() {
        return String.format("Patient[ID='%s', Name='%s', Age=%d, Complaint='%s']",
                patientId, name, age, chiefComplaint);
    }
}

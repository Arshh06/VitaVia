package com.vitavia;

import com.vitavia.domain.model.*;
import com.vitavia.domain.resource.BedResource;
import com.vitavia.domain.resource.MedicalResource;
import com.vitavia.domain.resource.SpecialistStaffResource;
import com.vitavia.domain.resource.VentilatorResource;
import com.vitavia.domain.routing.MockTrafficRoutingEngine;
import com.vitavia.domain.routing.RoutingEngine;
import com.vitavia.domain.triage.RuleBasedHeuristicTriageAssessor;
import com.vitavia.domain.triage.TriageAssessor;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("Object-Oriented Programming (OOP) Architectural Concept Verification")
class OOPConceptsVerificationTest {

    @Test
    @DisplayName("OOP Concept 1: Encapsulation - GeoPoint Boundary Validation & Geodesic Distance")
    void testEncapsulationGeoPoint() {
        // Validation boundary checks
        assertThrows(IllegalArgumentException.class, () -> new GeoPoint(95.0, 77.0), "Latitude > 90 must fail");
        assertThrows(IllegalArgumentException.class, () -> new GeoPoint(-91.0, 77.0), "Latitude < -90 must fail");
        assertThrows(IllegalArgumentException.class, () -> new GeoPoint(12.0, 190.0), "Longitude > 180 must fail");

        // Encapsulated state and haversine calculation
        GeoPoint origin = new GeoPoint(12.9700, 77.6000, "Trinity Junction");
        GeoPoint hospB = new GeoPoint(13.0080, 77.6250, "St. Jude Hospital");

        double distance = origin.distanceTo(hospB);
        assertTrue(distance > 4.0 && distance < 6.0, "Haversine distance should be ~5.0 km");
        assertEquals("Trinity Junction", origin.getAddress());
    }

    @Test
    @DisplayName("OOP Concept 1: Encapsulation - PatientVitals Invariants & Immutable Drift")
    void testEncapsulationPatientVitals() {
        assertThrows(IllegalArgumentException.class, () -> new PatientVitals(105.0, 80, 120, 80, 37.0), "SpO2 > 100 must fail");
        assertThrows(IllegalArgumentException.class, () -> new PatientVitals(-1.0, 80, 120, 80, 37.0), "SpO2 < 0 must fail");
        assertThrows(IllegalArgumentException.class, () -> new PatientVitals(98.0, 450, 120, 80, 37.0), "HR > 300 must fail");

        PatientVitals criticalVitals = new PatientVitals(87.5, 128, 88, 55, 38.4);
        assertTrue(criticalVitals.isSevereHypoxic(), "SpO2 87.5% must evaluate as severe hypoxia");
        assertTrue(criticalVitals.isHypotensive(), "SBP 88 must evaluate as hypotension");
        assertTrue(criticalVitals.isTachycardic(), "HR 128 must evaluate as tachycardia");

        // Immutable drift mutation
        PatientVitals drifted = criticalVitals.withDrift(2.0, -5, 4, 2, -0.2);
        assertEquals(89.5, drifted.getSpo2());
        assertEquals(123, drifted.getHeartRate());
        assertEquals(92, drifted.getSystolicBp());
        // Original remains untouched (Immutability)
        assertEquals(87.5, criticalVitals.getSpo2());
    }

    @Test
    @DisplayName("OOP Concept 1: Encapsulation - EmergencyMission State Machine Invariants")
    void testEncapsulationEmergencyMissionStateMachine() {
        EmergencyMission mission = new EmergencyMission(
                "EMERG-001", "AMB-07",
                PatientInfo.defaultPatient(),
                new PatientVitals(98.0, 75, 120, 80, 37.0),
                new GeoPoint(12.9700, 77.6000)
        );

        assertEquals(EmergencyStatus.CREATED, mission.getStatus());

        // Illegal transition test: Cannot jump from CREATED directly to COMPLETED or ARRIVED
        assertThrows(IllegalStateException.class, mission::completeMission,
                "Cannot jump directly from CREATED to COMPLETED without dispatch");
    }

    @Test
    @DisplayName("OOP Concept 2: Abstraction - Strategy Interfaces (RoutingEngine & TriageAssessor)")
    void testAbstractionContracts() {
        RoutingEngine routingEngine = new MockTrafficRoutingEngine();
        assertEquals("MOCK_TRAFFIC_ENGINE", routingEngine.getProviderName());

        TriageAssessor triageAssessor = new RuleBasedHeuristicTriageAssessor();
        assertEquals("HEURISTIC_FALLBACK", triageAssessor.getAssessorName());

        TriageAssessment assessment = triageAssessor.assess(
                new PatientVitals(87.0, 130, 85, 55, 38.5),
                PatientInfo.defaultPatient()
        );
        assertEquals(UrgencyLevel.CRITICAL, assessment.getUrgency());
        assertTrue(assessment.requiresIcu());
        assertTrue(assessment.requiresVentilator());
    }

    @Test
    @DisplayName("OOP Concept 3: Inheritance - MedicalResource Hierarchy (Bed, Ventilator, Staff)")
    void testInheritanceHierarchy() {
        MedicalResource bed = new BedResource("B1", "Trauma Bay 1", 10, 3, "ICU");
        MedicalResource vent = new VentilatorResource("V1", "Hamilton Ventilator", 5, 2, "Adult ICU", true);
        MedicalResource doc = new SpecialistStaffResource("D1", "Trauma Surgeon", 3, 1, "Trauma Surgery", "Dr. Rao");

        // Verify Inheritance (IS-A relationship)
        assertInstanceOf(MedicalResource.class, bed);
        assertInstanceOf(MedicalResource.class, vent);
        assertInstanceOf(MedicalResource.class, doc);

        assertEquals(10, bed.getTotalCapacity());
        assertEquals(3, bed.getAvailableUnits());
        assertTrue(bed.isAvailable());
    }

    @Test
    @DisplayName("OOP Concept 4: Polymorphism - Overridden allocate() and Resource Typing")
    void testPolymorphicAllocation() {
        List<MedicalResource> resources = List.of(
                new BedResource("B-ICU", "ICU Bed", 5, 1, "ICU"),
                new VentilatorResource("V-ICU", "Ventilator", 4, 1, "High Flow", true),
                new SpecialistStaffResource("S-DOC", "Trauma Doc", 2, 1, "Emergency", "Dr. Khan")
        );

        // Polymorphic allocation across heterogeneous medical resource types
        for (MedicalResource resource : resources) {
            assertTrue(resource.allocate(), "Allocation should succeed when units available");
            assertEquals(0, resource.getAvailableUnits(), "Available units should decrement to 0");
            assertFalse(resource.allocate(), "Second allocation must fail when 0 available");
            assertTrue(resource.release(), "Release must restore unit");
            assertEquals(1, resource.getAvailableUnits());
        }

        assertEquals("ICU", resources.get(0).getResourceType());
        assertEquals("Ventilator", resources.get(1).getResourceType());
        assertEquals("Emergency Doctor", resources.get(2).getResourceType());
    }
}

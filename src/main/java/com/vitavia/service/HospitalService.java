package com.vitavia.service;

import com.vitavia.domain.model.GeoPoint;
import com.vitavia.domain.model.Hospital;
import com.vitavia.domain.resource.BedResource;
import com.vitavia.domain.resource.SpecialistStaffResource;
import com.vitavia.domain.resource.VentilatorResource;
import com.vitavia.entity.HospitalEntity;
import com.vitavia.repository.HospitalEntityRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Hospital Registry & Capacity Management Service.
 * Manages hospital facilities, coordinates, polymorphic medical resources, and database persistence.
 */
@Service
public class HospitalService {

    private final HospitalEntityRepository hospitalEntityRepository;
    private final Map<String, Hospital> activeHospitals = new ConcurrentHashMap<>();

    public HospitalService(HospitalEntityRepository hospitalEntityRepository) {
        this.hospitalEntityRepository = hospitalEntityRepository;
    }

    @PostConstruct
    public void initHospitals() {
        resetHospitals();
    }

    public synchronized void resetHospitals() {
        activeHospitals.clear();

        List<Hospital> defaults = List.of(
                createHospital("HOSP-A", "Metro City Central Hospital",
                        12.9760, 77.5730, "MG Road Congested Downtown Grid",
                        "+91-80-2222-1001", "Level 1 Comprehensive Trauma Center",
                        30, 4, 12, 2, 8, 2, true),

                createHospital("HOSP-B", "St. Jude Super Specialty Hospital",
                        13.0080, 77.6250, "Expressway Corridor North (Arterial Green Wave)",
                        "+91-80-3333-2002", "Level 1 Advanced Cardiac & Trauma Care",
                        25, 8, 15, 5, 10, 4, true),

                createHospital("HOSP-C", "Apex Community Medical Center",
                        12.9630, 77.5880, "South Avenue Local Sector",
                        "+91-80-4444-3003", "Level 3 Urgent Care Clinic",
                        15, 3, 4, 0, 2, 0, true), // No ICU, No Ventilator

                createHospital("HOSP-D", "Lifeline Memorial Health",
                        12.9350, 77.6150, "Ring Road Outer Belt",
                        "+91-80-5555-4004", "Level 2 Regional Hospital",
                        20, 5, 6, 1, 4, 0, true), // Ventilator unavailable

                createHospital("HOSP-E", "Grace Emergency & Trauma Institute",
                        13.0250, 77.5650, "Tech Park Arterial Bypass",
                        "+91-80-6666-5005", "Level 1 Tertiary Emergency",
                        40, 12, 20, 7, 15, 6, true)
        );

        for (Hospital h : defaults) {
            activeHospitals.put(h.getId(), h);
            // Alias for backwards compatibility with hospital dashboard HOSP001-HOSP005 notation
            String alias = toLegacyId(h.getId());
            if (alias != null) {
                activeHospitals.put(alias, h);
            }
            saveEntity(h);
        }
    }

    private String toLegacyId(String id) {
        return switch (id) {
            case "HOSP-A" -> "HOSP001";
            case "HOSP-B" -> "HOSP002";
            case "HOSP-C" -> "HOSP003";
            case "HOSP-D" -> "HOSP004";
            case "HOSP-E" -> "HOSP005";
            default -> null;
        };
    }

    private Hospital createHospital(String id, String name, double lat, double lon, String address,
                                   String contact, String traumaLevel, int totalBeds, int availBeds,
                                   int totalIcu, int availIcu, int totalVent, int availVent, boolean doctor) {
        Hospital hospital = new Hospital(id, name, new GeoPoint(lat, lon, address), contact, traumaLevel);
        hospital.addResource(new BedResource(id + "-BED", name + " Emergency Bays", totalBeds, availBeds, "EMERGENCY_BED"));
        hospital.addResource(new BedResource(id + "-ICU", name + " ICU Ward", totalIcu, availIcu, "ICU"));
        hospital.addResource(new VentilatorResource(id + "-VENT", name + " Ventilators", totalVent, availVent, "Adult ICU Ventilator", true));
        hospital.addResource(new SpecialistStaffResource(id + "-DOC", name + " Emergency Team", 5, doctor ? 3 : 0, "Emergency Medicine", "Dr. Lead Physician"));
        return hospital;
    }

    private void saveEntity(Hospital h) {
        HospitalEntity entity = new HospitalEntity(
                h.getId(), h.getName(), h.getLocation().getLatitude(), h.getLocation().getLongitude(),
                h.getLocation().getAddress(), h.getContactNumber(), h.getTraumaLevel(),
                20, h.getAvailableBeds(), 10, h.getAvailableIcuBeds(), 8, h.getAvailableVentilators(),
                h.isDoctorAvailable()
        );
        hospitalEntityRepository.save(entity);
    }

    public List<Hospital> getAllHospitals() {
        // Return unique hospitals by primary ID
        return activeHospitals.values().stream()
                .filter(h -> h.getId().startsWith("HOSP-"))
                .distinct()
                .sorted(Comparator.comparing(Hospital::getId))
                .toList();
    }

    public Optional<Hospital> getHospitalById(String id) {
        if (id == null) return Optional.empty();
        return Optional.ofNullable(activeHospitals.get(id));
    }

    public synchronized Hospital updateHospitalCapacity(String hospitalId, Boolean emergencyBed, Boolean icu,
                                                       Boolean ventilator, Boolean doctor,
                                                       Integer availBeds, Integer availIcu, Integer availVent) {
        Hospital hosp = activeHospitals.get(hospitalId);
        if (hosp == null) {
            return null;
        }
        hosp.updateCapacity(emergencyBed, icu, ventilator, doctor, availBeds, availIcu, availVent);
        saveEntity(hosp);
        return hosp;
    }
}

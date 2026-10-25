package com.vitavia.controller;

import com.vitavia.domain.model.Hospital;
import com.vitavia.dto.HospitalUpdateRequest;
import com.vitavia.service.HospitalService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;

@RestController
@CrossOrigin(origins = "*")
public class HospitalApiController {

    private final HospitalService hospitalService;

    public HospitalApiController(HospitalService hospitalService) {
        this.hospitalService = hospitalService;
    }

    @GetMapping({"/api/v1/hospitals", "/api/hospitals", "/hospitals"})
    public List<Map<String, Object>> listHospitals() {
        return hospitalService.getAllHospitals().stream()
                .map(this::formatHospital)
                .toList();
    }

    @GetMapping({"/api/v1/hospitals/{id}", "/api/hospitals/{id}"})
    public ResponseEntity<Map<String, Object>> getHospital(@PathVariable("id") String id) {
        return hospitalService.getHospitalById(id)
                .map(h -> ResponseEntity.ok(formatHospital(h)))
                .orElse(ResponseEntity.notFound().build());
    }

    @PutMapping({"/api/v1/hospitals/{id}", "/api/hospitals/{id}"})
    public ResponseEntity<Map<String, Object>> updateHospital(@PathVariable("id") String id,
                                                              @RequestBody HospitalUpdateRequest req) {
        Hospital updated = hospitalService.updateHospitalCapacity(
                id,
                req.emergencyBedAvailable(),
                req.icuAvailable(),
                req.ventilatorAvailable(),
                req.emergencyDoctorAvailable(),
                req.availableEmergencyBeds(),
                req.availableIcuBeds(),
                req.availableVentilators()
        );
        if (updated == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(formatHospital(updated));
    }

    @PostMapping({"/api/v1/hospitals/reset", "/api/hospitals/reset"})
    public List<Map<String, Object>> resetHospitals() {
        hospitalService.resetHospitals();
        return listHospitals();
    }

    private Map<String, Object> formatHospital(Hospital h) {
        return Map.of(
                "id", h.getId(),
                "hospital_id", h.getId(),
                "name", h.getName(),
                "location", Map.of(
                        "latitude", h.getLocation().getLatitude(),
                        "longitude", h.getLocation().getLongitude(),
                        "address", h.getLocation().getAddress()
                ),
                "infrastructure", Map.of(
                        "emergency_bed_available", h.getAvailableBeds() > 0,
                        "icu_available", h.getAvailableIcuBeds() > 0,
                        "ventilator_available", h.getAvailableVentilators() > 0,
                        "emergency_doctor_available", h.isDoctorAvailable(),
                        "total_emergency_beds", 20,
                        "available_emergency_beds", h.getAvailableBeds(),
                        "total_icu_beds", 10,
                        "available_icu_beds", h.getAvailableIcuBeds(),
                        "total_ventilators", 8,
                        "available_ventilators", h.getAvailableVentilators()
                ),
                "availability", Map.of(
                        "emergency_bed", h.getAvailableBeds() > 0,
                        "icu", h.getAvailableIcuBeds() > 0,
                        "ventilator", h.getAvailableVentilators() > 0,
                        "emergency_team", h.isDoctorAvailable()
                ),
                "contact_number", h.getContactNumber(),
                "trauma_level", h.getTraumaLevel()
        );
    }
}

package com.vitavia.repository;

import com.vitavia.entity.EmergencyRecordEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface EmergencyRecordRepository extends JpaRepository<EmergencyRecordEntity, Long> {
    Optional<EmergencyRecordEntity> findByEmergencyId(String emergencyId);
    List<EmergencyRecordEntity> findAllByOrderByStartedAtDesc();
    List<EmergencyRecordEntity> findTop20ByOrderByStartedAtDesc();
    List<EmergencyRecordEntity> findBySelectedHospitalIdOrderByStartedAtDesc(String hospitalId);
}

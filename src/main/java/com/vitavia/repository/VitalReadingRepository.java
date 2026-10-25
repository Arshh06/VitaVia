package com.vitavia.repository;

import com.vitavia.entity.VitalReadingEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface VitalReadingRepository extends JpaRepository<VitalReadingEntity, Long> {
    List<VitalReadingEntity> findByEmergencyIdOrderByRecordedAtAsc(String emergencyId);
}

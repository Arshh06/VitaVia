package com.vitavia.repository;

import com.vitavia.entity.AmbulanceLocationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AmbulanceLocationRepository extends JpaRepository<AmbulanceLocationEntity, Long> {
    List<AmbulanceLocationEntity> findByEmergencyIdOrderByRecordedAtAsc(String emergencyId);
}

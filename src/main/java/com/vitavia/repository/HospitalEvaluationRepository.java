package com.vitavia.repository;

import com.vitavia.entity.HospitalEvaluationEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface HospitalEvaluationRepository extends JpaRepository<HospitalEvaluationEntity, Long> {
    List<HospitalEvaluationEntity> findByEmergencyId(String emergencyId);
}

package com.vitavia.repository;

import com.vitavia.entity.HospitalEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface HospitalEntityRepository extends JpaRepository<HospitalEntity, String> {
    Optional<HospitalEntity> findById(String id);
}

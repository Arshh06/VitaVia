package com.vitavia.controller;
 
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.time.Instant;
import java.util.Map;

/**
 * Centralized Global Exception Handler for REST Controllers.
 * Translates domain validation and lifecycle state exceptions into appropriate HTTP status codes.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalArgument(IllegalArgumentException ex) {
        logger.warn("Validation / Bad Request Error: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of(
                "error", "BAD_REQUEST",
                "message", ex.getMessage(),
                "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<Map<String, Object>> handleIllegalState(IllegalStateException ex) {
        logger.warn("Lifecycle State Conflict: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.CONFLICT).body(Map.of(
                "error", "CONFLICT_OR_ILLEGAL_STATE",
                "message", ex.getMessage(),
                "timestamp", Instant.now().toString()
        ));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleGenericException(Exception ex) {
        logger.error("Unhandled Server Exception: ", ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(Map.of(
                "error", "INTERNAL_SERVER_ERROR",
                "message", ex.getMessage() != null ? ex.getMessage() : "An unexpected server error occurred",
                "timestamp", Instant.now().toString()
        ));
    }
}

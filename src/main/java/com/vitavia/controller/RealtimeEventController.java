package com.vitavia.controller;

import com.vitavia.service.RealtimeEventService;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

/**
 * Server-Sent Events (SSE) Streaming Controller.
 * Provides a live reactive data stream to connected ambulance and hospital dashboards.
 */
@RestController
@CrossOrigin(origins = "*")
public class RealtimeEventController {

    private final RealtimeEventService eventService;

    public RealtimeEventController(RealtimeEventService eventService) {
        this.eventService = eventService;
    }

    @GetMapping(value = {"/api/v1/events/stream", "/api/events/stream"}, produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamEvents() {
        return eventService.subscribe();
    }
}

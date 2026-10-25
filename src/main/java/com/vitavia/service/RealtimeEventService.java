package com.vitavia.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Real-Time Event Bus using Server-Sent Events (SSE).
 * Delivers instant updates to connected ambulance and hospital control-room dashboards.
 */
@Service
public class RealtimeEventService {

    private static final Logger logger = LoggerFactory.getLogger(RealtimeEventService.class);
    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    public SseEmitter subscribe() {
        SseEmitter emitter = new SseEmitter(180_000L); // 3 minutes timeout

        emitter.onCompletion(() -> emitters.remove(emitter));
        emitter.onTimeout(() -> {
            emitter.complete();
            emitters.remove(emitter);
        });
        emitter.onError(e -> emitters.remove(emitter));

        emitters.add(emitter);

        try {
            emitter.send(SseEmitter.event()
                    .name("CONNECTED")
                    .data("{\"status\":\"CONNECTED\",\"message\":\"Subscribed to VitaVia Live Event Stream\"}"));
        } catch (IOException e) {
            emitters.remove(emitter);
        }

        return emitter;
    }

    public void broadcast(String eventName, Object eventData) {
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name(eventName)
                        .data(eventData));
            } catch (Exception e) {
                emitters.remove(emitter);
            }
        }
    }
}

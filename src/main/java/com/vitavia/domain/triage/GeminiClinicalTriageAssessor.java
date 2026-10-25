package com.vitavia.domain.triage;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.vitavia.domain.model.PatientInfo;
import com.vitavia.domain.model.PatientVitals;
import com.vitavia.domain.model.TriageAssessment;
import com.vitavia.domain.model.UrgencyLevel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Gemini AI Clinical Decision Support Implementation.
 * Demonstrates:
 * - Polymorphism: Implements TriageAssessor with Google Gemini LLM API calls.
 * - Fault Tolerance: Automatically falls back to RuleBasedHeuristicTriageAssessor if API key is missing or call fails.
 */
@Component("geminiClinicalTriageAssessor")
public class GeminiClinicalTriageAssessor implements TriageAssessor {

    private static final Logger logger = LoggerFactory.getLogger(GeminiClinicalTriageAssessor.class);
    public static final String ASSESSOR_NAME = "GEMINI_API";

    private final String apiKey;
    private final RuleBasedHeuristicTriageAssessor fallbackAssessor;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;

    public GeminiClinicalTriageAssessor(@Value("${vitavia.gemini.api-key:}") String apiKey,
                                        RuleBasedHeuristicTriageAssessor fallbackAssessor) {
        this.apiKey = apiKey != null ? apiKey.trim() : "";
        this.fallbackAssessor = fallbackAssessor;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(4))
                .build();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public TriageAssessment assess(PatientVitals vitals, PatientInfo patient) {
        if (apiKey.isEmpty()) {
            logger.info("GEMINI_API_KEY not configured. Using rule-based heuristic triage fallback.");
            return fallbackAssessor.assess(vitals, patient);
        }

        try {
            String prompt = String.format("""
                    You are a clinical decision-support AI assisting an emergency ambulance dispatch system.
                    Analyze the following live patient telemetry:
                    
                    PATIENT VITALS:
                    - SpO2 (Oxygen Saturation): %.1f%%
                    - Heart Rate: %d BPM
                    - Blood Pressure: %d/%d mmHg
                    - Body Temperature: %.1f °C
                    - Chief Complaint: %s
                    - Patient Age: %d
                    
                    Return ONLY a valid JSON object with the following exact structure:
                    {
                      "urgency": "CRITICAL" | "HIGH" | "MODERATE" | "LOW",
                      "required_infrastructure": ["Emergency Bed", "ICU", "Ventilator", "Emergency Doctor"],
                      "summary": "Concise 1-2 sentence clinical summary of patient condition.",
                      "clinical_notes": "Key clinical reasoning for required infrastructure."
                    }
                    
                    Criteria for required_infrastructure:
                    - Include "Emergency Bed" and "Emergency Doctor" for all acute cases.
                    - Include "ICU" if the patient shows shock, hypoxemia (SpO2 < 92%%), severe hypertension/hypotension, or severe tachycardia.
                    - Include "Ventilator" if the patient has severe hypoxia (SpO2 < 89%%) or respiratory failure.
                    Do not output markdown code blocks. Output plain JSON.
                    """,
                    vitals.getSpo2(),
                    vitals.getHeartRate(),
                    vitals.getSystolicBp(),
                    vitals.getDiastolicBp(),
                    vitals.getTemperature(),
                    patient != null ? patient.getChiefComplaint() : "Emergency transit",
                    patient != null ? patient.getAge() : 45
            );

            Map<String, Object> requestPayload = Map.of(
                    "contents", List.of(Map.of(
                            "parts", List.of(Map.of("text", prompt))
                    ))
            );

            String requestBody = objectMapper.writeValueAsString(requestPayload);

            String url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + apiKey;

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .header("Content-Type", "application/json")
                    .timeout(Duration.ofSeconds(6))
                    .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                JsonNode root = objectMapper.readTree(response.body());
                JsonNode candidates = root.path("candidates");
                if (candidates.isArray() && !candidates.isEmpty()) {
                    String text = candidates.get(0).path("content").path("parts").get(0).path("text").asText("");
                    text = cleanJsonMarkdown(text);

                    JsonNode parsed = objectMapper.readTree(text);
                    String urgencyStr = parsed.path("urgency").asText("HIGH").toUpperCase();
                    UrgencyLevel urgency;
                    try {
                        urgency = UrgencyLevel.valueOf(urgencyStr);
                    } catch (IllegalArgumentException e) {
                        urgency = UrgencyLevel.HIGH;
                    }

                    List<String> requiredInfra = new ArrayList<>();
                    JsonNode infraNode = parsed.path("required_infrastructure");
                    if (infraNode.isArray()) {
                        for (JsonNode item : infraNode) {
                            requiredInfra.add(item.asText());
                        }
                    }
                    if (requiredInfra.isEmpty()) {
                        requiredInfra.add("Emergency Bed");
                        requiredInfra.add("Emergency Doctor");
                    }

                    String summary = parsed.path("summary").asText("Patient requires emergency medical evaluation.");
                    String notes = parsed.path("clinical_notes").asText("Evaluated by Gemini Clinical Decision Support.");

                    return new TriageAssessment(urgency, requiredInfra, summary, notes, ASSESSOR_NAME);
                }
            }
            logger.warn("Gemini API returned status code {}. Falling back to heuristic triage.", response.statusCode());
        } catch (Exception exc) {
            logger.warn("Gemini API invocation failed ({}: {}). Falling back to heuristic triage.",
                    exc.getClass().getSimpleName(), exc.getMessage());
        }

        return fallbackAssessor.assess(vitals, patient);
    }

    private String cleanJsonMarkdown(String raw) {
        String cleaned = raw.trim();
        if (cleaned.startsWith("```json")) {
            cleaned = cleaned.substring(7);
        } else if (cleaned.startsWith("```")) {
            cleaned = cleaned.substring(3);
        }
        if (cleaned.endsWith("```")) {
            cleaned = cleaned.substring(0, cleaned.length() - 3);
        }
        return cleaned.trim();
    }

    @Override
    public String getAssessorName() {
        return ASSESSOR_NAME;
    }
}

package com.vitavia.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

/**
 * Controller serving the Ambulance Command Center and Hospital Control Room Dashboards.
 */
@Controller
public class DashboardViewController {

    @GetMapping({"/", "/ambulance"})
    public String ambulanceDashboard() {
        return "ambulance";
    }

    @GetMapping("/hospital")
    public String hospitalDashboard() {
        return "hospital";
    }
}

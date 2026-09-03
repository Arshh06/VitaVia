"""
Traffic-Aware Routing Module for VitaVia.
Integrates Google Maps Routes API with an intelligent, highly realistic
Mock Traffic Engine fallback for offline local demonstrations.
"""

import os
import math
import logging
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv

from backend.models import GeoPoint

load_dotenv()
logger = logging.getLogger("VitaVia.Routing")


def haversine_distance_km(p1: GeoPoint, p2: GeoPoint) -> float:
    """Calculate the Great Circle distance between two coordinates in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    d_lat = math.radians(p2.latitude - p1.latitude)
    d_lon = math.radians(p2.longitude - p1.longitude)
    
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(p1.latitude)) * math.cos(math.radians(p2.latitude)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)


# Deterministic traffic profiles for simulated demonstration hospitals
# Simulates congested city centers vs clear arterial expressways
SIMULATED_TRAFFIC_CONDITIONS: Dict[str, Dict[str, Any]] = {
    "HOSP-A": {
        "condition": "HEAVY",
        "speed_kmh": 11.0,     # Heavy downtown bottleneck
        "road_factor": 1.35     # Urban street grid tortuosity
    },
    "HOSP-B": {
        "condition": "LOW",
        "speed_kmh": 36.0,     # Elevated corridor / green wave signal
        "road_factor": 1.18
    },
    "HOSP-C": {
        "condition": "LOW",
        "speed_kmh": 20.0,     # Short local connector
        "road_factor": 1.22
    },
    "HOSP-D": {
        "condition": "MODERATE",
        "speed_kmh": 22.0,     # Moderate ring road flow
        "road_factor": 1.28
    },
    "HOSP-E": {
        "condition": "LOW",
        "speed_kmh": 34.0,     # Tech park expressway
        "road_factor": 1.20
    }
}


def _mock_route_calculation(
    origin: GeoPoint,
    destination: GeoPoint,
    hospital_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Simulates realistic road network distance and traffic-weighted ETA.
    """
    raw_dist = haversine_distance_km(origin, destination)
    
    traffic_profile = SIMULATED_TRAFFIC_CONDITIONS.get(hospital_id or "", {
        "condition": "MODERATE",
        "speed_kmh": 22.0,
        "road_factor": 1.3
    })
    
    condition = traffic_profile["condition"]
    speed_kmh = traffic_profile["speed_kmh"]
    road_factor = traffic_profile["road_factor"]
    
    # Road driving distance is typically 20-35% longer than straight-line distance
    road_distance_km = round(max(0.5, raw_dist * road_factor), 2)
    
    # ETA in minutes = (distance / speed) * 60 + base dispatch / intersection buffer
    traffic_multiplier = {
        "LOW": 1.0,
        "MODERATE": 1.25,
        "HEAVY": 1.85,
        "SEVERE": 2.4
    }.get(condition, 1.2)
    
    travel_time_minutes = (road_distance_km / speed_kmh) * 60.0
    eta_minutes = round(max(2.0, travel_time_minutes), 1)
    
    return {
        "distance_km": road_distance_km,
        "eta_minutes": eta_minutes,
        "traffic_condition": condition,
        "source": "MOCK_TRAFFIC_ENGINE"
    }


def calculate_route(
    origin: GeoPoint,
    destination: GeoPoint,
    hospital_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes distance and traffic-aware travel time between origin and destination.
    Uses Google Maps Routes API if key is present, otherwise uses high-fidelity Mock Engine.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    
    if not api_key:
        return _mock_route_calculation(origin, destination, hospital_id)
        
    try:
        # Google Maps Routes API (Directions v2)
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.staticDuration"
        }
        body = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": origin.latitude,
                        "longitude": origin.longitude
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": destination.latitude,
                        "longitude": destination.longitude
                    }
                }
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL"
        }
        
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, json=body, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                routes = data.get("routes", [])
                if routes:
                    primary_route = routes[0]
                    dist_meters = primary_route.get("distanceMeters", 0)
                    dist_km = round(dist_meters / 1000.0, 2)
                    
                    # duration is formatted as "840s"
                    duration_str = primary_route.get("duration", "0s").replace("s", "")
                    duration_sec = float(duration_str) if duration_str else 0.0
                    eta_mins = round(duration_sec / 60.0, 1)
                    
                    static_str = primary_route.get("staticDuration", duration_str).replace("s", "")
                    static_sec = float(static_str) if static_str else duration_sec
                    
                    # Derive traffic condition ratio
                    ratio = (duration_sec / static_sec) if static_sec > 0 else 1.0
                    if ratio >= 1.5:
                        condition = "HEAVY"
                    elif ratio >= 1.2:
                        condition = "MODERATE"
                    else:
                        condition = "LOW"
                        
                    return {
                        "distance_km": dist_km,
                        "eta_minutes": eta_mins,
                        "traffic_condition": condition,
                        "source": "GOOGLE_ROUTES_API"
                    }
    except Exception as exc:
        logger.warning(f"Google Routes API call failed ({exc}). Using mock routing fallback.")
        
    return _mock_route_calculation(origin, destination, hospital_id)

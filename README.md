# 🚑 VITAVIA: AI-Assisted Connected Ambulance & Traffic-Aware Routing

**VITAVIA** is an intelligent emergency response platform that connects ambulances, real-time IoT patient telemetry, AI clinical decision support, and dynamic traffic-aware routing to direct emergency patients to the **fastest suitable hospital** rather than simply the closest one.

---

## 🌟 Key Features

1. **Simulated IoT Medical Telemetry**: Streams SpO2, Heart Rate, Blood Pressure (Systolic/Diastolic), and Body Temperature with continuous physiologic drift.
2. **Gemini Clinical Decision Support**: Evaluates patient distress, computes clinical urgency levels, and identifies mandatory hospital infrastructure (e.g. ICU, Ventilator, Emergency Trauma Bay) with an intelligent heuristic fallback.
3. **Deterministic Multi-Hospital Resource Verification**: Checks real-time bed, ICU, and specialist availability across candidate hospitals.
4. **Traffic-Aware Routing Engine**: Integrates Google Maps Routes API with a high-fidelity local Mock Traffic Engine fallback (simulating urban congestion, arterial expressways, and bottleneck corridors).
5. **Fastest-Suitable Hospital Optimization**: Selects the hospital with the lowest ETA (Estimated Travel Time) that satisfies 100% of the patient's clinical infrastructure needs.
6. **Hospital Handshake & Acknowledgment**: Generates formal trauma bay reservation and team readiness confirmation.
7. **Interactive Command Dashboard**: Streamlit-based operations center with live telemetry gauges, hospital comparison matrix, and real-time GIS map.

---

## 🏗️ System Architecture

```
                                  +-----------------------+
                                  |   Patient / Request   |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |  Ambulance Simulator  |
                                  | - Real-time GPS       |
                                  | - Simulated IoT Vitals|
                                  +-----------+-----------+
                                              | (HTTP / REST)
                                              v
+------------------------------------------------------------------------------------------+
|                                    FASTAPI BACKEND                                       |
|                                                                                          |
|  1. Ingests Patient Vitals & Live GPS                                                    |
|  2. Gemini AI Analysis (Clinical Decision Support)                                       |
|     --> Extracts urgency level, required infrastructure, and clinical summary            |
|  3. Deterministic Hospital Eligibility Filter                                            |
|     --> Matches required infrastructure against live hospital capacity (ICU, Beds, etc.) |
|  4. Traffic-Aware Routing Engine                                                         |
|     --> Google Maps Routes API with smart Mock Traffic fallback                          |
|  5. Fastest Suitable Hospital Selection Algorithm                                        |
|     --> Optimizes for lowest ETA among eligible hospitals (not just shortest distance)   |
|  6. Hospital Dispatch & Acknowledgment Handshake                                         |
+------------------------------------------------------------------------------------------+
                                              |
                                              v
                                  +-----------------------+
                                  |  Streamlit Dashboard  |
                                  | - Emergency Control   |
                                  | - Live Vitals Monitor |
                                  | - AI Insights Panel   |
                                  | - Hospital Matrix &   |
                                  |   Live Route Map      |
                                  +-----------------------+
```

---

## 🚀 Quick Start (Local Setup)

### 1. Install Dependencies
Make sure you have Python 3.9+ installed.

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (Optional)
The system is designed to run 100% locally out-of-the-box using simulated fallbacks. If you have API keys:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Add your keys in `.env`:
   ```ini
   GEMINI_API_KEY=your_google_gemini_api_key_here
   GOOGLE_MAPS_API_KEY=your_google_maps_routes_key_here
   ```

---

## 🖥️ Running the Application

### Step 1: Start the FastAPI Backend
In your first terminal:
```bash
uvicorn backend.main:app --reload --port 8000
```
- API Docs (Swagger UI): `http://127.0.0.1:8000/docs`

### Step 2: Start the Streamlit Dashboard
In your second terminal:
```bash
streamlit run frontend/app.py
```
- Open browser at: `http://localhost:8501`

### Step 3 (Optional): Run Standalone Ambulance Simulator
In your third terminal (if you wish to test pure IoT telemetry broadcasting):
```bash
python -m ambulance.simulator
```

---

## 🧪 Demonstration Scenarios

| Scenario | Clinical Findings | Gemini Assessment | Eligible Hospitals | Decision Result |
| :--- | :--- | :--- | :--- | :--- |
| **Acute Respiratory Distress & Shock** | SpO2: 87.5%, HR: 128, BP: 92/58 | **CRITICAL** (Requires ICU + Ventilator) | Rejects Hospital C (No ICU) and Hospital D (No Vent). | Selects **St. Jude (HOSP-B)**: 5.1 km, Low Traffic, **ETA 9.8 min** over Hospital A (3.2 km, Heavy Traffic, ETA 17.5 min). |
| **Cardiac / Hypertensive Emergency** | SpO2: 91%, HR: 118, BP: 88/54 | **HIGH** (Requires ICU + Bed) | Rejects Hospital C. | Routes to fastest ICU facility. |
| **Moderate Extremity Trauma** | SpO2: 98%, HR: 84, BP: 124/78 | **MODERATE** (Emergency Bed only) | All hospitals eligible. | Routes to **Apex Community (HOSP-C)**: **ETA 7.0 min** (Closest and fastest). |

---

## 📂 Project Structure

```text
VitaVia/
│
├── backend/
│   ├── __init__.py
│   ├── main.py             # FastAPI entry point & API endpoints
│   ├── models.py           # Pydantic schemas (Vitals, Telemetry, Hospital, Routing)
│   ├── hospitals.py        # Hospital registry & infrastructure capacity manager
│   ├── gemini_service.py   # Gemini AI clinical analysis + heuristic fallback
│   ├── routing.py          # Google Maps Routes API client + mock traffic engine
│   └── decision.py         # Deterministic hospital eligibility & fastest-ETA selector
│
├── ambulance/
│   ├── __init__.py
│   └── simulator.py        # IoT vital signs generator & transit movement simulator
│
├── frontend/
│   └── app.py              # Streamlit emergency response command center
│
├── .env.example            # Environment configuration template
├── .gitignore              # Ignored files (.env, __pycache__, etc.)
├── requirements.txt        # Python dependencies
└── README.md               # Documentation
```

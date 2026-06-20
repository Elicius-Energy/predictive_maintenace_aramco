# LEDL Predictive Maintenance Dashboard

Professional IIoT Condition Monitoring & AI-Driven Diagnostics Platform.

## 🚀 Overview

This system provides real-time monitoring and predictive maintenance for critical industrial assets (pumps, compressors, fans). It integrates high-frequency vibration and electrical data with a Retrieval-Augmented Generation (RAG) system using Anthropic Claude to provide actionable, physics-grounded engineering insights.

### Key Features
- **Real-time Ingestion**: Seamlessly handles ESP32 MQTT streams or falls back to physics-accurate simulation.
- **Advanced Feature Engineering**: Computes RMS, Kurtosis, Crest Factor, and FFT Peak Detection.
- **Anomaly Detection**: ISO 10816 threshold monitoring combined with Isolation Forest ML models.
- **AI Diagnostics (RAG)**: Claude-3.5 analyzes current signatures against a local knowledge base of bearing diagnostics and vibration standards.
- **Premium UI**: Dark industrial SCADA-style dashboard with high-performance Recharts visualizations.

## 🛠 Setup Instructions

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env` in the root directory and add your Anthropic API Key.
```bash
cp .env.example .env
```

### 3. Running the System (Local)

**Start Backend:**
```bash
cd backend
python -m app.main
```

**Start Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### 4. Running with Docker
```bash
docker-compose up --build
```

## 📊 Knowledge Base
The RAG system is pre-loaded with document chunks in `backend/data/knowledge`:
- `bearing_diagnostics.txt`: Fault progression and frequency signatures.
- `vibration_analysis.txt`: ISO 10816 standards and modal analysis.
- `electrical_faults.txt`: MCSA and power quality metrics.
- `predictive_maintenance_guide.txt`: General PdM methodology.

## 🛡️ LEDL Demo Specs
- **Facility**: Ras Tanura Refinery
- **Unit**: Processing Unit 3 (Hydrocracker)
- **Asset**: Machine_5 (Centrifugal Pump P-105)
- **Sample Rate**: 1s (Dashboard) / 10ms (Feature Extraction)

---
© 2026 Elicius Energy. Real-time Industrial Intelligence.

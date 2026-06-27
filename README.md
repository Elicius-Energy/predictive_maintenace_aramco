# LEDL Predictive Maintenance Dashboard

Professional IIoT Condition Monitoring & AI-Driven Diagnostics Platform.

## 🚀 Overview

This system provides real-time monitoring and predictive maintenance for critical industrial assets (pumps, compressors, fans). It integrates high-frequency vibration and electrical data with a Retrieval-Augmented Generation (RAG) system using OpenAI to provide actionable, physics-grounded engineering insights.

### Key Features
- **Real-time Ingestion**: Seamlessly handles ESP32 MQTT streams or falls back to physics-accurate simulation.
- **Advanced Feature Engineering**: Computes RMS, Kurtosis, Crest Factor, and FFT Peak Detection.
- **Anomaly Detection**: ISO 10816 threshold monitoring combined with Isolation Forest ML models.
- **AI Diagnostics (RAG)**: GPT-4o analyzes current signatures against a local knowledge base of bearing diagnostics and vibration standards.
- **Premium UI**: Dark industrial SCADA-style dashboard with high-performance Recharts visualizations.

## 🏗 Architecture
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Recharts
- **Backend**: FastAPI, SQLite (WAL mode), Pydantic
- **AI Engine**: Sentence Transformers (local FAISS index) + OpenAI GPT-4o
- **IoT Broker**: Eclipse Mosquitto (MQTT)
- **Deployment**: Docker Compose, Nginx Reverse Proxy

## 🛠 Setup & Deployment

The system is designed to run in isolated Docker containers for robust production deployment.

### Quick Start (Local Docker)
1. Copy `.env.example` to `.env` and add your OpenAI API Key.
2. Build and start the containers:
```bash
docker-compose up --build -d
```
3. Access the dashboard at `http://localhost:8080`.

### AWS EC2 Production Deployment
For complete instructions on deploying to an AWS EC2 instance, including security groups, initial server setup, and backup automation, please see the [AWS_DEPLOYMENT_GUIDE.md](./AWS_DEPLOYMENT_GUIDE.md).

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

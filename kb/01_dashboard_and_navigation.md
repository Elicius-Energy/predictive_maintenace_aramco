# LEDL Energy Monitoring System - Dashboard & Navigation Guide

## Welcome to the LEDL Motor Energy Monitoring Platform
This platform is engineered by M/s. Lakshmi Electrical Drives Pvt Ltd (LEDL) for the Energy Audit Department.
It provides real-time condition monitoring, electrical power quality analysis, wiring fault diagnostics, and automated motor energy reports for industrial induction motors.

## System Navigation
The interface has been intentionally streamlined to avoid complex menus. After logging in, there are exactly three pages accessible from the top navigation bar:

1. **Configuration (`/config`)**:
   - Manages device identity, customer details, motor nameplate specifications, machine parameters, inverter details, service personnel, commercial tariff, and fault alarm thresholds.
   - Contains the **Mark Installation OK** button to establish a baseline after physical installation.

2. **Dashboard (`/dashboard`)**:
   - The primary operational screen.
   - Displays real-time device status banner with per-phase CT and Voltage clip health chips.
   - Six live measurement cards: Voltage (V), Current (A), Active Power (kW), Energy (kWh), Power Factor (PF), and Frequency (Hz).
   - Interactive trend charts with flexible time window filters (Last 1 h, 8 h, 24 h, 7 d, Custom) and parameter chips.
   - Period summary strip summarizing total energy consumption and idle time for the active analysis window.

3. **Reports & Downloads (`/reports`)**:
   - Prepares and exports standard LEDL Energy Audit reports in Microsoft Excel (`.xlsx`) format.
   - Supports Before vs. After motor energy saving and Return on Investment (ROI) analysis.
   - Live preview card displaying study calculations before downloading.
   - Historical report archives for instantaneous re-download.
   - Raw time-series data export in `.xlsx` and `.csv`.

## Multi-Device Switching
- The device selector dropdown located in the top navigation bar allows instantaneous switching between any number of connected energy meters.
- A colored status dot next to each device provides immediate health visibility:
  - **Green (Normal)**: Device operating within standard parameters without active alarms.
  - **Amber (Warning)**: Advisory conditions such as unbalance or baseline deviation.
  - **Red / Grey (Incorrect connection / Disconnected / Communication failure)**: Hardware wiring fault, disconnected CT/clip, or missing telemetry.
- New devices sending telemetry are automatically registered as "New – not configured" and appear in the selector immediately.

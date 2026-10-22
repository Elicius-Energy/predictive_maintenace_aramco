# Configuration Guide & Parameter Definitions

The Configuration page (`/config`) is organized into collapsible sections with inline validation and a single sticky **Save** button.

## 1. Device Information
- **Device ID (`dID`)**: Read-only unique 24-character hexadecimal hardware serial number burned into the energy meter's microcontroller (e.g., `002D00203335471332323632`).
- **Device Alias**: Friendly, plain-English name for the machine or installation location (e.g., "Ring Frame 14 - Main Drive").
- **Firmware Version**: Read-only firmware version reported by the IoT meter (e.g., `13.4`).
- **Last Seen**: Read-only timestamp of the most recently received packet.
- **Expected Data Interval**: Sampling cadence in seconds (default: 60 s).
- **Nominal Voltage**: System nominal line-to-neutral voltage in Volts (default: 240 V, yielding ~415 V line-to-line).
- **CT Rated Current Range**: Full-scale current rating of the installed Current Transformers in Amperes (e.g., 50 A, 100 A).
- **Mark Installation OK**: Captures the current active operating state as the installation baseline signature. Stores per-phase current shares and power factors for detecting physical CT movement over time.

## 2. Customer Information
- **Customer**: Company name (e.g., "M/s. Lakshmi Electrical Drives Pvt Ltd").
- **Location**: Factory or mill site location (e.g., "Coimbatore Plant 2").
- **Department**: Mill section (e.g., "Spinning Preparatory / Ring Frame").
- **Contact Person**: Primary customer contact or plant engineer.
- **Contact Number**: Phone number.

## 3. Motor Nameplate Details
- **Make**: Motor manufacturer (e.g., "LEDL", "Siemens", "ABB").
- **Motor Rating (kW)**: Rated shaft power in kilowatts (e.g., 15.0 kW).
- **Frame Size**: Standard motor mechanical frame (e.g., "160M").
- **Rated Current (Amps)**: Nameplate full-load current (e.g., 28.5 A).
- **Rated Speed (RPM)**: Rated synchronous/rotor speed (e.g., 1460 RPM).
- **Rated Voltage (V)**: Rated operating voltage (e.g., 415 V).
- **Connection**: Winding connection (`Delta` or `Star`).
- **Duty**: Operating duty cycle (e.g., `S1 Continuous`).
- **Insulation Class**: Thermal insulation rating (`Class F`, `Class H`).
- **Motor Type**: Type designation (e.g., "IE3 Premium Efficiency Induction Motor").
- **Serial Number**: Motor manufacturer serial number.

## 4. Machine Details
- **Machine Name**: Machine designation (e.g., "Spinning Frame LR9/AXL").
- **Make & Model No.**: Machine builder details.
- **Count & TPI**: Textile yarn count (Ne) and twists per inch (if applicable).
- **Raw Material**: Processing fiber (e.g., "100% Combed Cotton").
- **Machine RPM (Max & Avg)**: Operational speed benchmarks.
- **No. of Spindles**: Total spindle count (e.g., 1200 spindles).

## 5. Inverter Details
- **Make & Model**: Variable Frequency Drive (VFD) manufacturer and model (e.g., "Danfoss VLT AutomationDrive").

## 6. LEDL Representative & Signatories
- **Representative Name, Designation, Contact Number, Email**: Auditing engineer conducting the study.
- **Customer Signatory Name & Designation**: Plant authority confirming receipt of the audit results.

## 7. Commercial Inputs (Used for ROI)
- **Electricity Tariff (Rs/kWh)**: Unit rate charged by the electrical utility (e.g., Rs. 8.50 / kWh).
- **Annual Operating Hours**: Plant working hours per annum (e.g., 8,000 hrs/year).
- **LEDL Motor Investment (Rs)**: Capital expenditure for upgrading to a high-efficiency motor.
- **Installation / Modification Cost (Rs)**: Labor and mechanical retrofit costs.

## 8. Advanced Thresholds (Collapsed)
- **Idle Power Threshold (kW)**: Power level below which the motor is classified as running in an unloaded or idle condition. Defaults to 5% of the motor kW rating (or 0.2 kW if unconfigured).
- **Active Current Threshold (A)**: Minimum current threshold (default: 1.0 A) to consider a phase actively energized.
- **Debounce Raise Count**: Consecutive faulty samples required to raise an alarm (default: 3).
- **Debounce Clear Count**: Consecutive healthy samples required to clear an alarm (default: 3).
- **Email Notifications**: Optional switch to dispatch alerts via SMTP to the designated service personnel.

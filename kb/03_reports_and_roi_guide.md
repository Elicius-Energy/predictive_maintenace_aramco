# Reports, Energy Saving & ROI Guide

The Reports & Downloads page (`/reports`) generates professional Microsoft Excel (.xlsx) workbooks adhering strictly to the official LEDL Motor Energy Reading Report standard.

## Report Structure (Sheets)

### Sheet 1: Energy Reading Report
- Formal auditing report formatted for A4 landscape print presentation.
- Contains 8 numbered sections matching the LEDL engineering template:
  1. Customer Information
  2. Motor Name Plate Details
  3. Machine Details
  4. Inverter Details
  5. Measured Energy Data (Start Time, End Time, Analysis Period, Idle Time, Total Energy Consumption, Avg/Min/Max Power, Voltage, Current, Power Factor, and Frequency)
  6. Observation / Remarks (User notes combined with automated engineering observations)
  7. Customer Confirmation (Designation and blank signature fields for physical signing)
  8. LEDL Representative (Designation and blank signature fields)

### Sheet 2: Energy Saving & ROI
- Activated when the **Include energy saving & ROI** switch is toggled.
- Built using **live native Excel formulas** so customers can interactively modify tariffs or operating hours in Microsoft Excel.
- Formulas and calculations:
  - **Before Motor Consumption ($kWh/hr$)**: Energy consumed per running hour during baseline study.
  - **After Motor Consumption ($kWh/hr$)**: Energy consumed per running hour after motor retrofit.
  - **Energy Saving ($kWh/hr$)**: $kWh/hr_{\text{Before}} - kWh/hr_{\text{After}}$.
  - **Annual Energy Saving ($kWh/year$)**: $\text{Energy Saving} \times \text{Annual Operating Hours}$.
  - **Annual Monetary Saving ($Rs/year$)**: $\text{Annual Energy Saving} \times \text{Electricity Tariff (Rs/kWh)}$.
  - **Total Investment ($Rs$)**: $\text{LEDL Motor Cost} + \text{Installation Cost}$.
  - **Payback Period / ROI (Years)**: $\text{Total Investment} / \text{Annual Monetary Saving}$.
  - **Monthly Monetary Saving ($Rs/month$)**: $\text{Annual Monetary Saving} / 12$.
  - **Monthly Energy Saving ($kWh/month$)**: $\text{Annual Energy Saving} / 12$.
- Features embedded Excel Before vs. After comparison charts and hourly energy trends.

### Sheet 3: Analysis
Detailed statistical audit breakdown:
- Energy metrics: Trapezoidally integrated total kWh vs. hardware counter import delta ($kwh\_imp$), discrepancy percentage, energy cost.
- Power metrics: Load factor ($\text{Avg kW} / \text{Max kW}$), average loading % of rated nameplate kW and rated current, maximum demand ($md\_kw, md\_kva$).
- Duty cycle: Running hours vs. idle hours and idle percentage.
- Power quality: Voltage unbalance %, current unbalance %, energy-weighted power factor ($kWh / kVAh$), percentage of time $PF < 0.85$.
- Hourly profile matrix (hours 00 to 23 with average kW and kWh).
- Daily aggregate summary table.
- Data completeness % and list of communication gaps.
- Historical alarm log active during the audit window.

### Sheet 4: Data
Complete date-wise and time-wise bucketed telemetry at the selected interval (1-min, 5-min, or 1-hour). Preserves gaps as blank rows so missing intervals are transparently identified.

### Sheet 5: Charts
Embedded native Excel charts for Power (kW), Voltage (3-phase), Current (3-phase), Power Factor, and Frequency trends.

## Raw Data Export
Supports on-demand download of raw per-phase metrics in `.xlsx` format and timestamp-formatted `.csv` in the local display timezone (`Asia/Kolkata`).

# Electrical Parameters & Energy Audit Glossary

A reference guide for engineering terminology and calculations used throughout the LEDL Motor Energy Monitoring Dashboard.

## Primary Electrical Parameters

- **Voltage ($V$, Volts)**:
  - $V_{LN}$ (Line-to-Neutral): Voltage between phase conductor (L1, L2, L3) and system neutral ($v1n, v2n, v3n$).
  - $V_{LL}$ (Line-to-Line): Voltage between two phase conductors ($v12, v23, v31$). For a balanced 3-phase system: $V_{LL} = \sqrt{3} \times V_{LN} \approx 1.732 \times V_{LN}$.
  - $vln\_avg$: Arithmetic average of the three line-to-neutral voltages.

- **Current ($I$, Amperes)**:
  - Phase currents ($i1, i2, i3$): RMS current passing through each motor stator phase.
  - $i\_avg$: Arithmetic average of the three phase currents: $(i1 + i2 + i3) / 3$.

- **Active Power ($P$, Kilowatts - kW)**:
  - The actual electrical power converted into mechanical shaft torque and losses:
    $kw_n = v_{nn} \times i_n \times \cos(\phi_n) / 1000$
  - Total Active Power: $t\_kw = kw1 + kw2 + kw3$.

- **Reactive Power ($Q$, Kilovolt-Amperes Reactive - kVAR)**:
  - Magnetizing power required to establish magnetic flux in the motor core air gap:
    $kvar_n = v_{nn} \times i_n \times \sin(\phi_n) / 1000$
  - Total Reactive Power: $t\_kvar = kvar1 + kvar2 + kvar3$.

- **Apparent Power ($S$, Kilovolt-Amperes - kVA)**:
  - Total vector power supplied by the electrical utility:
    $kva_n = \sqrt{kw_n^2 + kvar_n^2}$
  - Total Apparent Power: $t\_kva = \sqrt{t\_kw^2 + t\_kvar^2}$.

- **Power Factor ($PF$, Dimensionless, $0.00$ to $1.00$)**:
  - Ratio of active power to apparent power: $PF = kW / kVA = \cos(\phi)$.
  - **Bucket PF (Trends)**: Arithmetic mean of instantaneous $pf\_avg$.
  - **Energy-Weighted Power Factor (Audit Reports)**: Over any extended time window, the authentic thermodynamic power factor is defined as:
    $PF_{\text{weighted}} = \frac{\text{Total Energy (kWh)}}{\text{Total Apparent Energy (kVAh)}}$
  - Indian electrical utilities mandate $PF \ge 0.90$ (typically penalizing below $0.85$ and offering rebates above $0.95$).

- **Frequency ($Hz$, Hertz)**:
  - AC grid supply frequency (nominal 50.0 Hz in India).

- **Energy ($kWh$, Kilowatt-Hours)**:
  - Cumulative electrical energy consumed.
  - In this platform, high-resolution interval energy is computed by **trapezoidal integration** of active power $t\_kw$ over elapsed seconds.
  - $kwh\_imp$: The integer counter from the meter register used as an independent cross-check.

- **Maximum Demand ($MD$, $md\_kw$ & $md\_kva$)**:
  - The peak average power drawn over standard rolling integration intervals (typically 15 minutes). Peak demand drives utility capacity charges.

- **Idle Time & Running Time**:
  - **Running Time**: Time when the motor is energized and drawing active power above the idle threshold (default: 5% of motor kW rating or 0.2 kW).
  - **Idle Time**: Time when the motor is running below the threshold (unloaded, waiting for material, or bearing spinning without productive work).
  - Reducing motor idle time is one of the highest-yield low-cost energy efficiency recommendations.

- **Load Factor**:
  - Ratio of average power to peak power during the monitoring period:
    $\text{Load Factor} = \frac{\text{Average kW}}{\text{Peak kW}}$

- **Voltage Unbalance (%)**:
  - Maximum deviation from the average voltage divided by the average voltage:
    $\text{Voltage Unbalance} = \frac{\max(|V_1 - V_{\text{avg}}|, |V_2 - V_{\text{avg}}|, |V_3 - V_{\text{avg}}|)}{V_{\text{avg}}} \times 100\%$
  - Voltage unbalance exceeding 2% causes severe stator current unbalance, parasitic rotor heating, and motor derating.

- **Current Unbalance (%)**:
  - Maximum current deviation from average current divided by average current:
    $\text{Current Unbalance} = \frac{\max(|I_1 - I_{\text{avg}}|, |I_2 - I_{\text{avg}}|, |I_3 - I_{\text{avg}}|)}{I_{\text{avg}}} \times 100\%$

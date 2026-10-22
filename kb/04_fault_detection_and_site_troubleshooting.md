# Fault Detection & Site Troubleshooting Manual

The LEDL Energy Monitoring System runs an intelligent fault detection engine that checks incoming telemetry against electrical engineering principles. Alarms are debounced over 3 consecutive bad packets before triggering, and clear after 3 consecutive good packets.

## Overall Status Hierarchy (Precedence Order)
1. **Communication failure** (Highest priority)
2. **Disconnected**
3. **Incorrect connection**
4. **Warning**
5. **Normal** (All checks clear)

---

## Alarm Catalog & On-Site Correction Procedures

### 1. CT Polarity / Direction Incorrect
- **Trigger Rule**: Active power on phase $n$ is negative ($kw_n < -0.02\text{ kW}$) while current is active ($i_n > 1.0\text{ A}$).
- **Phase Indication**: Specifically identifies the phase (e.g., `CT L2: Incorrect connection - wrong direction`). If all 3 phases are negative, alerts that all CTs are reversed or reverse power flow is occurring.
- **Cause**: The Current Transformer is clamped backwards onto the cable (arrow pointing towards grid source instead of towards load).
- **Site Fix**: Open the CT clip on Phase $n$ and turn it around 180° so the directional arrow points in the direction of power flow (towards the motor terminal box). Alternatively, reverse the S1 and S2 secondary wire connections at the meter terminal block.

### 2. CT Disconnected
- **Trigger Rule**: Phase voltage is present ($v_{nn} > 50\text{ V}$), but phase current is near zero ($i_n < 0.05\text{ A}$) while at least one other phase has active current ($i > 1.0\text{ A}$).
- **Note**: If all three phase currents are ~0 A and voltages are present, the motor is stopped/idle; this is NOT flagged as a fault.
- **Cause**: CT secondary wire unplugged, terminal screw loose, or CT not clamped onto any conductor.
- **Site Fix**: Check the secondary signal plug on the meter. Verify that the CT clamp has closed tightly around the phase conductor and latched.

### 3. CT Connection Incorrect (Phase Swap)
- **Trigger Rule**: Phase $n$ has active current ($i_n > 1.0\text{ A}$), but its power factor differs from the median of the other two phases by more than $0.25$, or $|pf_n| < 0.3$ while others $> 0.6$ (and $kw_n \ge -0.02\text{ kW}$).
- **Cause**: CT installed on the wrong phase conductor relative to the voltage clip (e.g., CT for L1 is clamped onto Phase L2 cable).
- **Site Fix**: Trace the wire harness from the meter voltage clips and CT inputs. Ensure CT 1 is on Phase R/L1, CT 2 is on Phase Y/L2, and CT 3 is on Phase B/L3.

### 4. CT Position Changed
- **Trigger Rule**: Compared against the installation baseline (captured via "Mark installation OK"), current share ($i_n / i_{\text{total}}$) or per-phase PF deviates by $> 30\%$ for 15 minutes.
- **Cause**: Physical displacement of the CT, loose CT clamp vibrating open, or uneven core air gap.
- **Site Fix**: Inspect CT seating on the conductor. Fasten with a cable tie to prevent vibration displacement.

### 5. Voltage Clip Disconnected
- **Trigger Rule**: Phase-to-neutral voltage drops below $50\text{ V}$ ($v_{nn} < 50\text{ V}$) while the device remains online.
- **Cause**: Crocodile/alligator voltage clip slipped off the busbar or terminal stud.
- **Site Fix**: Re-attach the voltage probe clip firmly to the corresponding phase terminal. Clean off grease or oxidation from the copper terminal.

### 6. Voltage Connection Incorrect
- **Trigger Rule**: Line-to-line voltage differs from $\sqrt{3} \times V_{LN}$ by $> \pm 6\%$, or average voltage is outside 80% to 120% of nominal voltage (e.g., outside 192 V – 288 V for 240 V nominal).
- **Cause**: Neutral reference disconnected, crossed voltage leads, or severe grid undervoltage/overvoltage.
- **Site Fix**: Verify the neutral (black) wire connection. Confirm line-to-line phase sequence (L1 -> L2 -> L3) with a digital multimeter.

### 7. Current / Voltage Signal Not Received
- **Trigger Rule**: Payload is missing expected electrical fields or values are `null`.
- **Cause**: Internal ADC read error in meter firmware or corrupted serial packet.
- **Site Fix**: Power cycle the energy meter. Inspect internal ribbon cables.

### 8. Sensor Communication Failure
- **Trigger Rule**: Meter telemetry contains non-numeric data, values out of physical boundaries ($V > 600\text{ V}$, $Freq \notin [40, 60]\text{ Hz}$), total active power $t\_kw$ deviates from $\sum kw_n$ by $> 5\% + 0.05\text{ kW}$, or all readings remain byte-identical (frozen) for 10 consecutive cycles.
- **Cause**: Microcontroller memory corruption or locked I2C/SPI bus to energy metering chip.
- **Site Fix**: Perform hardware reboot of the IoT energy meter.

### 9. IoT Device Communication / Network Failure
- **Trigger Rule**: Server has not received a packet from the device for $\max(3 \times \text{interval}, 180\text{ s})$.
- **Cause**: Cellular/Wi-Fi signal drop, network router outage, or device power lost.
- **Auto-Recovery**: Clears automatically as soon as the next telemetry packet arrives. If the device was buffering data offline, it will back-fill store-and-forward packets with their original timestamps without data loss.

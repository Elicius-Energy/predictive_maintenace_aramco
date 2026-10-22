# LEDL Motor Energy Monitoring Dashboard

**M/s. Lakshmi Electrical Drives Pvt Ltd (LEDL) — Energy Audit Department**  
Production-Ready, Containerised IoT Energy Monitoring, Wiring Diagnostics & ROI Reporting Platform.

---

## 📋 Table of Contents
1. [Overview & Design Philosophy](#overview--design-philosophy)
2. [Key Capabilities & Hard Constraints](#key-capabilities--hard-constraints)
3. [Architecture & Technology Stack](#architecture--technology-stack)
4. [Quick Start (Single-Command Run)](#quick-start-single-command-run)
5. [Local Development (Without Docker)](#local-development-without-docker)
6. [Credentials & Seeded Devices](#credentials--seeded-devices)
7. [Adding New Users](#adding-new-users)
8. [Pointing IoT Devices to the Ingestion API](#pointing-iot-devices-to-the-ingestion-api)
9. [Electrical Wiring Fault Engine (10 Rules)](#electrical-wiring-fault-engine-10-rules)
10. [Client Excel Report & ROI Engine](#client-excel-report--roi-engine)
11. [Floating AI (RAG) Diagnostics Assistant](#floating-ai-rag-diagnostics-assistant)
12. [Backup & Disaster Recovery](#backup--disaster-recovery)
13. [Test Suite & Verification](#test-suite--verification)

---

## 1. Overview & Design Philosophy

This platform is engineered specifically for the **Energy Audit Department of M/s. Lakshmi Electrical Drives Pvt Ltd (LEDL)**. Energy auditors install 3-phase clamp meters on customer motors (textile ring frames, compressors, pumps, etc.) to capture real electrical data, identify site wiring issues, compute true energy consumption, and prove monetary savings achieved by upgrading to LEDL energy-efficient motors.

### The Core Constraint: Simplicity
The UI is strictly streamlined so field audit engineers and non-technical clients can operate it without training:
- **No unnecessary sub-menus, nested sidebars, or complex charting widgets.**
- **White background (`#FFFFFF`) with LEDL Navy (`#1F3A8A`) accents.**
- **Large readable numbers with explicit units.**
- **Standardized status colors only**: Normal (Green), Warning (Amber), Fault/Failure (Red), Disconnected/Offline (Grey).

---

## 2. Key Capabilities & Hard Constraints

1. **Strict 3-Tab Architecture**: Exactly **one Login page** + **three top-level pages**:
   - **Configuration** (`/config`): 9 collapsible plant/motor/meter sections + sticky Save button & baseline capture.
   - **Dashboard** (`/dashboard`): Status banner with per-phase CT/Clip chips, 6 live telemetry cards, period summary strip, and 6 clean trend charts.
   - **Reports & Downloads** (`/reports`): Live period preview, study parameters, live ROI toggle, 1-click Excel generation, and report history.
2. **Floating AI Assistant**: Available at the bottom-right across all 3 pages with slide-out drawer, parameterized database tools, and LEDL audit knowledge base grounding.
3. **Multi-Device Support**: Top navigation device selector switches the active context for Configuration, Dashboard, and Reports simultaneously. Unknown device IDs (`dID`) arriving via HTTP are auto-registered as `"New – not configured"`.
4. **Idempotent Ingestion**: Real Unix epoch seconds `dTS` in UTC. Database enforces `PRIMARY KEY (device_id, ts)` with `ON CONFLICT DO NOTHING`.
5. **Accurate Energy Integration**: Trapezoidal integration with interval gap preservation (>3× expected interval) and energy-weighted Power Factor ($kWh / kVAh$).

---

## 3. Architecture & Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS, Lucide | Responsive SPA, clean white theme, Recharts |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2 | Async REST API, Argon2 security, APScheduler watchdog |
| **Database** | PostgreSQL 16 + TimescaleDB + pgvector | Hypertables, continuous aggregates (`1m`, `5m`, `1h`), SQLite fallback |
| **Excel Engine** | XlsxWriter | 5-sheet native Excel reports with live calculation formulas |
| **AI / RAG** | OpenAI GPT-4o-mini + FAISS / pgvector | Streaming SSE chat with safe read-only database query tools |
| **Proxy / Web** | Nginx | Reverse proxy for API routing and static caching |

---

## 4. Quick Start (Single-Command Run)

### Prerequisites
- Docker Engine 24+ and Docker Compose v2+

### Running the Complete Stack
1. Clone the repository and navigate to the project directory:
   ```bash
   cd predictive_maintenace_aramco
   ```
2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
   *(Optional: Add your `OPENAI_API_KEY` in `.env` if you wish to enable OpenAI responses for the chatbot).*

3. Start all services:
   ```bash
   docker compose up -d --build
   ```

4. *(Optional)* Start the realistic IoT multi-device simulator:
   ```bash
   docker compose --profile simulator up -d
   ```

5. Open your web browser and navigate to:
   - **Web Application**: `http://localhost` (or `http://localhost:8080`)
   - **Backend API Docs**: `http://localhost:8000/docs`
   - **Backend Health Check**: `http://localhost:8000/healthz`

---

## 5. Local Development (Without Docker)

The platform includes an automatic SQLite fallback (`data/ledl_energy.db`) so developers can run the entire platform locally without running PostgreSQL:

### 1. Backend Setup
```bash
# Set up Python virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Start backend server
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. Vite automatically proxies `/api` requests to `http://localhost:8000`.

### 3. Run Simulated IoT Devices
In a separate terminal:
```bash
./backend/venv/bin/python simulator/publish_readings.py --interval 5
```

---

## 6. Credentials & Seeded Devices

### Default Administrator Login
- **Username**: `admin`
- **Password**: `admin123`
*(Authenticated via Argon2 with secure httpOnly cookie session `ledl_access_token`)*

### Pre-Configured Audit Devices
1. **Device A**: `002D00203335471332323632`
   - **Alias**: Ring Frame 14 - Main Motor
   - **Motor Rating**: 22.0 kW (415 V, 50 Hz, 1475 RPM)
   - **Site**: Lakshmi Mills, Unit 1, Coimbatore
2. **Device B**: `002D00203335471332323633`
   - **Alias**: Compressor House - Motor 2
   - **Motor Rating**: 37.0 kW (415 V, 50 Hz, 2950 RPM)
   - **Site**: Lakshmi Electrical Drives Plant 2

---

## 7. Adding New Users

To create additional audit engineers or operators, use the built-in CLI utility:

```bash
# Add operator
python scripts/add_user.py <username> <password> --role operator

# Add administrator
python scripts/add_user.py <username> <password> --role admin
```

Example:
```bash
python scripts/add_user.py engineer1 ledl2026 --role operator
```

---

## 8. Pointing IoT Devices to the Ingestion API

Any IoT energy meter or gateway can transmit data directly over HTTP POST.

### Ingestion Details
- **URL**: `http://<SERVER_IP>:8000/api/ingest`
- **Method**: `POST`
- **Header**: `X-Device-Key: ledl_secret_device_key_2026`
- **Content-Type**: `application/json`

### JSON Telemetry Payload Format
```json
{
  "dID": "002D00203335471332323632",
  "dTS": 1704067200,
  "fw_ver": "13.4",
  "v_l1_n": 232.4,
  "v_l2_n": 231.8,
  "v_l3_n": 233.1,
  "v_l1_l2": 402.1,
  "v_l2_l3": 401.9,
  "v_l3_l1": 402.8,
  "i_l1": 24.8,
  "i_l2": 25.1,
  "i_l3": 24.6,
  "kw_l1": 4.92,
  "kw_l2": 4.98,
  "kw_l3": 4.88,
  "t_kw": 14.78,
  "kwh_imp": 10425.6,
  "kwh_exp": 0.0,
  "kwh_tot": 10425.6,
  "t_kvar": 6.82,
  "t_kvarh": 4120.1,
  "t_kva": 16.28,
  "t_kvah": 11210.0,
  "pf_l1": 0.86,
  "pf_l2": 0.86,
  "pf_l3": 0.85,
  "t_pf": 0.86,
  "hz": 50.02,
  "md_kw": 18.2
}
```

*Note: Telemetry payloads can also be transmitted as a JSON array `[...]` for batch uploads after network outages.*

---

## 9. Electrical Wiring Fault Engine (10 Rules)

The engine monitors live electrical signals and detects site installation errors before they corrupt audit calculations. Every rule includes debouncing ($N=3$ bad packets to raise, $M=3$ good packets to clear):

| # | Fault Condition | Detection Logic | Severity |
|---|---|---|---|
| **1** | **CT polarity/direction incorrect** | Active current $i_n > 1.0\text{ A}$ but phase power $kw_n < -0.02\text{ kW}$ | Red (`Fault`) |
| **2** | **CT disconnected** | Voltage present ($v_n > 50\text{ V}$), current $i_n < 0.05\text{ A}$ while other phases carry active load | Red (`Disconnected`) |
| **3** | **CT connection incorrect / phase swap** | Phase PF deviates $>0.25$ from median of other phases | Red (`Incorrect connection`) |
| **4** | **CT position changed** | Phase current share deviates $>30\%$ from saved baseline | Amber (`Warning`) |
| **5** | **Voltage clip disconnected** | Phase voltage $v_n < 50\text{ V}$ | Red (`Disconnected`) |
| **6** | **Voltage connection incorrect** | Line-to-line vs line-to-neutral $\ne \sqrt{3} \pm 6\%$ or $V_{nom} \notin 80-120\%$ | Red (`Incorrect connection`) |
| **7** | **Current signal missing** | Required current fields null or unparseable | Red (`Fault`) |
| **8** | **Voltage signal missing** | Required voltage fields null or unparseable | Red (`Fault`) |
| **9** | **Sensor comm failure** | Out-of-bounds readings, $t\_kw \ne \sum kw_n$, or frozen telemetry | Red (`Communication failure`) |
| **10** | **IoT device comm watchdog** | $now - last\_seen > \max(3 \times interval, 180s)$ | Red (`Communication failure`) |

**Status Precedence:** `Communication failure` > `Disconnected` > `Incorrect connection` > `Warning` > `Normal`.

---

## 10. Client Excel Report & ROI Engine

The platform generates official, professional Excel workbooks matching LEDL's 8-section audit template with **five native sheets**:

1. **Sheet 1 — Energy Reading Report**:
   - Company branding & Report reference `LEDL/ER/YYYY/XXXX`
   - Customer & Site details
   - Motor Nameplate & Machine operating specifications
   - Operating condition metrics (Avg Voltage, Current, Power, PF, Frequency)
   - Energy Consumption (Total kWh, Total kVAh, Idle vs Running hours)
   - Signature blocks (Energy Audit Engineer & Customer Representative)
2. **Sheet 2 — Energy Saving & ROI**:
   - Existing vs Proposed LEDL Motor specifications
   - **Live Native Excel Formulas** (recalculating automatically upon edits):
     - Power Saved (kW): `=C4-C5`
     - Annual Energy Saved (kWh): `=C6*C7`
     - Annual Cost Saved (INR): `=C8*C9`
     - Total Investment (INR): `=C13+C14`
     - Simple Payback Period (Months): `=(C15/C10)*12`
     - Simple Payback Period (Years): `=C15/C10`
     - 5-Year Net ROI (%): `=((C10*5-C15)/C15)*100`
   - Native Excel ROI Comparison Column Chart embedded beside the calculations.
3. **Sheet 3 — Analysis**:
   - Motor Load Factor (%), Voltage Unbalance (%), Current Unbalance (%)
   - 24-Hour hourly average profile table
   - Data completeness (%) and missing timestamp record log.
4. **Sheet 4 — Data**:
   - Interval-bucketed raw electrical readings with outage gap preservation.
5. **Sheet 5 — Charts**:
   - Native Excel Line Charts for Active Power (kW), 3-Phase Voltages (V), 3-Phase Currents (A), Power Factor, and Frequency (Hz).

---

## 11. Floating AI (RAG) Diagnostics Assistant

The floating assistant is accessible via the button at the bottom-right on all pages.

### Capabilities:
- **Direct Database Query Tools**: Live power cards, device status, active alerts, period summaries, and report history.
- **RAG Knowledge Retrieval**: Grounded in 5 markdown documents (`kb/` directory) covering audit procedures, motor formulas, wiring fault troubleshooting, and ROI calculations.
- **Streaming SSE Output**: Real-time markdown rendering with code blocks, tables, and clickable references.
- **Graceful Fallback**: If `OPENAI_API_KEY` is not configured, the assistant provides a helpful explanation rather than crashing.

---

## 12. Backup & Disaster Recovery

### Automated Nightly Backup
The script handles both PostgreSQL/TimescaleDB and SQLite fallback databases, rotating archives after 14 days:

```bash
# Run backup manually
./deploy/backup.sh

# Recommended crontab entry (daily at 2:00 AM)
0 2 * * * /path/to/predictive_maintenace_aramco/deploy/backup.sh >> /var/log/ledl_backup.log 2>&1
```

### Turnkey Database Restore
To restore any previous backup archive:
```bash
./deploy/restore.sh backups/ledl_energy_pg_20261015_120000.sql.gz
```

---

## 13. Test Suite & Verification

The codebase includes automated unit and integration tests across backend and frontend:

### 1. Backend Pytest Suite (26 Tests — 100% Passing)
```bash
PYTHONPATH=backend ./backend/venv/bin/pytest backend/tests/ -v
```
- `test_fault_engine.py`: Tests all 10 fault rules, debouncing, per-phase chips, and recovery.
- `test_ingest_idempotency.py`: Tests duplicate packet rejection, device auto-registration, and future timestamp rejection.
- `test_energy_integration.py`: Tests trapezoidal integration with outage gaps and energy-weighted PF.
- `test_excel_report.py`: Tests workbook generation, sheet validation, and live ROI formulas.
- `test_chat_tools.py`: Tests safe read-only database query tools.
- `test_api.py`: Tests FastAPI authentication, device configuration, live cards, trends, and reports download.

### 2. Frontend Vitest Suite (100% Passing)
```bash
cd frontend && npx vitest run
```
- Validates Navbar rendering (exactly 3 tabs + device selector).
- Validates Login page presentation and credential entry.
- Validates Floating AI Assistant drawer toggle and query input.

### 3. Production Build Validation
```bash
cd frontend && npm run build
```
Builds production-optimized static bundle into `frontend/dist` with 0 TypeScript/lint errors.

---

## 📞 Support & Maintenance
For questions or configuration assistance, contact **M/s. Lakshmi Electrical Drives Pvt Ltd, Energy Audit Department**.


The credentials are still using the development defaults. I checked the active configuration: it’s in development, the admin password falls back to admin123, and the JWT secret is a placeholder. The local database contains one admin account. The app hashes the seeded password with Argon2, but that doesn’t make a default password safe. Don’t expose this setup to the internet.
The current app already has a users table with a role field, Argon2 password hashing, and cookie-based sessions. It doesn’t yet have user management or device-level access control: device access isn’t consistently enforced by the API, so hiding devices in the UI alone wouldn’t protect them.
Suggested framework
- Give admins a user-management page to create, disable, and reset accounts, assign roles, and select allowed device IDs.
- Store device grants in a many-to-many user_device_access table. Check those grants on the server for every device list, reading, chart, report, and AI request.
- Use roles such as Admin, Analyst, and Viewer to control actions; device assignments separately control which assets each user can see.
- Issue one-time invitations or temporary passwords that must be changed at first login. Add admin MFA, login throttling, session revocation, and an audit log.
- Keep Argon2id password hashing and secure, HttpOnly, SameSite cookies. Enable Secure cookies behind HTTPS and use CSRF protection for cookie-authenticated requests.
- For a larger organization, consider OIDC single sign-on through its identity provider; otherwise, the existing database-backed user model can support this cleanly.
Before deployment, replace the default admin password and placeholder JWT secret, and disable development-mode behavior.


11:45 PM
# User access and deployment setup

The application supports Admin, Analyst, and Viewer roles. Administrators manage users at `/users`, assign device grants, reset passwords, disable accounts, and enroll TOTP MFA. New and reset accounts receive a temporary password that must be changed before any other API use. Device access is checked server-side for telemetry, reports, exports, and AI requests; grants are stored in `user_device_access`.

Before starting a deployment, configure a unique `JWT_SECRET_KEY` of at least 32 characters and an `ADMIN_PASSWORD` of at least 12 characters (or an `ADMIN_PASSWORD_HASH`). Do not publish or deploy with the example file's blank values. Set `ENVIRONMENT=production` and `COOKIE_SECURE=true` when served over HTTPS. Existing accounts using `admin123` are forced through password change on their next sign in. Database initialization adds the user lifecycle columns and access/audit tables to existing installations.

CSRF protection uses a SameSite cookie plus the `X-CSRF-Token` header on cookie-authenticated state-changing requests. Login throttling is process-local; multi-worker or multi-instance deployments should put a shared rate limiter at the proxy or use a shared store. TOTP MFA is available for admins. Audit events are retained in `audit_logs` and the latest 200 are available to admins through `/api/users/audit`.

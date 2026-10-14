# Plate Scan & Case Matching Service

A production-grade, multi-tenant full-stack service that ingests real-time vehicle plate scans from cameras, associates sightings with active recovery cases, queries partner network eligibility for unmatched vehicles, facilitates atomic cross-tenant case claiming, and renders a tenant-scoped React dashboard.

---

## 1. Project Overview & Architecture

### Core Responsibilities
- **High-Throughput Scan Ingestion (`POST /api/v1/scans`)**: Ingests vehicle license plate and VIN scans from automated cameras, validates camera state, and stores raw sightings immutably.
- **Intelligent Case Matching**: Automatically associates sightings with existing active cases for that VIN, maintaining an end-to-end location trail across multiple cameras and tenants.
- **Partner Network Eligibility**: Calls a mock third-party eligibility service for unmatched vehicles with timeout protection and transactional isolation.
- **Atomic Cross-Tenant Case Claiming (`POST /api/v1/cases/{case_id}/claim`)**: Allows authorized staff from any tenant to claim open `pending_claim` cases with concurrency safety (compare-and-swap update).
- **Tenant-Scoped Dashboard**: React SPA displaying tenant-isolated active cases alongside globally claimable pending cases, complete with chronological sighting trail modals.
- **Interactive UI Testing Tools**: Includes a **"Simulate Scan"** modal directly in the dashboard to test incoming camera webhooks without external CLI tools, and a **"Close Case"** action for managing active lifecycles.

---

## 2. Technology Stack

- **Backend**: Python 3.12+ / 3.13, FastAPI, Pydantic v2, SQLAlchemy 2.0 (synchronous sessions), Alembic, PyJWT, Passlib (Argon2), HTTPX, Pytest.
- **Frontend**: React 18, TypeScript, Vite, React Router 7, Axios, Lucide Icons, Pure CSS (Dark Mode Design System).
- **Database**: PostgreSQL 16+ (Docker / Production) with automatic SQLite zero-config fallback for seamless local bare-metal running.
- **Containerization**: Docker, Docker Compose.

---

## 3. Repository Structure

```
CaseStudyArchetype/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py                  # POST /api/v1/auth/login
│   │   │   ├── cases.py                 # GET /cases, POST /claim, POST /close, GET /scans
│   │   │   └── scans.py                 # POST /api/v1/scans (camera webhook)
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic BaseSettings
│   │   │   ├── dependencies.py          # get_db, get_current_user
│   │   │   └── security.py              # Argon2 hashing & PyJWT encode/decode
│   │   ├── db/
│   │   │   ├── base.py                  # DeclarativeBase
│   │   │   └── session.py               # SQLAlchemy 2.0 Engine (with auto-fallback)
│   │   ├── models/
│   │   │   ├── camera.py, case.py, scan.py, tenant.py, user.py
│   │   ├── schemas/
│   │   │   ├── auth.py, case.py, scan.py
│   │   ├── services/
│   │   │   ├── case_service.py          # Atomic claiming & tenant-scoped access
│   │   │   ├── eligibility_service.py   # External partner client with timeouts
│   │   │   └── scan_service.py          # Ingestion pipeline & transaction boundaries
│   │   └── main.py                      # FastAPI app & mock partner route
│   ├── migrations/                      # Alembic migrations & initial schema
│   ├── scripts/seed.py                  # Idempotent development seed data
│   ├── tests/
│   │   ├── conftest.py                  # Fixtures, test client & DB reset
│   │   ├── test_cases.py                # Claiming, listing, isolation & auth tests
│   │   └── test_scans.py                # Ingestion, duplicates, timeouts tests
│   ├── Dockerfile, requirements.txt, pytest.ini
├── frontend/
│   ├── src/
│   │   ├── api/client.ts                # Axios instance with JWT interceptor
│   │   ├── components/
│   │   │   ├── Navbar.tsx               # Tenant pill, user profile, logout
│   │   │   ├── NewScanModal.tsx         # In-browser camera webhook simulator
│   │   │   ├── ScanModal.tsx            # Chronological vehicle sighting trail modal
│   │   │   └── StatusBadge.tsx          # Status indicators
│   │   ├── context/AuthContext.tsx      # Auth session provider
│   │   ├── pages/
│   │   │   ├── DashboardPage.tsx        # Cases table, filter, claim/close actions, trail
│   │   │   └── LoginPage.tsx            # Form with quick seed demo switches
│   │   ├── types/index.ts               # TypeScript schemas
│   │   ├── App.tsx, main.tsx, index.css # Pure CSS dark theme
│   ├── Dockerfile, package.json, vite.config.ts, tsconfig.json
├── docker-compose.yml
├── .env.example
├── .gitignore
├── DESIGN.md                # System architecture, ER diagram, AWS deployment design
└── README.md                # This manual
```

---

## 4. Local Startup Instructions

### Option A: Running Bare Metal (Zero-Config, Instant Startup)

The project includes pre-configured virtual environments and an automatic local SQLite database (`platescan.db`) so you can run it right away without configuring PostgreSQL credentials.

#### 1. Start the Backend
Open a terminal in `backend/`:
```powershell
cd d:\Asccesment\CaseStudyArchetype\backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Start the server (tables and seed data auto-initialize on startup!)
uvicorn app.main:app --reload --port 8000
```
- API Root: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

#### 2. Start the Frontend
Open a second terminal in `frontend/`:
```powershell
cd d:\Asccesment\CaseStudyArchetype\frontend

npm run dev
```
- Web Application: `http://localhost:5173`

---

### Option B: Running with Docker Compose (PostgreSQL 16)

1. Ensure Docker Desktop is running.
2. From the repository root:
   ```bash
   cp .env.example .env
   docker compose up --build
   ```
3. In a separate terminal, seed the PostgreSQL container:
   ```bash
   docker compose exec backend python scripts/seed.py
   ```
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

---

## 5. Demo Credentials (Local Development Only)

You can click the quick demo buttons on the login screen or enter these credentials:

| Tenant | Name | Username | Password | Role |
| :--- | :--- | :--- | :--- | :--- |
| **Tenant 1** | Acme Recovery | `alice` | `alice123` | `admin` |
| **Tenant 2** | Beta Investigations | `bob` | `bob123` | `staff` |

---

## 6. How to Add and Edit Data

### From the Web Frontend
1. **Simulate an Incoming Camera Scan**:
   - In the dashboard, click **"Simulate Scan"** (top right of the table).
   - Click a quick preset (e.g. *Create Claimable Case* or *Match Active Case*) or type custom values.
   - Click **Send Camera Webhook** — the table refreshes immediately!
2. **Claim a Case**:
   - For cases with status `Pending Claim`, click **"Claim Case"**. The case atomically transitions to `Active`, assigned to your user and tenant.
3. **Close an Active Case**:
   - For active cases owned by your tenant, click **"Close"** to mark the case as resolved.
4. **View Sighting History**:
   - Click **"Scan Trail"** to view all camera sightings across all tenants in chronological order.

### From CLI / cURL
```powershell
# Simulate camera scan creating a new pending case:
curl -X POST http://localhost:8000/api/v1/scans `
  -H "Content-Type: application/json" `
  -d '{
    "camera_id": "cam_2050",
    "plate": "DEMO99",
    "vin": "VIN_DEMO_9999",
    "latitude": 34.052,
    "longitude": -118.243,
    "scanned_at": "2026-10-14T12:00:00Z"
  }'
```

---

## 7. API Endpoint Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/login` | No | Authenticate user & return JWT token with tenant attribution |
| `POST` | `/api/v1/scans` | No | Camera webhook scan ingestion & automatic case matching |
| `GET` | `/api/v1/cases` | Yes | List tenant's cases + globally claimable pending cases |
| `POST` | `/api/v1/cases/{id}/claim` | Yes | Atomic compare-and-swap claiming of a pending case |
| `POST` | `/api/v1/cases/{id}/close` | Yes | Close an active case owned by the user's tenant |
| `GET` | `/api/v1/cases/{id}/scans` | Yes | Multi-camera chronological sighting history for a VIN |
| `POST` | `/mock/partner-network/eligibility` | No | Mock partner eligibility verification endpoint |
| `GET` | `/health` | No | Health check endpoint |

---

## 8. Automated Test Suite & Actual Verification Results

Testing was executed using `pytest` covering all edge cases, access control boundaries, race conditions, and error recovery:

```powershell
cd backend
.venv\Scripts\pytest -v
```

### Actual Test Results (Verified)
```
tests/test_cases.py::TestCaseClaiming::test_successful_claim_by_originating_tenant PASSED [  4%]
tests/test_cases.py::TestCaseClaiming::test_successful_cross_tenant_claim PASSED [  8%]
tests/test_cases.py::TestCaseClaiming::test_claim_already_claimed_returns_409 PASSED [ 12%]
tests/test_cases.py::TestCaseClaiming::test_claim_closed_case_returns_409 PASSED [ 16%]
tests/test_cases.py::TestCaseClaiming::test_claim_nonexistent_case_returns_404 PASSED [ 20%]
tests/test_cases.py::TestCaseListing::test_list_cases_shows_own_and_pending_only PASSED [ 24%]
tests/test_cases.py::TestCaseListing::test_status_filter_preserves_tenant_isolation PASSED [ 28%]
tests/test_cases.py::TestCaseListing::test_status_filter_pending_claim PASSED [ 32%]
tests/test_cases.py::TestCaseListing::test_pagination PASSED             [ 36%]
tests/test_cases.py::TestScanHistoryAndAccessControl::test_scan_history_chronological_with_multiple_cameras PASSED [ 40%]
tests/test_cases.py::TestScanHistoryAndAccessControl::test_pending_case_scan_history_accessible PASSED [ 44%]
tests/test_cases.py::TestScanHistoryAndAccessControl::test_cross_tenant_active_case_access_denied PASSED [ 48%]
tests/test_cases.py::TestScanHistoryAndAccessControl::test_cross_tenant_closed_case_access_denied PASSED [ 52%]
tests/test_cases.py::TestScanHistoryAndAccessControl::test_unauthenticated_requests_rejected PASSED [ 56%]
tests/test_cases.py::TestAuthLogin::test_login_success PASSED            [ 60%]
tests/test_cases.py::TestAuthLogin::test_login_invalid_password PASSED   [ 64%]
tests/test_cases.py::TestAuthLogin::test_login_unknown_user PASSED       [ 68%]
tests/test_scans.py::TestScanIngestion::test_valid_scan_existing_case PASSED [ 72%]
tests/test_scans.py::TestScanIngestion::test_valid_scan_eligible_vin_creates_pending_case PASSED [ 76%]
tests/test_scans.py::TestScanIngestion::test_valid_scan_ineligible_vin_no_case PASSED [ 80%]
tests/test_scans.py::TestScanIngestion::test_unknown_camera_rejected PASSED [ 84%]
tests/test_scans.py::TestScanIngestion::test_inactive_camera_rejected PASSED [ 88%]
tests/test_scans.py::TestScanIngestion::test_duplicate_scan_no_duplicate_case PASSED [ 92%]
tests/test_scans.py::TestScanIngestion::test_scan_persisted_on_eligibility_timeout PASSED [ 96%]
tests/test_scans.py::TestScanIngestion::test_invalid_payload_rejected PASSED [100%]

======================= 25 passed in 18.35s =======================
```

### Frontend Production Build Verification
```powershell
cd frontend
npm run build
```
- **TypeScript Typecheck**: Passed with 0 errors.
- **Production Asset Bundling**: Built `dist/assets/index-*.js` and `dist/assets/index-*.css`.

---

## 9. Important Business Rules & Edge Cases

1. **Originating Tenant Attribution**:
   - Webhooks send `camera_id` only. The backend resolves the camera record to determine originating tenant attribution. Frontends or camera payloads can never submit an authoritative `tenant_id`.
2. **VIN Lifecycle & Partial Uniqueness**:
   - A vehicle may have multiple closed cases over its lifetime. To prevent invalid constraints while protecting against duplicate open cases, a PostgreSQL partial unique index is enforced on `(vin) WHERE status IN ('pending_claim', 'active')`.
3. **Transaction Safety Around External Calls**:
   - In `ingest_scan`, the raw scan is committed to the database **before** calling the external partner eligibility endpoint. The network call is executed outside open database transactions, preventing database locks during partner network latency.
   - If the partner service fails, the stored scan is retained and a recoverable `502 Bad Gateway` error is returned.
4. **Compare-and-Swap Claiming**:
   - Cases are claimed using an atomic SQL conditional update: `UPDATE cases SET status = 'active' ... WHERE id = :id AND status = 'pending_claim'`. A failed claim returns `409 Conflict` and never leaves a case partially assigned.
5. **Cross-Tenant Sighting Trails**:
   - Vehicle location trails belong to the VIN, querying sightings captured by any camera across all tenants.

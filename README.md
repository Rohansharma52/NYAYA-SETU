# NYAYA SETU · न्याय सेतु

### Integrated Institution Complaint Monitoring & Coordination Platform for AICTE
**Smart India Hackathon · PS 26264 · AICTE — Regulation Bureau · Theme: Smart Automation**

> One institution · One record · One voice.

> ⚠️ **DEMO DATA ONLY.** Every institution, complaint and identifier in this prototype is fictional and synthetic. None of it is official AICTE data.

---

## The problem (PS 26264)

AICTE complaints about the same institution reach different Bureaus/Cells, such as the Regulation Bureau (RB) and the Public Grievance Redressal Cell (PGRC). Nobody has a single, real-time view of them. The result is overlapping actions, duplicated effort, delays, and confusion about who is handling which institution.

## What NYAYA SETU does

| PS requirement | Where in the app |
|---|---|
| Centralized institution profile (AICTE ID, region, consolidated history) | **Institutions → Institution 360°** |
| Complaint/case tracking: ID, receipt date, category, status, bureau, officer, last & next action, expected disposal | **All Cases → Case detail** |
| Cross-bureau overlap detection, alert, linking | **Overlap Radar**, Review Inbox, overlap banner on every case |
| Real-time dashboard: received / pending / under process / disposed / transferred / beyond timeline / institution-wise / bureau workload | **Command Centre** (auto-refresh, live activity feed) |
| Workflow & action history, remarks, **supporting documents**, transfer/escalation history | **Case detail** (timeline, SHA-256-fingerprinted attachments, transfer history) |
| Search & filters: name, AICTE ID, case ID, bureau, region, category, status, date range | **All Cases** filters + **Ctrl K** global search |
| Alerts: overlap, pending reminders, escalation, timeline/SLA | **Alerts**; a background scanner runs every 15 minutes |
| Reports: bureau, region, institution, ageing, disposal rate, overlaps, **monthly & quarterly** | **Reports** (CSV/PDF export) |
| Innovation: identify the same institution even when descriptions or references differ | **Identity Lab** and **Register Complaint** |

## What makes it different

1. **Institution Identity Resolution Engine (IRE 2.0).** It finds the institution from acronyms ("A.I.E.T. Faridabad"), abbreviations, typos, **Hindi text**, an AICTE ID, an e-mail domain or an address. It runs fully offline, and every match lists its evidence. When two institutions look equally likely, it abstains instead of guessing.
   *Reproducible benchmark (174 labelled snippets): F1 **0.99**, versus 0.37 for exact lookup and 0.28 for plain fuzzy matching.* The labelled set is synthetic; real-world accuracy has to be re-measured on AICTE data.
2. **Overlap & Conflict Intelligence (OCI-1.0).** It goes beyond "same institution". Each cross-bureau pair is classified as **duplicate / action conflict / related issue / independent**, using auditable rules:
   - **C1** Closure vs enforcement: PGRC closes a file as resolved while RB is pursuing penal action.
   - **C2** Parallel directions: two bureaus write to the institution on the same issue.
   - **C3** Transfer into an existing file.
   - **C4** Divergent outcomes.
3. **"One Institution, One Voice" coordination.** The system proposes a **Lead Bureau** with reasons. One click opens a coordination item with the lead and supporting bureaus, acknowledgements and tasks, and alerts every bureau involved. Source cases are never merged or closed automatically.
4. **Risk Radar.** An explainable 0–100 risk score per institution, based on complaint velocity, overdue files, multi-bureau exposure, systemic issues, escalations and conflicts. It recommends an RB inspection when a regulatory issue keeps recurring.
5. **Integration-ready ingestion.** It imports CPGRAMS / bureau CSVs that only carry the institution name as the citizen typed it. IRE resolves each row, and ambiguous rows are held back for an officer. A sample file is in `docs/samples/cpgrams_export_sample.csv`.
6. **Data sovereignty and accountability.** No complaint text goes to external AI services. Access is role-based and enforced on the server, every action is audit-logged, and every suggestion is advisory: officers decide.

---

## Quick start — Windows, one click (recommended for the demo)

1. Install Python 3.12+ (tick *Add python.exe to PATH*). Portable Node.js is already in `tools\node`.
2. Double-click **`start-local.bat`**. It sets up everything on the first run, seeds the demo data into a local SQLite file and opens **http://localhost:5173**. Later runs work **without internet**.
3. Before each judge round, double-click **`reset-demo.bat`** to restore the fresh demo scenarios.

- API docs (live OpenAPI): **http://localhost:8000/api/docs**
- Backup demo video: `docs/NYAYA_SETU_backup_demo.mp4`

### Docker / PostgreSQL (deployment)

```bash
docker compose up -d --build
docker exec nyaya_setu_backend alembic upgrade head
docker exec nyaya_setu_backend python seed.py --reset
```

### Manual development setup

```bash
# backend
cd backend && python -m venv venv && venv\Scripts\activate   # (source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
python seed.py --reset
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev
```

### Tests

```bash
cd backend && python -m pytest tests/ -q        # 73 tests
```

The identity and overlap engines are pure Python. Their tests run without a database:

```bash
python -m pytest tests/test_identity_engine.py tests/test_overlap_engine.py --noconftest
```

To regenerate the benchmark: `python -m app.services.identity_benchmark`

## Project structure

```
NYAYA SETU/
├── start-local.bat            one-click local run (SQLite, no Docker)
├── reset-demo.bat             rebuild the demo dataset
├── docker-compose.yml         PostgreSQL deployment
├── backend/                   FastAPI · SQLAlchemy · Alembic
│   ├── app/
│   │   ├── api/v1/endpoints/  REST endpoints (cases, transfers, coordination, intelligence, reports …)
│   │   ├── services/          identity.py (IRE 2.0) · overlap.py (OCI-1.0, Risk Radar) · intelligence.py
│   │   ├── models/            database tables
│   │   ├── data/registry.py   fictional demo registry (bureaus, institutions)
│   │   └── core/              config, JWT security
│   ├── alembic/               database migrations
│   ├── tests/                 pytest suite
│   └── seed.py                demo scenarios S1–S6 + background cases
├── frontend/                  React 18 · TypeScript · Vite · Tailwind
│   └── src/
│       ├── pages/             dashboard, intelligence, cases, coordination, reports, admin …
│       ├── components/        design system (ui/), layout, brand (particle wordmark)
│       ├── api/               typed API clients
│       └── lib/               domain metadata, formatting
├── docs/
│   ├── problem-alignment.md   PS 26264 requirement → feature mapping
│   ├── ARCHITECTURE.md        architecture, data model, security
│   ├── samples/               sample CPGRAMS export for the import demo
│   └── NYAYA_SETU_backup_demo.mp4
└── tools/node/                portable Node.js runtime
```

## Demo accounts

All passwords are `Demo@123456`, except admin, which is `Admin@123456`. The login page also has **one-click demo role** buttons.

| Role | E-mail |
|---|---|
| Senior Management (Director, Monitoring) | management@aicte.demo |
| Regulation Bureau officer | officer1@aicte.demo |
| PGRC grievance officer | officer2@aicte.demo |
| Approval Bureau officer | officer3@aicte.demo |
| Coordination reviewer | reviewer@aicte.demo |
| System administrator | admin@aicte.demo |
| Data manager (imports) | datamgr@aicte.demo |

## 5-minute judge demo

The full script, with links, is in-app under **Help & Demo Guide**.

1. **PGRC officer → Register complaint.** Paste *"Students of A.I.E.T. Faridabad are charged extra fees"*. IRE links **AIET** from the acronym plus the city.
2. **Save.** The system detects that RB and FIN already have files on AIET and raises **"Potential Overlapping Cases – Coordination Required"**.
3. **Overlap Radar → AIET.** Shows the bureau lanes, rule C2 (parallel directions), a duplicate from the same complainant, and RB as the proposed lead.
4. **Start One-Voice coordination.** Creates the lead and supporting bureaus, tasks and deadlines, and alerts the officers.
5. **Command Centre and Reports.** Shows the PS dashboard numbers, plus Gangotri's **critical** closure-vs-enforcement conflict and the monthly/quarterly performance report.

## Architecture

| Layer | Technology |
|---|---|
| Frontend | React 18 · TypeScript · Vite · Tailwind (custom design system, canvas particle wordmark, Recharts) |
| Backend | FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 15 (SQLite for the one-click demo) |
| Intelligence | `services/identity.py` (IRE), `services/overlap.py` (OCI, Risk Radar), `services/intelligence.py` (DB glue + alert scanner) |
| Auth | JWT bearer tokens · role-based, bureau-scoped access |

Key new APIs:

- `/intelligence/resolve`, `/intelligence/benchmark`
- `/intelligence/overlaps`, `/intelligence/overlaps/{id}/coordinate`
- `/intelligence/risk`, `/intelligence/institutions/{id}/360`, `/intelligence/pulse`, `/intelligence/alerts/scan`
- `/analytics/overview`, `/analytics/performance?period=monthly|quarterly`, `/analytics/regions`
- `/transfers`, `/transfers/{id}/respond`
- `/cases/{id}/attachments`

## Honest limitations

- All data is synthetic. Matching thresholds and risk weights are transparent defaults that must be calibrated on AICTE historical data.
- There is no live CPGRAMS or e-Office connection; CSV ingestion is the integration path in this prototype.
- Timeline rules (e.g. PGRC 30 days, RB 60 days) are configurable demo values, not official AICTE policy.
- Notifications are in-app only. E-mail and SMS gateways are not configured.

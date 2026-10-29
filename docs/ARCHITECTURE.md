# NYAYA SETU — Architecture

```
            ┌──────────────────────────── Browser (React 18 + TypeScript) ───────────────────────────┐
            │ Command Centre · Overlap Radar · Risk Radar · Identity Lab · Cases · Transfers ·        │
            │ Coordination · Review Inbox · Reports · Alerts · Imports · Users · Audit · Help        │
            └───────────────────────────────────────┬────────────────────────────────────────────────┘
                                                    │ REST / JSON + JWT (role & bureau scoped)
            ┌───────────────────────────────────────▼────────────────────────────────────────────────┐
            │ FastAPI  /api/v1                                                                        │
            │  auth · users · bureaus · institutions · cases · transfers · deadline-extensions        │
            │  relationships · coordination · notifications · analytics · performance · reports       │
            │  imports · audit · intelligence                                                         │
            ├─────────────────────────────────────────────────────────────────────────────────────────┤
            │ Intelligence layer (pure Python, offline, explainable)                                  │
            │  services/identity.py      IRE 2.0  — which institution is this complaint about?        │
            │  services/overlap.py       OCI-1.0  — duplicate / action conflict / related / independent│
            │                            Lead-bureau proposal · Risk Radar score                      │
            │  services/intelligence.py  DB glue · Institution 360° · background alert scanner (15 min)│
            ├─────────────────────────────────────────────────────────────────────────────────────────┤
            │ SQLAlchemy 2 · Alembic  →  PostgreSQL 15 (deployment)  /  SQLite (one-click local demo)  │
            └─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Request flow — registering a complaint

1. The officer pastes the complaint text. `POST /intelligence/resolve` returns the candidate institutions, each with its evidence: ID, acronym, domain, location, and fuzzy or transliterated name.
2. The officer confirms the institution and submits with `POST /cases`. This assigns the case number `AICTE-NS-YYYY-NNNNN`, records the timeline and writes the first action.
3. The overlap engine compares the new case with every other file on the same institution. When another bureau's file overlaps, the officers involved and the reviewers are notified and the UI shows **"Potential Overlapping Cases – Coordination Required"**.
4. On Overlap Radar, a reviewer opens a One-Voice coordination with `POST /intelligence/overlaps/{id}/coordinate`. This creates:
   - a lead bureau and the supporting bureaus;
   - tasks with deadlines;
   - acknowledgements from each bureau;
   - an audit trail.

Source cases are never merged or closed automatically.

## Data model (core tables)

| Table | Purpose |
|---|---|
| `institutions`, `institution_identifiers` | Master record: AICTE Permanent ID, AISHE code, aliases, domains, location |
| `bureaus`, `users` | Bureaus/Cells (RB, PGRC, AB, ACAD, FIN) and role-based users |
| `cases`, `case_actions`, `case_assignments`, `case_attachments` | Complaint lifecycle, action history, officer assignment, SHA-256 documents |
| `transfer_requests`, `deadline_rules`, `case_deadlines`, `deadline_extension_requests` | Movement between bureaus and timelines/SLA |
| `case_relationships`, `relationship_reviews` | Suggested and confirmed links (human in the loop) |
| `coordination_items`, `coordination_participants`, `coordination_tasks` | One-Voice coordination with lead bureau |
| `notifications`, `audit_events`, `import_jobs`, `import_rows` | Alerts, accountability, CSV/CPGRAMS ingestion |

## Security

- **JWT bearer tokens.** Server-side role checks cover 6 roles.
- **Bureau-scoped access.** Officers see their own bureau's files in full. Other bureaus' overlap metadata stays visible, because it is needed to avoid duplicate action.
- **Self sign-up is safe.** It only creates a *pending* bureau officer. An admin assigns the bureau and approves the account.
- **Audited actions.** Every state change is written to `audit_events`.
- **No external AI calls.** No complaint text leaves the server.

## Tests

`cd backend && python -m pytest tests/ -q` runs 73 tests. They cover:

- auth;
- the case lifecycle;
- relationships, analytics and imports;
- the identity engine and the overlap engine;
- the intelligence API and the user-account lifecycle.

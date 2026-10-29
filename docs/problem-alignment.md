# NYAYA SETU — Problem Alignment (SIH PS 26264)

**Problem Statement ID:** 26264
**Title:** Integrated Dashboard for Monitoring and Tracking Institution-Related Complaint Cases Across AICTE Bureaus/Cells
**Organization / Department:** AICTE — Regulation Bureau · **Category:** Software · **Theme:** Smart Automation

## Objectives → implementation

| PS objective | Implementation |
|---|---|
| View all institution-related complaints in one place | All Cases (search across every bureau), Command Centre, Ctrl K search |
| Identify the Bureau/Cell currently handling each case | `Case.bureau_id`, bureau chips on every list, "Presently with" on case detail |
| Track complete status and movement | 12-stage guarded lifecycle, lifecycle stepper, chronological timeline, transfer history |
| Identify RB/PGRC overlaps and multi-bureau handling | Overlap Radar (OCI-1.0): duplicate / action conflict / related / independent |
| Avoid duplication, ensure coordination | Lead-bureau proposal + One-Voice coordination items with acknowledgements and tasks |
| Monitor pending, disposed, under-process, transferred, escalated | `/analytics/overview` → Command Centre KPI tiles |
| Institution-, region-, bureau-, status-wise reports | Reports tabs + CSV/PDF exports |
| Alerts for pending cases and approaching timelines | Background alert scanner (15 min): SLA breach, approaching, pending reminder, escalation, overlap |

## Key features → implementation

1. **Centralized institution profile** — Institution 360° (`/intelligence/institutions/{id}/360`): identifiers, aliases, consolidated history, bureau split, cross-bureau timeline, risk.
2. **Complaint/case tracking** — case ID, receipt date, category, status, bureau, officer, last action + date, next action, expected disposal (all shown on case detail and list).
3. **Cross-bureau overlap detection** — automatic, alert raised on case creation and by the scanner; linking via Review Inbox and coordination.
4. **Real-time dashboard** — all PS counters, institution-wise status, bureau workload, ageing, trend, live activity feed.
5. **Workflow & action history** — officer, bureau, timestamp, remarks, supporting documents (SHA-256), transfer/escalation history.
6. **Search & filters** — institution name, AICTE Permanent ID, case ID, bureau, region, category, status, date range.
7. **Alerts & notifications** — duplicate/overlap, pending reminders, escalation alerts, timeline/SLA alerts.
8. **Reports & analytics** — bureau-wise, region-wise, institution-wise history, ageing, disposal rate, overlap report, monthly & quarterly (FY) performance.

## Innovation expected → implementation

"Identify complaints relating to the same institution even when descriptions or case references are different":
**Institution Identity Resolution Engine (IRE 2.0)** — acronyms, abbreviations, typos, Devanagari transliteration, AICTE/AISHE IDs, e-mail/web domain, phone, pincode and location fused with explainable noisy-OR scoring. Benchmark: F1 0.99 vs 0.37 (exact lookup) and 0.28 (plain fuzzy) on a reproducible synthetic set (`python -m app.services.identity_benchmark`).
The PS example (PGRC case under process + RB action initiated on the same institution) is seeded exactly and produces **"Potential Overlapping Cases – Coordination Required"**.

## Known limitations

Synthetic data only; thresholds and weights need calibration on AICTE historical data; no live CPGRAMS/e-Office connector (CSV ingestion provided); timeline rules are configurable demo values; in-app notifications only.

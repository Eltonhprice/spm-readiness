# SPM Readiness Skill — Design Spec

**Date:** 2026-08-04
**Status:** Approved
**Location:** `~/.claude/skills/spm-readiness/` (standalone, no SAGE dependency)

---

## 1. Purpose

A standalone Claude Code skill that assesses a ServiceNow instance's readiness across the full SPM (Strategic Portfolio Management) suite. Given export files from a client instance, the skill:

1. Runs deterministic Python analysis to extract metrics from the exports
2. Applies a Claude AI overlay to score readiness, write three-beat findings, and produce narrative
3. Writes two deliverables: a structured AS-IS markdown report and a self-contained HTML leadership deck

**Hard rules inherited from SAGE:**
- No disposition language in any output (should / recommend / migrate / replace) — facts only
- Every observation must be verifiable from export data
- Every metric flagged as `not_collected` when the source table is absent — no fabricated values

---

## 2. Architecture (Approach B — SAGE-mirrored)

```
Python modules (deterministic)          Claude AI overlay
─────────────────────────────           ────────────────────────────────
load.py       → typed data buckets      Reads metrics.json
metrics.py    → compute all blocks      Scores 5 dimensions × 7 modules
facts.py      → metrics.json + CSVs     Writes three-beat Key Observations
scoring.py    → readiness_scorecard     Writes SPM-NNN findings table
                                        Writes full markdown profile
html_deck.py  → leadership HTML deck    (pure render of metrics.json — no AI)
```

The Python layer owns all numbers. Claude owns all narrative and scoring rationale. The HTML deck is a deterministic render — no AI content.

---

## 3. Directory Structure

```
~/.claude/skills/spm-readiness/
  SKILL.md
  docs/
    2026-08-04-spm-readiness-skill-design.md   ← this file
  collectors/
    demand/
      pm_demand.js
      pm_demand_category.js
    ppm/
      pm_project.js
      pm_project_task.js
      pm_program.js
    resource/
      pm_resource_plan.js
      pm_resource_allocation.js
    financial/
      pm_project_financials.js
      pm_cost_plan.js
      pm_budget_plan.js
    agile/
      rm_story.js
      rm_sprint.js
      rm_team.js
    apm/
      apm_appl_now.js
      apm_appl_lifecycle.js
    innovation/
      innovation_idea.js
      innovation_challenge.js
    governance/
      timesheet_period.js
      timesheet_entry.js
      pm_project_status.js
      sysapproval_approver.js          ← filtered to SPM tables only
    scoring/
      pm_scoring_criterion.js
      pm_portfolio_score.js
    pa/
      pa_scorecard.js                  ← filtered to SPM indicator sources
    sidecars/
      _sidecar_spm_adoption.js         ← plugin activation + role counts + NX workspace
      _sidecar_portfolio_health.js     ← completeness scores + staleness counts
  scripts/
    __init__.py
    run_analysis.py
    load.py
    metrics.py
    facts.py
    profile.py
    findings.py
    scoring.py
    html_deck.py
    status.py
    theme.py
    icons.py
    generate_mock.py
```

---

## 4. Path Convention

Mirrors SAGE without requiring it:

| Role | Path |
|---|---|
| Inputs | `spm-inputs/<client>/` |
| Outputs | `spm-outputs/<client>/` |
| Metrics | `spm-outputs/<client>/metrics.json` |
| CSVs | `spm-outputs/<client>/data/*.csv` |
| Profile | `spm-outputs/<client>/as-is-spm-readiness-profile.md` |
| Deck | `spm-outputs/<client>/spm-leadership-deck.html` |

The `<client>` folder name is extracted from the user's request. If ambiguous, Claude asks.

**Invocation:**
```bash
python -m scripts.run_analysis \
  --input spm-inputs/<client> \
  --out   spm-outputs/<client>
```

---

## 5. SPM Modules, Tables & Metrics

### 5.1 Demand Management
**Tables:** `pm_demand`, `pm_demand_category`

| Metric | Notes |
|---|---|
| Total demand records | |
| Active / closed / cancelled counts | by `state` field |
| Demand by category | from `pm_demand_category` join |
| Avg age of open demands (days) | `sys_created_on` to today |
| Demands linked to projects (%) | `project` field populated |
| Demands with no owner (%) | `assigned_to` empty |
| Demands with approval records (%) | cross-read from `sysapproval_approver` |

### 5.2 Project Portfolio Management
**Tables:** `pm_project`, `pm_project_task`, `pm_program`

| Metric | Notes |
|---|---|
| Total projects by state | planning / in-progress / closed / on-hold |
| Projects grouped under programs (%) | `program` field populated |
| Avg schedule variance (days) | planned vs actual end dates where both populated |
| Shell projects (%) | projects with zero tasks |
| Projects with no business owner (%) | `business_owner` or equivalent empty |
| Program count + projects-per-program distribution | |
| Projects with status report in last 30 days (%) | cross-read from `pm_project_status` |

### 5.3 Resource Management
**Tables:** `pm_resource_plan`, `pm_resource_allocation`

| Metric | Notes |
|---|---|
| Total resource plans | |
| Plans linked to projects (%) | `project` field populated |
| Allocation records: allocated vs actual hours coverage | both fields present % |
| Resource utilisation rate | allocated / available where both fields populated |
| Plans with no named resource (%) | `resource` field empty |
| Plans with matching timesheet entries (%) | cross-read from `timesheet_entry` |

### 5.4 Financial Management
**Tables:** `pm_project_financials`, `pm_cost_plan`, `pm_budget_plan`

| Metric | Notes |
|---|---|
| Projects with cost plans attached (%) | financial discipline indicator |
| Projects with budget plans (%) | budget governance indicator |
| Cost plan records by type | capex / opex where `cost_type` field present |
| Budget vs actual variance availability (%) | both fields populated |
| Projects with no financial record at all (%) | |

### 5.5 Agile Development
**Tables:** `rm_story`, `rm_sprint`, `rm_team`

| Metric | Notes |
|---|---|
| Total stories by state | |
| Teams count + stories-per-team distribution | |
| Sprints: completed vs active | |
| Avg velocity | story points per sprint where populated |
| Stories with no sprint assignment (%) | backlog health indicator |
| Stories with no team assignment (%) | |

### 5.6 Application Portfolio Management
**Tables:** `apm_appl_now`, `apm_appl_lifecycle`

| Metric | Notes |
|---|---|
| Total application records | |
| Applications with lifecycle stage populated (%) | maturity indicator |
| Applications with business owner populated (%) | accountability indicator |
| Applications linked to CMDB services (%) | `cmdb_ci` field populated |
| Applications with lifecycle record (%) | `apm_appl_lifecycle` join coverage |

### 5.7 Innovation Management
**Tables:** `innovation_idea`, `innovation_challenge`

| Metric | Notes |
|---|---|
| Total ideas by state | submitted / under review / approved / rejected |
| Ideas linked to demands or projects (%) | conversion rate where traceable |
| Challenges count + ideas-per-challenge ratio | |
| Ideas with no owner (%) | governance gap |

---

## 6. Additional Signal Tables

### 6.1 Timesheet & Work Logging
**Tables:** `timesheet_period`, `timesheet_entry`

| Metric | Notes |
|---|---|
| Active timesheet periods | |
| Entries per active period | adoption density |
| % of resource plans with matching timesheet entries | cross-read |

### 6.2 Approval & Governance Chains
**Table:** `sysapproval_approver` (filtered: `source_table` IN SPM tables)

| Metric | Notes |
|---|---|
| % of demands with at least one approval record | |
| % of projects with gate approvals | |
| Avg approval cycle time (days) | where `approved_on` - `sys_created_on` available |

### 6.3 Project Status Reporting
**Table:** `pm_project_status`

| Metric | Notes |
|---|---|
| Total status reports | |
| % of active projects with a status report in last 30 days | |
| Report frequency distribution | reports per project histogram |

### 6.4 Portfolio Scoring Models
**Tables:** `pm_scoring_criterion`, `pm_portfolio_score`

| Metric | Notes |
|---|---|
| Scoring criteria count | |
| % of demands with a portfolio score attached | |
| % of projects with a portfolio score attached | |

### 6.5 SPM Role Adoption
**Source:** `_sidecar_spm_adoption.js` (GlideAggregate over `sys_user_has_role`)

| Role | What it signals |
|---|---|
| `portfolio_manager` | Portfolio governance coverage |
| `project_manager` | PPM process ownership |
| `resource_manager` | Resource management ownership |
| `financial_analyst` | Financial governance coverage |
| `it_demand_manager` | Demand process ownership |

### 6.6 Performance Analytics for SPM
**Tables:** `pa_scorecard`, `pa_indicator_source`

| Metric | Notes |
|---|---|
| Scorecard count tied to SPM tables | |
| Indicator sources referencing PM/RM tables | KPI instrumentation coverage |

### 6.7 Data Staleness
**Source:** `_sidecar_portfolio_health.js` (GlideAggregate)

| Metric | Notes |
|---|---|
| Projects with no update in 90+ days (count + %) | |
| Demands with no update in 90+ days (count + %) | |
| Flagged in profile as a data quality caveat — not counted against readiness score |

### 6.8 SPM Next Experience Workspace
**Source:** `_sidecar_spm_adoption.js` (GlidePluginManager + `sys_ux_app_config`)

| Metric | Notes |
|---|---|
| `sn-spm-workspace` active (bool) | modern UI adoption indicator |

---

## 7. Sidecar Scripts

### `_sidecar_spm_adoption.js`
GlideAggregate + GlidePluginManager. Outputs a single JSON object:
```json
{
  "plugins": {
    "com.snc.sdlc.ppm_core": true,
    "com.snc.rm": true,
    "com.snc.financial_mgmt": false,
    "com.snc.agile": true,
    "com.snc.apm": false,
    "com.snc.innovation_mgmt": false
  },
  "roles": {
    "portfolio_manager": 4,
    "project_manager": 12,
    "resource_manager": 3,
    "financial_analyst": 0,
    "it_demand_manager": 2
  },
  "spm_workspace_active": true,
  "active_users_90d": {
    "pm_demand": 18,
    "pm_project": 24,
    "pm_resource_plan": 6
  }
}
```

### `_sidecar_portfolio_health.js`
GlideAggregate completeness and staleness. Outputs:
```json
{
  "project_completeness_pct": 61,
  "demand_priority_set_pct": 74,
  "resource_plan_named_pct": 52,
  "projects_stale_90d": 34,
  "projects_stale_90d_pct": 28,
  "demands_stale_90d": 19,
  "demands_stale_90d_pct": 15
}
```

Both sidecars follow SAGE sidecar conventions:
- IIFE pattern
- Single JSON object output (no array, no chunking)
- `isValid()` guard → `{}` + `TABLE_NOT_FOUND` if absent
- Footer: `// SPM sidecar: name=<name> status=COMPLETE`
- Saved as `_sidecar_<name>.txt`

---

## 8. Collector Script Conventions

All table collectors follow the SAGE background script pattern:
- IIFE `(function() { ... })();`
- Constants: `TABLE`, `CHUNK_SIZE` (5000), `CHUNK_INDEX` (0), `FILTER`, `FIELDS`
- `isValid()` guard → prints `[]` + `TABLE_NOT_FOUND` status line if table absent
- Count via `GlideAggregate` before windowed query
- Window: `gr.chooseWindow(start, start + CHUNK_SIZE, true)`
- Footer: `// SPM collector: table=X chunk=N rows=N total=N status=COMPLETE|MORE_RECORDS_EXIST`
- Chunked saves: `<table>.001.txt`, `<table>.002.txt`, etc.
- Saved as `<table>.txt` in `spm-inputs/<client>/<domain>/`

---

## 9. Scoring Methodology

### 9.1 Dimensions (applied to every module)

| Dimension | What it measures | Weight |
|---|---|---|
| Activation | Plugin active, core tables valid and present | 20% |
| Data Volume | Record counts indicate real usage (not test install) | 20% |
| Data Completeness | % of key fields populated across records | 25% |
| Process Adoption | Approvals, timesheets, status reports, scoring models firing | 25% |
| Integration | Records linked across modules (demand→project→resource→financial) | 10% |

### 9.2 RAG Thresholds

| RAG | Score |
|---|---|
| Green | ≥ 70% |
| Amber | 40–69% |
| Red | < 40% |

### 9.3 Module Score

Module % = weighted average of its 5 dimension scores.

### 9.4 Overall SPM Readiness Score

Simple average of 7 module scores. Displayed on deck cover slide.

### 9.5 Not-Collected Handling

If a table is absent, its dimension is marked `not_collected` and excluded from the module score denominator. The profile flags explicitly which tables were not collected. No score is fabricated from missing data.

### 9.6 Staleness Caveat

Staleness counts (§6.7) are reported as a data quality note in the profile. They are **not** deducted from any dimension score — they are a confidence qualifier, not a readiness penalty.

---

## 10. metrics.json Schema

Top-level keys:

```json
{
  "modules": {
    "demand": { ... },
    "ppm": { ... },
    "resource": { ... },
    "financial": { ... },
    "agile": { ... },
    "apm": { ... },
    "innovation": { ... }
  },
  "governance": {
    "timesheets": { ... },
    "approvals": { ... },
    "status_reports": { ... },
    "scoring_models": { ... }
  },
  "roles": { ... },
  "pa_adoption": { ... },
  "data_quality": {
    "projects_stale_90d": 34,
    "demands_stale_90d": 19
  },
  "spm_workspace_active": true,
  "coverage_matrix": [ ... ],
  "_context": {
    "exports_dir": "spm-inputs/mock",
    "generated_on": "2026-08-04",
    "client": "mock"
  }
}
```

Each module block:
```json
{
  "demand": {
    "total": 847,
    "by_state": { "open": 412, "closed": 310, "cancelled": 125 },
    "avg_age_open_days": 47,
    "linked_to_project_pct": 44,
    "no_owner_pct": 18,
    "with_approval_pct": 38,
    "plugin_active": true,
    "footprint_status": {
      "total": { "value": 847, "status": "measured" },
      "linked_to_project_pct": { "value": 44, "status": "measured" },
      "with_approval_pct": { "value": 38, "status": "measured" }
    }
  }
}
```

Coverage matrix rows (35 rows total, 5 per module):
```json
{
  "module": "demand",
  "dimension": "Process Adoption",
  "status": "measured",
  "value_token": "38%",
  "rag": "red",
  "note": "38% of demands have approval records"
}
```

---

## 11. Output Files

### 11.1 Markdown Report — `as-is-spm-readiness-profile.md`

Section order:
1. Branded header (Accenture purple, `SPM Readiness · AS-IS` badge)
2. How This Report Was Generated
3. Executive Summary (3–4 `[M]` sentences)
4. SPM Readiness Scorecard (7 modules × 5 dimensions heat-map table)
5. Module Profiles — one section per module (status-tagged metrics table + three-beat Key Observations)
6. Cross-Module Integration Analysis
7. Governance & Process Adoption
8. Data Quality Flags (staleness, shell records, unpopulated owners)
9. Leading-Practice Coverage Matrix (35 rows)
10. Key Observations (three-beat bullets: `[M]` · `[I]` · `[I]`)
11. Candidate Findings for FDE Review (`SPM-001` … `SPM-N` structured table)
12. Branded footer
13. Appendix A — Collector Coverage

**Three-beat format:**
- `[M]` clause — carries all numbers, sourced from `metrics.json`, deterministic
- `[I]` consequence clause — AI overlay, no numbers
- `[I]` open question — AI overlay, no numbers

**Finding prefix:** `SPM-NNN`

### 11.2 HTML Leadership Deck — `spm-leadership-deck.html`

Self-contained (no external dependencies). 6 slides:

| Slide | Content |
|---|---|
| 1 — Cover | Client name, date, Overall SPM Readiness Score (large, RAG-coloured) |
| 2 — Readiness at a Glance | Radar/spider chart of 7 module scores + overall score tile |
| 3 — Module Scorecard | Heat-map table: 7 modules × 5 dimensions, RAG cells |
| 4 — Governance & Adoption | Approval %, timesheet %, status report cadence, scoring model coverage |
| 5 — Top Findings | Top 5 findings (SPM-001 to SPM-005), RAG badge + one-line impact each |
| 6 — Recommended Next Steps | Structured placeholder — labelled "For Discussion"; consultant fills in |

Slide 6 contains no AI-generated recommendations. This maintains the RDE facts-only boundary and creates a natural handoff into FDE.

### 11.3 CSVs — `spm-outputs/<client>/data/`

| File | Content |
|---|---|
| `demand_summary.csv` | Demand counts by state, category, age bucket |
| `project_portfolio.csv` | Projects by state, program, schedule variance |
| `resource_utilisation.csv` | Resource plans: linked %, utilisation rate, named % |
| `financial_coverage.csv` | Projects with cost plan / budget plan / neither |
| `agile_adoption.csv` | Stories by state/sprint, team distribution, velocity |
| `apm_coverage.csv` | Applications by lifecycle stage, owner %, CMDB linkage % |
| `innovation_pipeline.csv` | Ideas by state, conversion %, challenge distribution |
| `readiness_scorecard.csv` | Full 7 × 5 scoring matrix with RAG and % per cell |

---

## 12. SKILL.md Workflow

```
Step 0 — Identify client
  Extract client name from the user's request.
  If unclear, ask: "Which client folder? (e.g. mock, acme)"
  Confirm input folder: spm-inputs/<client>/

Step 1 — Check collectors
  List files found in spm-inputs/<client>/
  Report: which tables are present vs missing.
  For any missing critical table, name the collector script to run
  (collectors/<domain>/<table>.js) and wait for the user to re-run.

Step 2 — Run analysis
  python -m scripts.run_analysis \
    --input spm-inputs/<client> \
    --out   spm-outputs/<client>
  Writes: metrics.json + all CSVs

Step 3 — AI overlay
  Read spm-outputs/<client>/metrics.json
  Score each module across 5 dimensions → readiness_scorecard.csv
  Write three-beat Key Observations per module
  Write SPM-001 … SPM-N findings table
  Apply scoring rationale narrative

Step 4 — Write outputs
  Write as-is-spm-readiness-profile.md (deterministic sections + AI overlay sections)
  python -m scripts.html_deck (pure render of metrics.json → spm-leadership-deck.html)

Step 5 — Report to user
  - Overall SPM Readiness Score: XX%
  - Weakest module: <name> — XX%
  - Top 3 findings: SPM-001, SPM-002, SPM-003 (one-line each)
  - Profile: spm-outputs/<client>/as-is-spm-readiness-profile.md
  - Deck: spm-outputs/<client>/spm-leadership-deck.html
  - Next step: "Share the HTML deck with leadership, or run /fde-review to start requirements."
```

---

## 13. SKILL.md Frontmatter

```yaml
---
name: spm-readiness
description: Assess ServiceNow SPM readiness from export files. Use when the user wants
  to evaluate SPM adoption, score portfolio management maturity across Demand, PPM,
  Resource, Financial, Agile, APM, and Innovation modules, or produce a leadership
  readiness deck from ServiceNow SPM table exports.
---
```

---

## 14. Python Modules — Responsibilities

| Module | Role |
|---|---|
| `run_analysis.py` | Orchestrates: discover → load → compute → write |
| `load.py` | Routes files to typed buckets per module; loads sidecars |
| `metrics.py` | Computes all 7 module blocks + governance + roles + PA + data quality |
| `facts.py` | Serialises `metrics.json` + companion CSVs |
| `profile.py` | Renders the deterministic sections of the AS-IS markdown profile |
| `findings.py` | Produces structured `Finding` objects (prefix `SPM-`) |
| `scoring.py` | RAG + % scoring engine; writes `readiness_scorecard.csv` |
| `html_deck.py` | Renders `spm-leadership-deck.html` from `metrics.json` — pure render, no AI |
| `status.py` | Status trichotomy: `measured` / `not_collected` / `not_applicable` |
| `theme.py` | `render_header()`, `render_footer()`, `section_badge()` — Accenture purple |
| `icons.py` | Tabler SVG path constants |
| `generate_mock.py` | Generates synthetic mock data for testing |

---

## 15. Decisions Deferred to Implementation

- Exact `FILTER` strings per collector (depends on client instance scope; documented as defaults in each `.js`)
- Velocity calculation method when story points are absent (fallback: story count per sprint)
- Exact field names for `business_owner` on `pm_project` (varies by instance customisation; `load.py` probes multiple candidates)
- HTML deck charting library choice (Chart.js CDN vs inline SVG — inline SVG preferred for true offline use)
- Whether `pm_project_status` warrants its own domain subfolder or goes under `ppm/`

---

## 16. Out of Scope

- FDE / recommendations — the HTML deck slide 6 is a deliberate placeholder
- Live MCP connection to ServiceNow — input is always files
- Integration with SAGE `engagements/` or `rde/` paths — skill is fully self-contained
- Automated PDF export — consultant prints from browser

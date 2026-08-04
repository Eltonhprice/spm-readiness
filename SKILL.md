# SPM Readiness Assessment Skill

Assess ServiceNow SPM (Strategic Portfolio Management) module readiness from export files. Produces a scored AS-IS readiness profile (markdown), self-contained HTML leadership deck, and 8 companion CSVs.

## Quick Reference

**Input:** `engagement/<client>/` — collector .txt exports per domain subfolder  
**Output:** `spm-outputs/<client>/` — `metrics.json`, `as-is-spm-readiness-profile.md`, `spm-leadership-deck.html`, `data/*.csv`

**Run full analysis:**
```bash
# RDE mode (default) — facts-only, slide 6 is a consultant placeholder
python -m scripts.run_analysis --input engagement/<client> --out spm-outputs/<client>

# FDE mode — slide 6 populated with priority focus areas from top findings
python -m scripts.run_analysis --input engagement/<client> --out spm-outputs/<client> --mode fde
```

**Generate mock data (for demo/testing):**
```bash
python -m scripts.generate_mock --out engagement/mock
python -m scripts.run_analysis --input engagement/mock --out spm-outputs/mock
```

**Render HTML deck only (from existing metrics.json):**
```bash
python -m scripts.html_deck --metrics spm-outputs/<client>/metrics.json --out spm-outputs/<client> [--mode rde|fde]
```

## Coverage

7 SPM modules assessed across 5 readiness dimensions:

| Module | Key Tables |
|---|---|
| Demand Management | `pm_demand`, `pm_demand_category` |
| Project Portfolio (PPM) | `pm_project`, `pm_project_task`, `pm_program` |
| Resource Management | `pm_resource_plan`, `pm_resource_allocation` |
| Financial Management | `pm_project_financials`, `pm_cost_plan`, `pm_budget_plan` |
| Agile Development | `rm_story`, `rm_sprint`, `rm_team` |
| Application Portfolio (APM) | `apm_appl_now`, `apm_appl_lifecycle` |
| Innovation Management | `innovation_idea`, `innovation_challenge` |

**Governance overlays:** `timesheet_period`, `timesheet_entry`, `pm_project_status`, `sysapproval_approver`  
**Scoring:** `pm_scoring_criterion`, `pm_portfolio_score`  
**Performance Analytics:** `pa_scorecard`  
**Sidecars:** `_sidecar_spm_adoption`, `_sidecar_portfolio_health`

## Scoring

RAG thresholds: **Green ≥ 70%** · **Amber 40–69%** · **Red < 40%**

5 dimensions with weights:
- Activation 20% · Data Volume 20% · Data Completeness 25% · Process Adoption 25% · Integration 10%

Not-installed modules (`plugin_active = False`) score as `not_collected` — they do not count as Red.

## Data Collection Workflow

1. Open Scripts-Background in the client ServiceNow instance (Global scope)
2. For each domain, paste the relevant `.js` from `collectors/<domain>/`
3. Run the script, copy the output (JSON array + footer comment)
4. Save as `engagement/<client>/<domain>/<table>.txt`
5. Run the two sidecars last: `_sidecar_spm_adoption.js` and `_sidecar_portfolio_health.js` → save to `engagement/<client>/sidecars/`

For tables > 5,000 rows, the footer will say `status=MORE_RECORDS_EXIST` — increment `CHUNK_INDEX` at the top of the script and save chunks as `<table>.001.txt`, `<table>.002.txt`, etc.

## Hard Rules

- **No disposition language** in any output: no *should*, *recommend*, *migrate*, *replace*
- Every metric is `not_collected` when the source table is absent — never fabricate values
- HTML deck is fully self-contained — no CDN, no external CSS/JS/font references
- `[M]` bullet = deterministic metric from `metrics.json` · `[I]` bullet = AI-authored, no numbers

## Output Files

| File | Description |
|---|---|
| `metrics.json` | Machine-readable facts — source of truth for all numbers |
| `as-is-spm-readiness-profile.md` | Full AS-IS markdown profile with scorecard, module sections, findings |
| `spm-leadership-deck.html` | Self-contained 6-slide HTML deck (Cover · Radar · Scorecard · Governance · Findings · For Discussion) |
| `data/demand_summary.csv` | Demand state/priority/linkage breakdown |
| `data/project_portfolio.csv` | Project state/phase/program coverage |
| `data/resource_utilisation.csv` | Resource plan utilisation rates |
| `data/financial_coverage.csv` | Financial record coverage by project |
| `data/agile_adoption.csv` | Sprint velocity and story point adoption |
| `data/apm_coverage.csv` | Application lifecycle stage coverage |
| `data/innovation_pipeline.csv` | Idea state and conversion to demand/project |
| `data/readiness_scorecard.csv` | Per-module, per-dimension scores + RAG |

## AI Overlay

After the deterministic pipeline runs, Claude can enrich Key Observations in the profile:

1. Open `spm-outputs/<client>/as-is-spm-readiness-profile.md`
2. For each module section marked `*(AI overlay — Stage 2)*`, replace the placeholder with 2–3 three-beat observations:
   - `[M]` — verbatim metric from `metrics.json` (exact numbers only)
   - `[I]` — consequence or pattern (no numbers)
   - `[I]` — open question for FDE discussion (no numbers)

## Directory Layout

```
spm-readiness/
  SKILL.md                        ← this file
  collectors/
    demand/                       ← pm_demand.js, pm_demand_category.js
    ppm/                          ← pm_project.js, pm_project_task.js, pm_program.js
    resource/                     ← pm_resource_plan.js, pm_resource_allocation.js
    financial/                    ← pm_project_financials.js, pm_cost_plan.js, pm_budget_plan.js
    agile/                        ← rm_story.js, rm_sprint.js, rm_team.js
    apm/                          ← apm_appl_now.js, apm_appl_lifecycle.js
    innovation/                   ← innovation_idea.js, innovation_challenge.js
    governance/                   ← timesheet_period.js, timesheet_entry.js,
    |                               pm_project_status.js, sysapproval_approver.js
    scoring/                      ← pm_scoring_criterion.js, pm_portfolio_score.js
    pa/                           ← pa_scorecard.js
    sidecars/                     ← _sidecar_spm_adoption.js, _sidecar_portfolio_health.js
  scripts/
    __init__.py
    status.py                     ← measured/not_collected/not_applicable helpers
    icons.py                      ← SVG icon paths for 7 modules
    theme.py                      ← colors, header/footer renderers
    load.py                       ← collector file parser and bucket router
    metrics.py                    ← all metric computation logic
    facts.py                      ← metrics.json writer + 8 CSV writers
    scoring.py                    ← 5-dimension weighted scoring + RAG
    findings.py                   ← SPM-NNN finding generator
    profile.py                    ← deterministic markdown profile writer
    html_deck.py                  ← 6-slide self-contained HTML deck renderer
    generate_mock.py              ← synthetic mock data for all 26 tables/sidecars
    run_analysis.py               ← full pipeline orchestrator
    test_*.py                     ← 9 test suites (45 tests)
  engagement/
    mock/                         ← tracked demo inputs (generated by generate_mock.py)
    <client>/                     ← real client exports (not tracked)
  spm-outputs/
    mock/                         ← tracked demo outputs
    <client>/                     ← real client outputs (not tracked)
  docs/
    2026-08-04-spm-readiness-skill-design.md
    plan-part1-foundation.md
    plan-part2-collectors.md
    plan-part3-python-core.md
    plan-part4-output-e2e.md
```

# SPM Readiness Skill — Implementation Plan Part 1: Foundation

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the skill directory structure, SKILL.md entry point, and the three foundation Python modules that every other module depends on.

**Architecture:** Standalone skill at `~/.claude/skills/spm-readiness/`. Python modules live in `scripts/`. Foundation layer = `status.py` (status envelopes), `theme.py` (HTML/MD branding), `icons.py` (SVG paths).

**Tech Stack:** Python 3.8+ standard library only. No external dependencies.

## Global Constraints

- Python 3.8+ standard library only — no pip installs
- Skill root: `C:\Users\elton.price\.claude\skills\spm-readiness\`
- Accenture purple: `#A100FF`
- No disposition language in any output (no: should, recommend, migrate, replace)
- Every metric must be `not_collected` when source data is absent — never fabricate values
- No `Co-Authored-By` trailers in commit messages

---

## Task 1: Directory Scaffold

**Files:**
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\SKILL.md`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\scripts\__init__.py`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\demand\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\ppm\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\resource\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\financial\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\agile\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\apm\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\innovation\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\governance\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\scoring\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\pa\.gitkeep`
- Create: `C:\Users\elton.price\.claude\skills\spm-readiness\collectors\sidecars\.gitkeep`

**Interfaces:**
- Produces: skill root directory tree ready for all subsequent tasks

- [ ] **Step 1: Create all collector subdirectories**

```powershell
$root = "$env:USERPROFILE\.claude\skills\spm-readiness"
$dirs = @(
  "collectors\demand", "collectors\ppm", "collectors\resource",
  "collectors\financial", "collectors\agile", "collectors\apm",
  "collectors\innovation", "collectors\governance", "collectors\scoring",
  "collectors\pa", "collectors\sidecars", "scripts", "docs"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force "$root\$d" | Out-Null }
Write-Host "Directories created."
```

Expected output: `Directories created.`

- [ ] **Step 2: Write `scripts/__init__.py`**

```python
# scripts/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 3: Write `SKILL.md`**

```markdown
---
name: spm-readiness
description: Assess ServiceNow SPM readiness from export files. Use when the user wants
  to evaluate SPM adoption, score portfolio management maturity across Demand, PPM,
  Resource, Financial, Agile, APM, and Innovation modules, or produce a leadership
  readiness deck from ServiceNow SPM table exports.
---

# SPM Readiness Assessment

## Overview

Reads ServiceNow SPM export files and produces:
1. A scored AS-IS readiness profile (markdown) — 7 modules × 5 dimensions, RAG + %
2. A self-contained HTML leadership deck — 6 slides, no external dependencies

AS-IS only. No recommendations, no disposition language.

## When to Use

- Consultant has run SPM collector scripts against a client instance
- User asks to assess SPM maturity, score portfolio readiness, or produce a leadership deck
- Input files are in `spm-inputs/<client>/`

## When NOT to Use

- No export files available (use collector scripts first)
- User wants recommendations — that is FDE scope, not this skill

## Workflow

> Prerequisite: Python 3.8+, standard library only. Run from the skill root directory.
> Input folder: `spm-inputs/<client>/` (relative to current working directory)
> Output folder: `spm-outputs/<client>/` (created automatically)

### Step 0 — Identify client

Extract the client folder name from the user's request.
If unclear, ask: "Which client folder should I use? (e.g. `mock`, `acme`)"
Store as `<client>`.

### Step 1 — Check collectors

List all `.txt` files found under `spm-inputs/<client>/`.
Report which tables are present vs missing.

Critical tables (skill degrades gracefully without optional ones):
- **Required:** `pm_demand.txt`, `pm_project.txt`
- **Recommended:** `pm_resource_plan.txt`, `pm_project_financials.txt`, `rm_story.txt`, `apm_appl_now.txt`
- **Optional:** all governance, scoring, PA, and sidecar files

For any missing critical table, tell the user which collector script to run:
`collectors/<domain>/<table>.js` — paste into ServiceNow Scripts-Background (Global scope), run, save output as `spm-inputs/<client>/<domain>/<table>.txt`

Wait for the user to confirm before proceeding if critical tables are missing.

### Step 2 — Run analysis

```bash
cd ~/.claude/skills/spm-readiness
python -m scripts.run_analysis \
  --input spm-inputs/<client> \
  --out   spm-outputs/<client>
```

This writes:
- `spm-outputs/<client>/metrics.json`
- `spm-outputs/<client>/data/*.csv` (8 files)

### Step 3 — AI overlay

Read `spm-outputs/<client>/metrics.json`.

For each of the 7 modules, score the 5 readiness dimensions:
- **Activation** (20%): plugin_active=true scores 100; false scores 0; not in sidecar scores 50 (unknown)
- **Data Volume** (20%): use VOLUME_THRESHOLDS — demand≥50→100, 10-49→60, 1-9→20, 0→0
- **Data Completeness** (25%): use the completeness % from the module's footprint_status block
- **Process Adoption** (25%): use approval %, timesheet %, status report %, scoring model coverage
- **Integration** (10%): use cross-module linkage % (demand→project, project→resource, etc.)

RAG thresholds: Green ≥70%, Amber 40–69%, Red <40%

If a dimension's source data is `not_collected`, exclude it from the weighted average (shrink denominator).

Write three-beat Key Observations per module:
- `[M]` clause — copy exact numbers from metrics.json, no rounding beyond what's there
- `[I]` consequence clause — one sentence, no numbers
- `[I]` open question — one sentence ending in "?"

Write SPM-001 … SPM-N findings table. One finding per significant Red or Amber dimension.
Finding columns: ID | Module | Dimension | RAG | Observation | Significance

### Step 4 — Write outputs

Write `spm-outputs/<client>/as-is-spm-readiness-profile.md` using the profile structure in §11.1 of the design spec.

Run html deck render:
```bash
python -m scripts.html_deck \
  --metrics spm-outputs/<client>/metrics.json \
  --out     spm-outputs/<client>/spm-leadership-deck.html
```

### Step 5 — Report to user

Report:
- Overall SPM Readiness Score: XX%
- Weakest module: `<name>` — XX% (RAG)
- Top 3 findings: SPM-001, SPM-002, SPM-003 (one line each)
- Profile path: `spm-outputs/<client>/as-is-spm-readiness-profile.md`
- Deck path: `spm-outputs/<client>/spm-leadership-deck.html`
- Next step: "Open the HTML deck in a browser to review, or share with the client team."

## Quick Reference

| Step | Command |
|---|---|
| Run full analysis | `python -m scripts.run_analysis --input spm-inputs/<client> --out spm-outputs/<client>` |
| Render deck only | `python -m scripts.html_deck --metrics spm-outputs/<client>/metrics.json --out spm-outputs/<client>/spm-leadership-deck.html` |
| Generate mock data | `python -m scripts.generate_mock --out spm-inputs/mock` |

## Collector Scripts

| Domain | Folder | Tables |
|---|---|---|
| Demand | `collectors/demand/` | `pm_demand`, `pm_demand_category` |
| PPM | `collectors/ppm/` | `pm_project`, `pm_project_task`, `pm_program` |
| Resource | `collectors/resource/` | `pm_resource_plan`, `pm_resource_allocation` |
| Financial | `collectors/financial/` | `pm_project_financials`, `pm_cost_plan`, `pm_budget_plan` |
| Agile | `collectors/agile/` | `rm_story`, `rm_sprint`, `rm_team` |
| APM | `collectors/apm/` | `apm_appl_now`, `apm_appl_lifecycle` |
| Innovation | `collectors/innovation/` | `innovation_idea`, `innovation_challenge` |
| Governance | `collectors/governance/` | `timesheet_period`, `timesheet_entry`, `pm_project_status`, `sysapproval_approver` |
| Scoring | `collectors/scoring/` | `pm_scoring_criterion`, `pm_portfolio_score` |
| PA | `collectors/pa/` | `pa_scorecard` |
| Sidecars | `collectors/sidecars/` | `_sidecar_spm_adoption`, `_sidecar_portfolio_health` |

## Finding Prefixes

`SPM-001` … `SPM-NNN` — single prefix for all modules.
```

- [ ] **Step 4: Verify structure**

```powershell
Get-ChildItem "$env:USERPROFILE\.claude\skills\spm-readiness" -Recurse -Directory | Select-Object FullName
```

Expected: 13 directories listed (collectors/demand through scripts, docs).

- [ ] **Step 5: Commit**

```bash
git -C "$env:USERPROFILE/.claude/skills/spm-readiness" init
git -C "$env:USERPROFILE/.claude/skills/spm-readiness" add SKILL.md scripts/__init__.py
git -C "$env:USERPROFILE/.claude/skills/spm-readiness" commit -m "feat: scaffold spm-readiness skill + SKILL.md"
```

> Note: if git is not available at this path, skip the commit — this skill directory does not need to be a git repo.

---

## Task 2: `status.py` — Status Trichotomy

**Files:**
- Create: `scripts/status.py`
- Test: `scripts/test_status.py`

**Interfaces:**
- Produces:
  - `measured(value, **kwargs) -> dict` — wraps a known value
  - `not_collected(note="") -> dict` — marks data as absent
  - `not_applicable(note="") -> dict` — marks metric as irrelevant
  - `pct(numerator, denominator) -> float | None` — safe percentage

- [ ] **Step 1: Write `scripts/test_status.py`**

```python
# scripts/test_status.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.status import measured, not_collected, not_applicable, pct

def test_measured():
    r = measured(42)
    assert r == {"value": 42, "status": "measured"}

def test_measured_kwargs():
    r = measured(42, note="from sidecar")
    assert r["note"] == "from sidecar"
    assert r["status"] == "measured"

def test_not_collected():
    r = not_collected("table absent")
    assert r["value"] is None
    assert r["status"] == "not_collected"
    assert r["note"] == "table absent"

def test_not_applicable():
    r = not_applicable()
    assert r["status"] == "not_applicable"

def test_pct_normal():
    assert pct(38, 100) == 38.0

def test_pct_zero_denominator():
    assert pct(5, 0) is None

def test_pct_rounding():
    assert pct(1, 3) == 33.3

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("status.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd C:\Users\elton.price\.claude\skills\spm-readiness
python scripts/test_status.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.status'`

- [ ] **Step 3: Write `scripts/status.py`**

```python
# scripts/status.py


def measured(value, **kwargs):
    d = {"value": value, "status": "measured"}
    d.update(kwargs)
    return d


def not_collected(note=""):
    return {"value": None, "status": "not_collected", "note": note}


def not_applicable(note=""):
    return {"value": None, "status": "not_applicable", "note": note}


def pct(numerator, denominator):
    if not denominator:
        return None
    return round(100.0 * numerator / denominator, 1)
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_status.py
```

Expected:
```
  PASS  test_measured
  PASS  test_measured_kwargs
  PASS  test_not_collected
  PASS  test_not_applicable
  PASS  test_pct_normal
  PASS  test_pct_zero_denominator
  PASS  test_pct_rounding
status.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/status.py scripts/test_status.py
git commit -m "feat: add status trichotomy module"
```

---

## Task 3: `icons.py` — SVG Paths

**Files:**
- Create: `scripts/icons.py`

**Interfaces:**
- Produces:
  - `DOMAIN_ICON: str` — SVG path for the SPM domain (briefcase/portfolio icon)
  - `MODULE_ICONS: dict[str, str]` — SVG paths keyed by module slug
  - `icon_svg(path, size=20, color="#A100FF") -> str` — wraps a path in a `<svg>` tag

- [ ] **Step 1: Write `scripts/icons.py`**

Tabler icon paths (viewBox 0 0 24 24, stroke-based):

```python
# scripts/icons.py
# Tabler icon SVG path data (https://tabler-icons.io, MIT license)
# All icons use viewBox="0 0 24 24", stroke="currentColor", fill="none"

# Briefcase — represents SPM domain
DOMAIN_ICON = (
    "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z "
    "M8 5V3h8v2"
)

# Chart bar — demand
_DEMAND = "M3 12h4v8H3zm7-5h4v13h-4zm7-3h4v16h-4z"

# Folder — projects/PPM
_PPM = (
    "M4 4h6l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2"
)

# Users — resource management
_RESOURCE = (
    "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 "
    "M9 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8 "
    "M23 21v-2a4 4 0 0 0-3-3.87 "
    "M16 3.13a4 4 0 0 1 0 7.75"
)

# Currency dollar — financial
_FINANCIAL = (
    "M12 1v22 "
    "M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"
)

# Rocket — agile
_AGILE = (
    "M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 "
    "2.18 0 0 0-2.91-.09z "
    "M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11 "
    "A22.35 22.35 0 0 1 12 15z "
    "M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0 "
    "M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"
)

# Layout — APM
_APM = (
    "M4 4h6v6H4z "
    "M14 4h6v6h-6z "
    "M4 14h6v6H4z "
    "M17 17m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0"
)

# Bulb — innovation
_INNOVATION = (
    "M9 18h6 "
    "M10 22h4 "
    "M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 "
    "1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"
)

MODULE_ICONS = {
    "demand": _DEMAND,
    "ppm": _PPM,
    "resource": _RESOURCE,
    "financial": _FINANCIAL,
    "agile": _AGILE,
    "apm": _APM,
    "innovation": _INNOVATION,
}


def icon_svg(path, size=20, color="#A100FF"):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="{path}"/></svg>'
    )
```

- [ ] **Step 2: Smoke-test icons**

```bash
python -c "
from scripts.icons import icon_svg, DOMAIN_ICON, MODULE_ICONS
svg = icon_svg(DOMAIN_ICON)
assert svg.startswith('<svg')
assert len(MODULE_ICONS) == 7
print('icons.py OK — 7 module icons, domain icon, icon_svg() works')
"
```

Expected: `icons.py OK — 7 module icons, domain icon, icon_svg() works`

- [ ] **Step 3: Commit**

```bash
git add scripts/icons.py
git commit -m "feat: add icons module with SPM domain + module SVG paths"
```

---

## Task 4: `theme.py` — Branded Header/Footer/Badges

**Files:**
- Create: `scripts/theme.py`
- Test: `scripts/test_theme.py`

**Interfaces:**
- Produces:
  - `render_header(title, badge="SPM Readiness · AS-IS", client="", date="") -> str` — HTML div for profile top
  - `render_footer(date="") -> str` — HTML div for profile bottom
  - `section_badge(label, icon_path, color="#A100FF") -> str` — inline HTML badge for profile sections
  - `RAG_COLORS: dict[str, str]` — `{"green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444", "not_collected": "#9ca3af"}`

- [ ] **Step 1: Write `scripts/test_theme.py`**

```python
# scripts/test_theme.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.theme import render_header, render_footer, section_badge, RAG_COLORS

def test_header_contains_title():
    h = render_header("SPM Readiness", client="Acme Corp", date="2026-08-04")
    assert "SPM Readiness" in h
    assert "Acme Corp" in h
    assert "2026-08-04" in h

def test_header_has_badge():
    h = render_header("X", badge="SPM Readiness · AS-IS")
    assert "SPM Readiness · AS-IS" in h

def test_footer_contains_sage():
    f = render_footer(date="2026-08-04")
    assert "SAGE" in f
    assert "2026-08-04" in f

def test_section_badge_contains_label():
    b = section_badge("Demand Management", "M3 12h4")
    assert "Demand Management" in b

def test_rag_colors_keys():
    assert set(RAG_COLORS.keys()) == {"green", "amber", "red", "not_collected"}

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("theme.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_theme.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.theme'`

- [ ] **Step 3: Write `scripts/theme.py`**

```python
# scripts/theme.py
from datetime import date as _date

PURPLE = "#A100FF"
LIGHT_PURPLE = "#F9F5FF"
BORDER_PURPLE = "#E9D5FF"

RAG_COLORS = {
    "green": "#22c55e",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "not_collected": "#9ca3af",
}

RAG_BG = {
    "green": "#f0fdf4",
    "amber": "#fffbeb",
    "red": "#fef2f2",
    "not_collected": "#f9fafb",
}


def render_header(title, badge="SPM Readiness · AS-IS", client="", date=""):
    date_str = date or _date.today().isoformat()
    client_str = f" &nbsp;·&nbsp; {client}" if client else ""
    return (
        f'<div style="border-left:6px solid {PURPLE};background:{LIGHT_PURPLE};'
        f'padding:16px 20px;margin-bottom:24px;border-radius:4px;">\n'
        f'<div style="display:flex;align-items:center;gap:12px;">\n'
        f'<div style="flex:1;">\n'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:2px;'
        f'color:{PURPLE};text-transform:uppercase;margin-bottom:4px;">{badge}</div>\n'
        f'<div style="font-size:22px;font-weight:800;color:#1a1a1a;">{title}</div>\n'
        f'<div style="font-size:12px;color:#666;margin-top:4px;">'
        f'{date_str}{client_str} &nbsp;·&nbsp; Accenture SAGE</div>\n'
        f'</div>\n</div>\n</div>\n'
    )


def render_footer(date=""):
    date_str = date or _date.today().isoformat()
    return (
        f'\n<div style="border-top:3px solid {PURPLE};margin-top:40px;'
        f'padding-top:12px;font-size:11px;color:#999;text-align:center;">\n'
        f'SAGE · SPM Readiness Assessment · AS-IS Profile · {date_str} · Accenture\n'
        f'</div>\n'
    )


def section_badge(label, icon_path="", color=PURPLE):
    icon_html = ""
    if icon_path:
        icon_html = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" '
            f'viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'style="vertical-align:middle;margin-right:6px;">'
            f'<path d="{icon_path}"/></svg>'
        )
    return (
        f'<div style="display:inline-flex;align-items:center;'
        f'background:{LIGHT_PURPLE};border:1px solid {BORDER_PURPLE};'
        f'border-radius:4px;padding:4px 10px;margin:8px 0 4px 0;">'
        f'{icon_html}'
        f'<span style="font-size:12px;font-weight:700;color:{color};">{label}</span>'
        f'</div>\n'
    )
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_theme.py
```

Expected:
```
  PASS  test_header_contains_title
  PASS  test_header_has_badge
  PASS  test_footer_contains_sage
  PASS  test_section_badge_contains_label
  PASS  test_rag_colors_keys
theme.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/theme.py scripts/test_theme.py
git commit -m "feat: add theme module with branded header, footer, section badges, RAG colors"
```

---

## Part 1 Complete

All foundation files in place. Verify the full foundation before moving to Part 2:

```bash
python scripts/test_status.py && python scripts/test_theme.py && \
python -c "from scripts.icons import MODULE_ICONS; print(f'icons OK — {len(MODULE_ICONS)} modules')"
```

Expected:
```
status.py tests passed.
theme.py tests passed.
icons OK — 7 modules
```

**Proceed to:** `plan-part2-collectors.md`

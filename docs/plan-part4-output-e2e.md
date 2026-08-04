# SPM Readiness Skill — Implementation Plan Part 4: Output & End-to-End

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement task-by-task.

**Goal:** Build the output renderers (`profile.py`, `html_deck.py`), the orchestrator (`run_analysis.py`), mock data generator (`generate_mock.py`), and validate the full pipeline end-to-end against mock data.

**Architecture:** `run_analysis.py` orchestrates: load → metrics → facts → score → findings → profile → html_deck. `generate_mock.py` creates realistic `.txt` files so the pipeline can be tested without a real ServiceNow instance.

**Tech Stack:** Python 3.8+ standard library only. HTML deck uses inline SVG — no CDN, no external dependencies.

## Global Constraints

- Python 3.8+ standard library only
- No disposition language in any output — Section 11.1 profile is AS-IS facts only
- HTML deck: fully self-contained, no external CSS/JS/font references
- Run all tests from skill root: `python scripts/test_<module>.py`

---

## Task 16: `profile.py` — Markdown Report (Deterministic Sections)

**Files:**
- Create: `scripts/profile.py`
- Create: `scripts/test_profile.py`

**Interfaces:**
- Consumes: `metrics` dict, `scores` dict, `findings` list, `out_dir: str`
- Produces:
  - `write_profile(metrics, scores, findings, out_dir) -> str` — writes and returns path to `as-is-spm-readiness-profile.md`

- [ ] **Step 1: Write `scripts/test_profile.py`**

```python
# scripts/test_profile.py
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _make_inputs():
    from scripts.metrics import compute_metrics
    from scripts.load import load_all
    from scripts.scoring import score_all, enrich_coverage_matrix
    from scripts.findings import generate_findings
    import json, tempfile

    # Write minimal mock data
    mock_buckets = {
        "pm_demand": [
            {"sys_id": "d1", "state": "open", "assigned_to": "u1",
             "project": "p1", "sys_created_on": "2026-01-01 00:00:00", "priority": "2"},
        ],
        "pm_project": [
            {"sys_id": "p1", "state": "in_progress", "program": "pg1",
             "business_owner": "o1", "start_date": "2026-01-01",
             "end_date": "2026-12-31", "actual_end_date": "",
             "sys_created_on": "2026-01-01 00:00:00",
             "sys_updated_on": "2026-07-01 00:00:00"},
        ],
        "_sidecar_spm_adoption": {
            "plugins": {"com.snc.sdlc.ppm_core": True, "com.snc.rm": False,
                        "com.snc.financial_mgmt": False, "com.snc.agile": False,
                        "com.snc.apm": False, "com.snc.innovation_mgmt": False},
            "roles": {"portfolio_manager": 2, "project_manager": 5},
            "spm_workspace_active": False,
            "active_users_90d": {"pm_demand": 4},
        },
        "_sidecar_portfolio_health": {
            "project_completeness_pct": 65, "demand_priority_set_pct": 50,
            "resource_plan_named_pct": None, "projects_stale_90d": 0,
            "projects_stale_90d_pct": 0, "demands_stale_90d": 0, "demands_stale_90d_pct": 0,
        },
    }
    from scripts.metrics import _coverage_matrix
    metrics = compute_metrics(mock_buckets, "test", "/tmp")
    metrics["coverage_matrix"] = _coverage_matrix(metrics["modules"])
    scores = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)
    return metrics, scores, findings

def test_profile_file_created():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        assert os.path.exists(path)

def test_profile_has_required_sections():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        content = open(path, encoding="utf-8").read()
        required = [
            "SPM Readiness",
            "Executive Summary",
            "SPM Readiness Scorecard",
            "Demand Management",
            "Project Portfolio",
            "Leading-Practice Coverage",
            "Candidate Findings",
            "Collector Coverage",
        ]
        for section in required:
            assert section in content, f"Missing section: {section}"

def test_profile_no_disposition_language():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.profile import write_profile
        path = write_profile(metrics, scores, findings, tmp)
        content = open(path, encoding="utf-8").read().lower()
        for word in ["should", "recommend", "migrate", "replace"]:
            assert word not in content, f"Disposition language found: '{word}'"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("profile.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_profile.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.profile'`

- [ ] **Step 3: Write `scripts/profile.py`**

```python
# scripts/profile.py
import os
from scripts.theme import render_header, render_footer, section_badge, RAG_COLORS
from scripts.icons import MODULE_ICONS, DOMAIN_ICON
from scripts.scoring import overall_score as _overall_score

_MODULE_LABELS = {
    "demand":     "Demand Management",
    "ppm":        "Project Portfolio Management",
    "resource":   "Resource Management",
    "financial":  "Financial Management",
    "agile":      "Agile Development",
    "apm":        "Application Portfolio Management",
    "innovation": "Innovation Management",
}

_DIMS = ["activation", "data_volume", "data_completeness", "process_adoption", "integration"]
_DIM_LABELS = {
    "activation":        "Activation",
    "data_volume":       "Data Volume",
    "data_completeness": "Completeness",
    "process_adoption":  "Process Adoption",
    "integration":       "Integration",
}


def write_profile(metrics, scores, findings, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    ctx     = metrics.get("_context", {})
    client  = ctx.get("client", "")
    date    = ctx.get("generated_on", "")
    mod_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall    = _overall_score(mod_scores)

    lines = []
    lines.append(render_header(
        f"AS-IS SPM Readiness Profile",
        badge="SPM Readiness · AS-IS",
        client=client.upper() if client else "",
        date=date,
    ))
    lines.append(_how_generated())
    lines.append(_executive_summary(metrics, scores, overall))
    lines.append(_scorecard_table(scores))
    lines.append("---\n")
    for mod_key, mod_label in _MODULE_LABELS.items():
        lines.append(_module_section(mod_key, mod_label, metrics, scores))
    lines.append(_cross_module_integration(metrics))
    lines.append(_governance_section(metrics))
    lines.append(_data_quality_section(metrics))
    lines.append(_coverage_matrix_section(metrics))
    lines.append(_key_observations_placeholder())
    lines.append(_findings_table(findings))
    lines.append(render_footer(date=date))
    lines.append(_appendix_collector_coverage(metrics))

    path = os.path.join(out_dir, "as-is-spm-readiness-profile.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def _how_generated():
    return (
        "\n## How This Report Was Generated\n\n"
        "**Stage 1 — Deterministic (Python):** All metrics, counts, and percentages are "
        "computed directly from export files. No AI involvement in this stage.\n\n"
        "**Stage 2 — AI Overlay (Claude):** Key Observations, scoring rationale, and "
        "finding significance statements are authored by Claude based on the metrics "
        "above. All `[M]` bullets are sourced from Stage 1. `[I]` bullets are AI-authored "
        "and contain no numbers.\n\n---\n"
    )


def _executive_summary(metrics, scores, overall):
    mods = metrics.get("modules", {})
    demand_total = mods.get("demand", {}).get("total", 0)
    ppm_total    = mods.get("ppm", {}).get("total", 0)
    best_mod  = max((k for k, v in scores.items() if v.get("module_score") is not None),
                    key=lambda k: scores[k]["module_score"], default="—")
    worst_mod = min((k for k, v in scores.items() if v.get("module_score") is not None),
                    key=lambda k: scores[k]["module_score"], default="—")
    best_score  = scores.get(best_mod, {}).get("module_score")
    worst_score = scores.get(worst_mod, {}).get("module_score")

    overall_str = f"{overall}%" if overall is not None else "not_collected"
    return (
        f"\n## Executive Summary\n\n"
        f"[M] The SPM instance contains {demand_total} demand records and "
        f"{ppm_total} project records across the assessed modules. "
        f"The overall SPM readiness score is **{overall_str}**.\n\n"
        f"[M] Strongest module: **{_MODULE_LABELS.get(best_mod, best_mod)}** "
        f"({best_score}%). "
        f"Weakest module: **{_MODULE_LABELS.get(worst_mod, worst_mod)}** "
        f"({worst_score}%).\n\n---\n"
    )


def _scorecard_table(scores):
    header = "| Module | " + " | ".join(_DIM_LABELS[d] for d in _DIMS) + " | Score | RAG |\n"
    sep    = "|---|" + "---|" * len(_DIMS) + "---|---|\n"
    rows   = ""
    for mod_key, mod_label in _MODULE_LABELS.items():
        s = scores.get(mod_key, {})
        cells = ""
        for dim in _DIMS:
            v = s.get(dim)
            cells += f" {v}% |" if v is not None else " — |"
        ms  = s.get("module_score")
        r   = s.get("rag", "not_collected")
        col = RAG_COLORS.get(r, "#9ca3af")
        badge = f'<span style="background:{col};color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;">{r.upper()}</span>'
        rows += f"| {mod_label} |{cells} {ms}% | {badge} |\n"
    return f"\n## SPM Readiness Scorecard\n\n{header}{sep}{rows}\n---\n"


def _module_section(mod_key, mod_label, metrics, scores):
    mod  = metrics.get("modules", {}).get(mod_key, {})
    s    = scores.get(mod_key, {})
    icon = MODULE_ICONS.get(mod_key, "")
    badge = section_badge(mod_label, icon)

    lines = [f"\n## {mod_label}\n", badge, "\n"]

    # Metrics table
    lines.append("| Metric | Value | Basis |\n|---|---|---|\n")
    for metric, val in mod.items():
        if metric in ("footprint_status", "by_state", "stories_per_team_dist",
                      "cost_plan_by_type", "plugin_active"):
            continue
        if isinstance(val, dict):
            continue
        basis = "measured" if val is not None else "not_collected"
        display = f"{val}%" if isinstance(val, float) and "pct" in metric else str(val) if val is not None else "—"
        lines.append(f"| {metric.replace('_', ' ')} | {display} | {basis} |\n")

    # Plugin status
    plugin = mod.get("plugin_active")
    lines.append(f"| plugin active | {'Yes' if plugin else 'No' if plugin is False else '—'} | "
                 f"{'sidecar' if plugin is not None else 'not_collected'} |\n")

    lines.append("\n**Key Observations** *(AI overlay — Stage 2)*\n\n")
    lines.append("> *Three-beat observations to be added by Claude in the AI overlay step.*\n\n")
    return "".join(lines)


def _cross_module_integration(metrics):
    mods = metrics.get("modules", {})
    demand  = mods.get("demand", {})
    resource = mods.get("resource", {})
    financial = mods.get("financial", {})
    apm = mods.get("apm", {})

    rows = [
        ("Demand → Project", demand.get("linked_to_project_pct")),
        ("Project → Resource Plan", resource.get("linked_to_project_pct")),
        ("Project → Financial Record", financial.get("projects_with_financials_pct")),
        ("APM → CMDB Service", apm.get("with_cmdb_link_pct")),
    ]
    table = "| Integration Link | Coverage % |\n|---|---|\n"
    for label, val in rows:
        display = f"{val}%" if val is not None else "not_collected"
        table += f"| {label} | {display} |\n"

    return f"\n## Cross-Module Integration Analysis\n\n{table}\n---\n"


def _governance_section(metrics):
    gov = metrics.get("governance", {})
    ts  = gov.get("timesheets", {})
    app = gov.get("approvals", {})
    sr  = gov.get("status_reports", {})
    sm  = gov.get("scoring_models", {})

    table = "| Signal | Value | Collected |\n|---|---|---|\n"
    rows = [
        ("Active timesheet periods",         ts.get("active_periods"),   ts.get("collected")),
        ("Timesheet entries total",           ts.get("total_entries"),    ts.get("collected")),
        ("Demand records with approvals",     app.get("demand_records_with_approvals"), app.get("collected")),
        ("Project records with approvals",    app.get("project_records_with_approvals"), app.get("collected")),
        ("Total project status reports",      sr.get("total"),            sr.get("collected")),
        ("Portfolio scoring criteria",        sm.get("criteria_count"),   sm.get("collected")),
        ("Records with portfolio score",      sm.get("scored_records"),   sm.get("collected")),
    ]
    for label, val, collected in rows:
        display = str(val) if val is not None else "—"
        col_str = "Yes" if collected else "No"
        table += f"| {label} | {display} | {col_str} |\n"

    return f"\n## Governance & Process Adoption\n\n{table}\n---\n"


def _data_quality_section(metrics):
    dq = metrics.get("data_quality", {})
    lines = ["\n## Data Quality Flags\n\n"]
    lines.append("> These counts are informational — they are not deducted from readiness scores.\n\n")
    lines.append("| Indicator | Count | % of Total |\n|---|---|---|\n")
    rows = [
        ("Projects with no update in 90+ days",
         dq.get("projects_stale_90d"), dq.get("projects_stale_90d_pct")),
        ("Demands with no update in 90+ days",
         dq.get("demands_stale_90d"), dq.get("demands_stale_90d_pct")),
    ]
    for label, count, pct in rows:
        c = str(count) if count is not None else "—"
        p = f"{pct}%" if pct is not None else "—"
        lines.append(f"| {label} | {c} | {p} |\n")
    lines.append("\n---\n")
    return "".join(lines)


def _coverage_matrix_section(metrics):
    matrix = metrics.get("coverage_matrix", [])
    if not matrix:
        return "\n## Leading-Practice Coverage Matrix\n\n*Coverage matrix not available.*\n\n---\n"

    table = "| Module | Dimension | Status | Value | RAG |\n|---|---|---|---|---|\n"
    for row in matrix:
        r = row.get("rag", "not_collected")
        col = RAG_COLORS.get(r, "#9ca3af")
        rag_badge = (f'<span style="background:{col};color:#fff;padding:2px 4px;'
                     f'border-radius:3px;font-size:10px;">{r.upper()}</span>')
        table += (f"| {row.get('module_label', row.get('module', ''))} "
                  f"| {row.get('dimension', '')} "
                  f"| {row.get('status', '')} "
                  f"| {row.get('value_token') or '—'} "
                  f"| {rag_badge} |\n")

    return f"\n## Leading-Practice Coverage Matrix\n\n{table}\n---\n"


def _key_observations_placeholder():
    return (
        "\n## Key Observations\n\n"
        "> *Three-beat Key Observations to be authored by Claude in the AI overlay step.*\n"
        "> Format: `[M]` fact clause (numbers from metrics.json) · "
        "`[I]` consequence · `[I]` open question.\n\n---\n"
    )


def _findings_table(findings):
    if not findings:
        return "\n## Candidate Findings for FDE Review\n\n*No findings generated.*\n\n---\n"
    table = "| ID | Module | Dimension | RAG | Observation | Significance |\n|---|---|---|---|---|---|\n"
    for f in findings:
        r   = f.get("rag", "")
        col = RAG_COLORS.get(r, "#9ca3af")
        badge = (f'<span style="background:{col};color:#fff;padding:1px 5px;'
                 f'border-radius:3px;font-size:10px;">{r.upper()}</span>')
        table += (f"| {f.get('id')} | {f.get('module_label', f.get('module'))} "
                  f"| {f.get('dimension')} | {badge} "
                  f"| {f.get('observation')} | {f.get('significance')} |\n")
    return f"\n## Candidate Findings for FDE Review\n\n{table}\n---\n"


def _appendix_collector_coverage(metrics):
    ctx  = metrics.get("_context", {})
    mods = metrics.get("modules", {})
    lines = ["\n## Appendix A — Collector Coverage\n\n"]
    lines.append("| Table | Domain | Status |\n|---|---|---|\n")
    table_map = [
        ("pm_demand",              "demand",     mods.get("demand", {}).get("total", 0) > 0),
        ("pm_demand_category",     "demand",     True),
        ("pm_project",             "ppm",        mods.get("ppm", {}).get("total", 0) > 0),
        ("pm_project_task",        "ppm",        True),
        ("pm_program",             "ppm",        True),
        ("pm_resource_plan",       "resource",   mods.get("resource", {}).get("total", 0) > 0),
        ("pm_resource_allocation", "resource",   True),
        ("pm_project_financials",  "financial",  True),
        ("pm_cost_plan",           "financial",  True),
        ("pm_budget_plan",         "financial",  True),
        ("rm_story",               "agile",      mods.get("agile", {}).get("total_stories", 0) > 0),
        ("rm_sprint",              "agile",      True),
        ("rm_team",                "agile",      True),
        ("apm_appl_now",           "apm",        mods.get("apm", {}).get("total", 0) > 0),
        ("apm_appl_lifecycle",     "apm",        True),
        ("innovation_idea",        "innovation", mods.get("innovation", {}).get("total", 0) > 0),
        ("innovation_challenge",   "innovation", True),
        ("timesheet_period",       "governance", True),
        ("timesheet_entry",        "governance", True),
        ("pm_project_status",      "governance", True),
        ("sysapproval_approver",   "governance", True),
        ("pm_scoring_criterion",   "scoring",    True),
        ("pm_portfolio_score",     "scoring",    True),
        ("pa_scorecard",           "pa",         True),
    ]
    for table, domain, present in table_map:
        status = "collected" if present else "not_collected"
        lines.append(f"| `{table}` | {domain} | {status} |\n")
    return "".join(lines)
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_profile.py
```

Expected:
```
  PASS  test_profile_file_created
  PASS  test_profile_has_required_sections
  PASS  test_profile_no_disposition_language
profile.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/profile.py scripts/test_profile.py
git commit -m "feat: add profile renderer — deterministic AS-IS markdown report"
```

---

## Task 17: `html_deck.py` — Leadership HTML Deck

**Files:**
- Create: `scripts/html_deck.py`
- Create: `scripts/test_html_deck.py`

**Interfaces:**
- Consumes: `metrics.json` path (CLI) or `metrics` dict + `scores` dict + `findings` list (programmatic)
- Produces:
  - `render_deck(metrics, scores, findings) -> str` — full self-contained HTML string
  - `write_deck(metrics, scores, findings, out_dir) -> str` — writes file, returns path
  - CLI: `python -m scripts.html_deck --metrics <path> --out <path>`

- [ ] **Step 1: Write `scripts/test_html_deck.py`**

```python
# scripts/test_html_deck.py
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _make_inputs():
    from scripts.metrics import compute_metrics
    from scripts.metrics import _coverage_matrix
    from scripts.scoring import score_all, enrich_coverage_matrix
    from scripts.findings import generate_findings

    buckets = {
        "pm_demand": [
            {"sys_id": "d1", "state": "open", "assigned_to": "u1",
             "project": "p1", "sys_created_on": "2026-01-01 00:00:00", "priority": "2"},
        ],
        "pm_project": [
            {"sys_id": "p1", "state": "in_progress", "program": "pg1",
             "business_owner": "o1", "start_date": "2026-01-01",
             "end_date": "2026-12-31", "actual_end_date": "",
             "sys_created_on": "2026-01-01 00:00:00",
             "sys_updated_on": "2026-07-01 00:00:00"},
        ],
        "_sidecar_spm_adoption": {
            "plugins": {"com.snc.sdlc.ppm_core": True, "com.snc.rm": False,
                        "com.snc.financial_mgmt": False, "com.snc.agile": False,
                        "com.snc.apm": False, "com.snc.innovation_mgmt": False},
            "roles": {"portfolio_manager": 2, "project_manager": 5},
            "spm_workspace_active": False,
            "active_users_90d": {"pm_demand": 4},
        },
        "_sidecar_portfolio_health": {
            "project_completeness_pct": 65, "demand_priority_set_pct": 50,
            "resource_plan_named_pct": None, "projects_stale_90d": 0,
            "projects_stale_90d_pct": 0, "demands_stale_90d": 0, "demands_stale_90d_pct": 0,
        },
    }
    metrics = compute_metrics(buckets, "test", "/tmp")
    metrics["coverage_matrix"] = _coverage_matrix(metrics["modules"])
    scores = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)
    return metrics, scores, findings

def test_deck_file_created():
    metrics, scores, findings = _make_inputs()
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.html_deck import write_deck
        path = write_deck(metrics, scores, findings, tmp)
        assert os.path.exists(path)

def test_deck_is_self_contained():
    metrics, scores, findings = _make_inputs()
    from scripts.html_deck import render_deck
    html = render_deck(metrics, scores, findings)
    assert "http://" not in html, "External HTTP reference found"
    assert "https://" not in html, "External HTTPS reference found"
    assert "<html" in html.lower()

def test_deck_has_6_slides():
    metrics, scores, findings = _make_inputs()
    from scripts.html_deck import render_deck
    html = render_deck(metrics, scores, findings)
    # Each slide has a data-slide attribute
    assert html.count('class="slide"') >= 6, "Expected at least 6 slides"

def test_deck_has_radar_svg():
    metrics, scores, findings = _make_inputs()
    from scripts.html_deck import render_deck
    html = render_deck(metrics, scores, findings)
    assert "<svg" in html
    assert "polygon" in html  # radar polygon

def test_deck_has_for_discussion_slide():
    metrics, scores, findings = _make_inputs()
    from scripts.html_deck import render_deck
    html = render_deck(metrics, scores, findings)
    assert "For Discussion" in html

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("html_deck.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_html_deck.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.html_deck'`

- [ ] **Step 3: Write `scripts/html_deck.py`**

```python
# scripts/html_deck.py
import argparse
import json
import math
import os

from scripts.scoring import overall_score as _overall_score
from scripts.theme import RAG_COLORS

_MODULE_LABELS = {
    "demand":     "Demand",
    "ppm":        "PPM",
    "resource":   "Resource",
    "financial":  "Financial",
    "agile":      "Agile",
    "apm":        "APM",
    "innovation": "Innovation",
}

_DIMS = ["activation", "data_volume", "data_completeness", "process_adoption", "integration"]
_DIM_SHORT = {
    "activation":        "Activation",
    "data_volume":       "Data Vol.",
    "data_completeness": "Completeness",
    "process_adoption":  "Adoption",
    "integration":       "Integration",
}

PURPLE = "#A100FF"
_SLIDE_BG = "#ffffff"
_DECK_BG  = "#f4f4f6"


def write_deck(metrics, scores, findings, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    html = render_deck(metrics, scores, findings)
    path = os.path.join(out_dir, "spm-leadership-deck.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def render_deck(metrics, scores, findings):
    ctx     = metrics.get("_context", {})
    client  = ctx.get("client", "Client").upper()
    date    = ctx.get("generated_on", "")
    mod_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall    = _overall_score(mod_scores)

    slides = [
        _slide_cover(client, date, overall),
        _slide_radar(scores, overall),
        _slide_scorecard(scores),
        _slide_governance(metrics),
        _slide_findings(findings),
        _slide_next_steps(),
    ]
    return _page_shell(slides, client, date)


def _page_shell(slides, client, date):
    slide_html = "\n".join(
        f'<div class="slide" id="slide-{i+1}">{s}</div>'
        for i, s in enumerate(slides)
    )
    nav_dots = "".join(
        f'<span class="dot {"active" if i == 0 else ""}" onclick="goTo({i})"></span>'
        for i in range(len(slides))
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPM Readiness — {client}</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
          background: {_DECK_BG}; display:flex; flex-direction:column;
          align-items:center; min-height:100vh; padding:20px; }}
  .deck {{ width:960px; max-width:100%; }}
  .slide {{ background:{_SLIDE_BG}; border-radius:8px; padding:48px 56px;
            box-shadow:0 2px 12px rgba(0,0,0,.08); margin-bottom:20px;
            min-height:540px; display:none; }}
  .slide.visible {{ display:block; }}
  .nav {{ display:flex; justify-content:center; gap:8px; margin:8px 0 20px; }}
  .dot {{ width:10px; height:10px; border-radius:50%;
          background:#d1d5db; cursor:pointer; transition:background .2s; }}
  .dot.active {{ background:{PURPLE}; }}
  .btn {{ border:none; background:{PURPLE}; color:#fff; padding:8px 20px;
          border-radius:4px; cursor:pointer; font-size:13px; }}
  .btn-row {{ display:flex; justify-content:space-between; margin-top:16px; }}
  table {{ border-collapse:collapse; width:100%; font-size:13px; }}
  th {{ background:#f9f5ff; color:{PURPLE}; text-align:left; padding:8px 10px;
        border-bottom:2px solid {PURPLE}; font-size:12px; }}
  td {{ padding:7px 10px; border-bottom:1px solid #f0e8ff; vertical-align:middle; }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:3px;
            font-size:11px; font-weight:700; color:#fff; }}
  h1 {{ font-size:28px; font-weight:800; color:#1a1a1a; }}
  h2 {{ font-size:20px; font-weight:700; color:{PURPLE}; margin-bottom:16px; }}
  h3 {{ font-size:15px; font-weight:600; color:#333; margin-bottom:8px; }}
  .score-big {{ font-size:72px; font-weight:900; line-height:1; }}
  .label {{ font-size:11px; text-transform:uppercase; letter-spacing:1.5px;
            color:#999; margin-bottom:4px; }}
  .purple {{ color:{PURPLE}; }}
</style>
</head>
<body>
<div class="deck">
{slide_html}
<div class="nav">{nav_dots}</div>
</div>
<script>
var current = 0;
var slides = document.querySelectorAll('.slide');
var dots   = document.querySelectorAll('.dot');
function goTo(n) {{
  slides[current].classList.remove('visible');
  dots[current].classList.remove('active');
  current = (n + slides.length) % slides.length;
  slides[current].classList.add('visible');
  dots[current].classList.add('active');
}}
goTo(0);
document.addEventListener('keydown', function(e) {{
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goTo(current + 1);
  if (e.key === 'ArrowLeft'  || e.key === 'ArrowUp')   goTo(current - 1);
}});
</script>
</body>
</html>"""


def _slide_cover(client, date, overall):
    score_str = f"{overall}%" if overall is not None else "—"
    rag_color = RAG_COLORS.get(
        "green" if (overall or 0) >= 70 else "amber" if (overall or 0) >= 40 else "red",
        "#9ca3af"
    )
    return f"""
<div class="label">Accenture SAGE · SPM Readiness Assessment · AS-IS</div>
<h1 style="margin:12px 0 4px;">{client}</h1>
<div style="font-size:13px;color:#888;margin-bottom:40px;">{date}</div>
<div class="label">Overall SPM Readiness Score</div>
<div class="score-big" style="color:{rag_color};">{score_str}</div>
<div style="margin-top:24px;font-size:13px;color:#666;">
  Score is a weighted average of 7 SPM modules × 5 readiness dimensions.<br>
  Green ≥70% &nbsp;·&nbsp; Amber 40–69% &nbsp;·&nbsp; Red &lt;40%
</div>
<div class="btn-row">
  <span></span>
  <button class="btn" onclick="goTo(1)">Next →</button>
</div>"""


def _slide_radar(scores, overall):
    labels = list(_MODULE_LABELS.values())
    vals   = [scores.get(k, {}).get("module_score") or 0
              for k in _MODULE_LABELS.keys()]
    colors = [RAG_COLORS.get(scores.get(k, {}).get("rag", "not_collected"), "#9ca3af")
              for k in _MODULE_LABELS.keys()]
    svg = _radar_svg(labels, vals, colors)
    overall_str = f"{overall}%" if overall is not None else "—"
    return f"""
<h2>Readiness at a Glance</h2>
<div style="display:flex;align-items:center;gap:40px;">
  <div>{svg}</div>
  <div>
    <div class="label">Overall Score</div>
    <div style="font-size:48px;font-weight:900;color:{PURPLE};">{overall_str}</div>
    <div style="margin-top:20px;font-size:13px;color:#555;">
      {''.join(f'<div style="margin:4px 0;"><span class="badge" style="background:{colors[i]};">{labels[i]}</span> &nbsp;{vals[i]}%</div>' for i in range(len(labels)))}
    </div>
  </div>
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(0)">← Back</button>
  <button class="btn" onclick="goTo(2)">Next →</button>
</div>"""


def _radar_svg(labels, scores, colors, size=340):
    n  = len(labels)
    cx = cy = size / 2
    r  = size / 2 - 70
    angles = [2 * math.pi * i / n - math.pi / 2 for i in range(n)]

    # Grid
    grid = ""
    for pct in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(
            f"{cx + pct*r*math.cos(a):.1f},{cy + pct*r*math.sin(a):.1f}"
            for a in angles
        )
        grid += f'<polygon points="{pts}" fill="none" stroke="#e5e7eb" stroke-width="1"/>'

    # Axes
    axes = "".join(
        f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx+r*math.cos(a):.1f}" y2="{cy+r*math.sin(a):.1f}" stroke="#e5e7eb" stroke-width="1"/>'
        for a in angles
    )

    # Data polygon
    pts = " ".join(
        f"{cx + (scores[i]/100)*r*math.cos(angles[i]):.1f},{cy + (scores[i]/100)*r*math.sin(angles[i]):.1f}"
        for i in range(n)
    )
    poly = f'<polygon points="{pts}" fill="rgba(161,0,255,0.15)" stroke="{PURPLE}" stroke-width="2"/>'

    # Labels
    lbls = ""
    for i, (lbl, score, col) in enumerate(zip(labels, scores, colors)):
        a  = angles[i]
        lx = cx + (r + 42) * math.cos(a)
        ly = cy + (r + 42) * math.sin(a)
        lbls += (
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="11" font-family="sans-serif" fill="#333">{lbl}</text>'
            f'<text x="{lx:.1f}" y="{ly+14:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="10" font-weight="bold" '
            f'font-family="sans-serif" fill="{col}">{score}%</text>'
        )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'{grid}{axes}{poly}{lbls}</svg>'
    )


def _slide_scorecard(scores):
    header = "<tr><th>Module</th>" + "".join(f"<th>{_DIM_SHORT[d]}</th>" for d in _DIMS) + "<th>Score</th><th>RAG</th></tr>"
    rows = ""
    for mod_key, mod_label in _MODULE_LABELS.items():
        s = scores.get(mod_key, {})
        cells = ""
        for dim in _DIMS:
            v = s.get(dim)
            if v is None:
                cells += '<td style="color:#ccc;">—</td>'
            else:
                r   = "green" if v >= 70 else "amber" if v >= 40 else "red"
                bg  = RAG_COLORS[r]
                cells += f'<td><span class="badge" style="background:{bg};">{v}%</span></td>'
        ms = s.get("module_score")
        mr = s.get("rag", "not_collected")
        mc = RAG_COLORS.get(mr, "#9ca3af")
        ms_str = f"{ms}%" if ms is not None else "—"
        rows += f"<tr><td><strong>{mod_label}</strong></td>{cells}<td><strong>{ms_str}</strong></td><td><span class=\"badge\" style=\"background:{mc};\">{mr.upper()}</span></td></tr>"

    return f"""
<h2>Module Readiness Scorecard</h2>
<table><thead>{header}</thead><tbody>{rows}</tbody></table>
<div style="margin-top:12px;font-size:11px;color:#888;">
  Green ≥70% &nbsp;·&nbsp; Amber 40–69% &nbsp;·&nbsp; Red &lt;40% &nbsp;·&nbsp; — = not collected
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(1)">← Back</button>
  <button class="btn" onclick="goTo(3)">Next →</button>
</div>"""


def _slide_governance(metrics):
    gov = metrics.get("governance", {})
    ts  = gov.get("timesheets", {})
    app = gov.get("approvals", {})
    sr  = gov.get("status_reports", {})
    sm  = gov.get("scoring_models", {})

    rows = [
        ("Active Timesheet Periods",      ts.get("active_periods"),   ts.get("collected")),
        ("Timesheet Entries (total)",      ts.get("total_entries"),    ts.get("collected")),
        ("Demands with Approvals",         app.get("demand_records_with_approvals"), app.get("collected")),
        ("Projects with Approvals",        app.get("project_records_with_approvals"), app.get("collected")),
        ("Project Status Reports (total)", sr.get("total"),            sr.get("collected")),
        ("Portfolio Scoring Criteria",     sm.get("criteria_count"),   sm.get("collected")),
        ("Records with Portfolio Score",   sm.get("scored_records"),   sm.get("collected")),
    ]
    rows_html = ""
    for label, val, collected in rows:
        display = str(val) if val is not None else "—"
        status  = f'<span class="badge" style="background:#22c55e;">Collected</span>' \
                  if collected else \
                  f'<span class="badge" style="background:#9ca3af;">Not collected</span>'
        rows_html += f"<tr><td>{label}</td><td><strong>{display}</strong></td><td>{status}</td></tr>"

    return f"""
<h2>Governance & Process Adoption</h2>
<table>
  <thead><tr><th>Signal</th><th>Value</th><th>Status</th></tr></thead>
  <tbody>{rows_html}</tbody>
</table>
<div class="btn-row">
  <button class="btn" onclick="goTo(2)">← Back</button>
  <button class="btn" onclick="goTo(4)">Next →</button>
</div>"""


def _slide_findings(findings):
    top5 = findings[:5]
    if not top5:
        body = "<p style='color:#888;'>No significant findings generated from the available data.</p>"
    else:
        rows = ""
        for f in top5:
            r   = f.get("rag", "")
            col = RAG_COLORS.get(r, "#9ca3af")
            rows += (
                f'<tr>'
                f'<td><span class="badge" style="background:{col};">{f.get("id")}</span></td>'
                f'<td>{f.get("module_label", f.get("module", ""))}</td>'
                f'<td>{f.get("observation", "")}</td>'
                f'</tr>'
            )
        body = f'<table><thead><tr><th>ID</th><th>Module</th><th>Observation</th></tr></thead><tbody>{rows}</tbody></table>'

    return f"""
<h2>Top Findings</h2>
{body}
<div style="margin-top:12px;font-size:11px;color:#888;">
  Showing top {len(top5)} findings. Full findings list in the markdown profile.
</div>
<div class="btn-row">
  <button class="btn" onclick="goTo(3)">← Back</button>
  <button class="btn" onclick="goTo(5)">Next →</button>
</div>"""


def _slide_next_steps():
    return f"""
<h2>Recommended Next Steps</h2>
<div style="background:#f9f5ff;border-left:4px solid {PURPLE};padding:16px 20px;border-radius:4px;margin-bottom:24px;">
  <div style="font-size:12px;font-weight:700;color:{PURPLE};text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">For Discussion</div>
  <div style="color:#555;font-size:13px;">This slide is intentionally left as a structured placeholder.<br>
  The consultant completes this section during the FDE conversation with the client.</div>
</div>
<table>
  <thead><tr><th>#</th><th>Initiative</th><th>Module</th><th>Priority</th></tr></thead>
  <tbody>
    <tr><td>1</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
    <tr><td>2</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
    <tr><td>3</td><td><em>[Consultant to complete]</em></td><td>—</td><td>—</td></tr>
  </tbody>
</table>
<div class="btn-row">
  <button class="btn" onclick="goTo(4)">← Back</button>
  <span></span>
</div>"""


def main(argv=None):
    ap = argparse.ArgumentParser(description="Render SPM leadership HTML deck from metrics.json")
    ap.add_argument("--metrics", required=True, help="Path to metrics.json")
    ap.add_argument("--out",     required=True, help="Output directory")
    args = ap.parse_args(argv)

    with open(args.metrics, encoding="utf-8") as f:
        metrics = json.load(f)

    from scripts.scoring import score_all, enrich_coverage_matrix
    from scripts.metrics import _coverage_matrix
    from scripts.findings import generate_findings

    if not metrics.get("coverage_matrix"):
        metrics["coverage_matrix"] = _coverage_matrix(metrics.get("modules", {}))
    scores   = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    findings = generate_findings(metrics, scores)

    path = write_deck(metrics, scores, findings, args.out)
    print(f"Deck written: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_html_deck.py
```

Expected:
```
  PASS  test_deck_file_created
  PASS  test_deck_is_self_contained
  PASS  test_deck_has_6_slides
  PASS  test_deck_has_radar_svg
  PASS  test_deck_has_for_discussion_slide
html_deck.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/html_deck.py scripts/test_html_deck.py
git commit -m "feat: add HTML leadership deck — 6 slides, inline SVG radar, self-contained"
```

---

## Task 18: `generate_mock.py` — Synthetic Mock Data

**Files:**
- Create: `scripts/generate_mock.py`

**Interfaces:**
- Produces:
  - `generate_mock(out_dir: str)` — writes all `.txt` mock input files
  - CLI: `python -m scripts.generate_mock --out spm-inputs/mock`

- [ ] **Step 1: Write `scripts/generate_mock.py`**

```python
# scripts/generate_mock.py
"""Generate synthetic SPM export files for testing."""
import argparse
import json
import os
import random
import string
from datetime import datetime, timedelta

random.seed(42)

_TODAY = datetime.now()
STATES_DEMAND  = ["open", "in_progress", "closed", "cancelled", "approved"]
STATES_PROJECT = ["planning", "in_progress", "closed", "on_hold"]
STATES_STORY   = ["open", "in_progress", "complete", "cancelled"]


def _uid():
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=32))


def _date(days_ago=0):
    return (_TODAY - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")


def _write(out_dir, domain, table, records):
    folder = os.path.join(out_dir, domain)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{table}.txt")
    content = json.dumps(records)
    footer = (f"// SPM collector: table={table} chunk=0 "
              f"rows={len(records)} total={len(records)} status=COMPLETE")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content + "\n" + footer + "\n")


def _write_sidecar(out_dir, name, data):
    folder = os.path.join(out_dir, "sidecars")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{name}.txt")
    content = json.dumps(data)
    footer = f"// SPM sidecar: name={name} status=COMPLETE"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content + "\n" + footer + "\n")


def generate_mock(out_dir):
    # Demand
    demands = [
        {"sys_id": _uid(), "short_description": f"Demand {i}",
         "state": random.choice(STATES_DEMAND),
         "category": random.choice(["IT", "Business", "Security", ""]),
         "assigned_to": "" if i % 6 == 0 else _uid(),
         "project": _uid() if i % 3 != 0 else "",
         "sys_created_on": _date(random.randint(10, 400)),
         "priority": str(random.randint(1, 4)),
         "business_justification": "Justification text",
         "requested_by": _uid()}
        for i in range(1, 141)
    ]
    _write(out_dir, "demand", "pm_demand", demands)
    _write(out_dir, "demand", "pm_demand_category",
           [{"sys_id": _uid(), "name": cat, "active": "true", "parent": ""}
            for cat in ["IT", "Business", "Security"]])

    # PPM
    programs = [{"sys_id": _uid(), "short_description": f"Program {i}",
                 "state": "active", "assigned_to": _uid(),
                 "start_date": "2026-01-01", "end_date": "2026-12-31",
                 "sys_created_on": _date(200)} for i in range(1, 6)]
    prog_ids = [p["sys_id"] for p in programs]
    projects = [
        {"sys_id": _uid(), "short_description": f"Project {i}",
         "state": random.choice(STATES_PROJECT),
         "phase": "execute",
         "program": random.choice(prog_ids) if i % 4 != 0 else "",
         "assigned_to": _uid(),
         "business_owner": "" if i % 8 == 0 else _uid(),
         "start_date": "2026-01-15",
         "end_date": "2026-11-30",
         "actual_start_date": "2026-01-20",
         "actual_end_date": "" if i % 3 != 0 else "2026-12-10",
         "sys_created_on": _date(random.randint(30, 300)),
         "sys_updated_on": _date(random.randint(1, 120)),
         "percent_complete": str(random.randint(0, 100)),
         "priority": str(random.randint(1, 3))}
        for i in range(1, 61)
    ]
    proj_ids = [p["sys_id"] for p in projects]
    tasks = [
        {"sys_id": _uid(), "short_description": f"Task {i}",
         "state": "open", "project": random.choice(proj_ids),
         "assigned_to": _uid(), "start_date": "2026-02-01",
         "end_date": "2026-06-30", "percent_complete": "50",
         "sys_created_on": _date(60)}
        for i in range(1, 121)
    ]
    _write(out_dir, "ppm", "pm_program", programs)
    _write(out_dir, "ppm", "pm_project", projects)
    _write(out_dir, "ppm", "pm_project_task", tasks)

    # Resource
    resource_plans = [
        {"sys_id": _uid(), "project": random.choice(proj_ids) if i % 5 != 0 else "",
         "resource": "" if i % 7 == 0 else _uid(), "role": "Developer",
         "state": "open", "planned_hours": str(random.randint(40, 200)),
         "actual_hours": str(random.randint(10, 150)),
         "available_hours": str(random.randint(160, 240)),
         "start_date": "2026-01-01", "end_date": "2026-06-30",
         "sys_created_on": _date(90)}
        for i in range(1, 41)
    ]
    _write(out_dir, "resource", "pm_resource_plan", resource_plans)
    _write(out_dir, "resource", "pm_resource_allocation",
           [{"sys_id": _uid(), "resource_plan": random.choice([r["sys_id"] for r in resource_plans]),
             "resource": _uid(), "start_date": "2026-01-01", "end_date": "2026-03-31",
             "allocated_hours": str(random.randint(20, 100)),
             "actual_hours": str(random.randint(10, 90)) if random.random() > 0.3 else "",
             "sys_created_on": _date(80)}
            for _ in range(60)])

    # Financial
    fin_proj_ids = random.sample(proj_ids, min(40, len(proj_ids)))
    _write(out_dir, "financial", "pm_project_financials",
           [{"sys_id": _uid(), "project": pid,
             "planned_cost": str(random.randint(10000, 500000)),
             "actual_cost": str(random.randint(5000, 400000)) if random.random() > 0.2 else "",
             "planned_benefit": str(random.randint(20000, 800000)),
             "actual_benefit": "", "currency": "USD", "sys_created_on": _date(120)}
            for pid in fin_proj_ids])
    cost_proj = random.sample(proj_ids, min(35, len(proj_ids)))
    _write(out_dir, "financial", "pm_cost_plan",
           [{"sys_id": _uid(), "project": pid,
             "cost_type": random.choice(["capex", "opex", ""]),
             "planned_cost": str(random.randint(5000, 200000)),
             "actual_cost": str(random.randint(2000, 180000)),
             "state": "approved", "sys_created_on": _date(100)}
            for pid in cost_proj])
    bud_proj = random.sample(proj_ids, min(30, len(proj_ids)))
    _write(out_dir, "financial", "pm_budget_plan",
           [{"sys_id": _uid(), "project": pid,
             "budget_amount": str(random.randint(50000, 1000000)),
             "actual_amount": str(random.randint(10000, 900000)),
             "state": "approved", "fiscal_year": "2026", "sys_created_on": _date(150)}
            for pid in bud_proj])

    # Agile
    teams = [{"sys_id": _uid(), "name": f"Team {i}", "team_type": "scrum",
              "active": "true", "manager": _uid(), "sys_created_on": _date(300)}
             for i in range(1, 9)]
    team_ids = [t["sys_id"] for t in teams]
    sprints = [{"sys_id": _uid(), "short_description": f"Sprint {i}",
                "state": "complete" if i < 16 else "active",
                "team": random.choice(team_ids),
                "start_date": _date(120 - i*14)[:10], "end_date": _date(106 - i*14)[:10],
                "planned_points": str(random.randint(20, 40)),
                "completed_points": str(random.randint(15, 38)),
                "sys_created_on": _date(150)}
               for i in range(1, 22)]
    sprint_ids = [s["sys_id"] for s in sprints]
    stories = [{"sys_id": _uid(), "short_description": f"Story {i}",
                "state": random.choice(STATES_STORY),
                "sprint": "" if i % 8 == 0 else random.choice(sprint_ids),
                "team": "" if i % 12 == 0 else random.choice(team_ids),
                "story_points": str(random.randint(1, 8)) if random.random() > 0.2 else "",
                "assigned_to": _uid(), "sys_created_on": _date(random.randint(5, 200)),
                "sys_updated_on": _date(random.randint(1, 30))}
               for i in range(1, 201)]
    _write(out_dir, "agile", "rm_team", teams)
    _write(out_dir, "agile", "rm_sprint", sprints)
    _write(out_dir, "agile", "rm_story", stories)

    # APM
    apps = [{"sys_id": _uid(), "name": f"Application {i}",
             "lifecycle_stage": random.choice(["growth", "mature", "sunset", ""]) if i % 3 != 0 else "",
             "business_owner": _uid() if i % 4 != 0 else "",
             "cmdb_ci": _uid() if i % 3 != 0 else "",
             "vendor": "Vendor Corp", "install_status": "1",
             "sys_created_on": _date(500)}
            for i in range(1, 46)]
    app_ids = [a["sys_id"] for a in apps]
    _write(out_dir, "apm", "apm_appl_now", apps)
    _write(out_dir, "apm", "apm_appl_lifecycle",
           [{"sys_id": _uid(), "application": random.choice(app_ids),
             "stage": random.choice(["growth", "mature", "sunset"]),
             "target_retirement_date": "", "migration_path": "",
             "sys_created_on": _date(200)}
            for _ in range(28)])

    # Innovation
    challenges = [{"sys_id": _uid(), "short_description": f"Challenge {i}",
                   "state": "open", "assigned_to": _uid(),
                   "start_date": "2026-01-01", "end_date": "2026-06-30",
                   "sys_created_on": _date(120)}
                  for i in range(1, 4)]
    chal_ids = [c["sys_id"] for c in challenges]
    demand_ids_for_ideas = [d["sys_id"] for d in demands[:20]]
    ideas = [{"sys_id": _uid(), "short_description": f"Idea {i}",
              "state": random.choice(["submitted", "under_review", "approved", "rejected"]),
              "category": "Process",
              "assigned_to": _uid() if i % 5 != 0 else "",
              "demand": random.choice(demand_ids_for_ideas) if i % 4 == 0 else "",
              "project": random.choice(proj_ids) if i % 7 == 0 else "",
              "challenge": random.choice(chal_ids) if i % 3 != 0 else "",
              "sys_created_on": _date(random.randint(10, 180)),
              "sys_updated_on": _date(random.randint(1, 90))}
             for i in range(1, 26)]
    _write(out_dir, "innovation", "innovation_challenge", challenges)
    _write(out_dir, "innovation", "innovation_idea", ideas)

    # Governance
    dem_ids_all = [d["sys_id"] for d in demands]
    approvals = [{"sys_id": _uid(),
                  "source_id": random.choice(dem_ids_all),
                  "source_table": "pm_demand",
                  "approver": _uid(),
                  "state": random.choice(["approved", "rejected", "requested"]),
                  "sys_created_on": _date(random.randint(5, 90)),
                  "sys_updated_on": _date(random.randint(1, 30))}
                 for _ in range(53)]
    approvals += [{"sys_id": _uid(),
                   "source_id": random.choice(proj_ids),
                   "source_table": "pm_project",
                   "approver": _uid(),
                   "state": "approved",
                   "sys_created_on": _date(60),
                   "sys_updated_on": _date(30)}
                  for _ in range(22)]
    ts_periods = [{"sys_id": _uid(), "state": "open" if i < 3 else "closed",
                   "start_date": _date(14*i)[:10], "end_date": _date(14*i - 14)[:10],
                   "name": f"Period {i}", "sys_created_on": _date(14*i)}
                  for i in range(1, 7)]
    ts_entries = [{"sys_id": _uid(), "timesheet": random.choice([t["sys_id"] for t in ts_periods]),
                   "task": random.choice(proj_ids),
                   "hours": str(round(random.uniform(1, 8), 1)),
                   "state": "approved", "user": _uid(),
                   "work_date": _date(random.randint(1, 80))[:10],
                   "sys_created_on": _date(random.randint(1, 80))}
                  for _ in range(300)]
    status_reports = [{"sys_id": _uid(), "project": random.choice(proj_ids),
                       "overall_status": random.choice(["green", "amber", "red"]),
                       "schedule_status": "green", "cost_status": "amber",
                       "risk_status": "green",
                       "sys_created_on": _date(random.randint(1, 45)),
                       "created_by": _uid()}
                      for _ in range(55)]
    _write(out_dir, "governance", "sysapproval_approver", approvals)
    _write(out_dir, "governance", "timesheet_period", ts_periods)
    _write(out_dir, "governance", "timesheet_entry", ts_entries)
    _write(out_dir, "governance", "pm_project_status", status_reports)

    # Scoring
    _write(out_dir, "scoring", "pm_scoring_criterion",
           [{"sys_id": _uid(), "name": f"Criterion {i}", "active": "true",
             "weight": str(random.randint(10, 30)), "scoring_model": "default",
             "sys_created_on": _date(200)}
            for i in range(1, 7)])
    _write(out_dir, "scoring", "pm_portfolio_score",
           [{"sys_id": _uid(), "source_id": random.choice(dem_ids_all[:40]),
             "source_table": "pm_demand",
             "score": str(round(random.uniform(20, 95), 1)),
             "scoring_model": "default", "sys_created_on": _date(60)}
            for _ in range(30)])

    # PA
    _write(out_dir, "pa", "pa_scorecard",
           [{"sys_id": _uid(), "name": f"SPM Scorecard {i}",
             "indicator_source": f"pm_project_{_uid()[:6]}",
             "active": "true", "owner": _uid(), "sys_created_on": _date(180)}
            for i in range(1, 4)])

    # Sidecars
    _write_sidecar(out_dir, "_sidecar_spm_adoption", {
        "plugins": {
            "com.snc.sdlc.ppm_core": True, "com.snc.rm": True,
            "com.snc.financial_mgmt": True, "com.snc.agile": True,
            "com.snc.apm": False, "com.snc.innovation_mgmt": False,
        },
        "roles": {
            "portfolio_manager": 4, "project_manager": 12,
            "resource_manager": 3, "financial_analyst": 1, "it_demand_manager": 2,
        },
        "spm_workspace_active": True,
        "active_users_90d": {
            "pm_demand": 18, "pm_project": 24, "pm_resource_plan": 6,
            "rm_story": 15, "apm_appl_now": None,
        },
    })
    _write_sidecar(out_dir, "_sidecar_portfolio_health", {
        "project_completeness_pct": 61,
        "demand_priority_set_pct": 74,
        "resource_plan_named_pct": 83,
        "projects_stale_90d": 7,
        "projects_stale_90d_pct": 12,
        "demands_stale_90d": 11,
        "demands_stale_90d_pct": 8,
    })

    print(f"Mock data written to: {out_dir}")
    print(f"  Demands: 140 | Projects: 60 | Stories: 200 | Apps: 45 | Ideas: 25")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate mock SPM input data")
    ap.add_argument("--out", default="spm-inputs/mock", help="Output directory")
    args = ap.parse_args(argv)
    generate_mock(args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test mock generation**

```bash
python -m scripts.generate_mock --out spm-inputs/mock
```

Expected output:
```
Mock data written to: spm-inputs/mock
  Demands: 140 | Projects: 60 | Stories: 200 | Apps: 45 | Ideas: 25
```

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_mock.py
git commit -m "feat: add mock data generator for all 21 SPM tables + 2 sidecars"
```

---

## Task 19: `run_analysis.py` — Orchestrator

**Files:**
- Create: `scripts/run_analysis.py`

**Interfaces:**
- Produces:
  - `run(input_dir, out_dir)` — full pipeline: load → metrics → facts → score → findings → profile → deck
  - CLI: `python -m scripts.run_analysis --input <dir> --out <dir>`

- [ ] **Step 1: Write `scripts/run_analysis.py`**

```python
# scripts/run_analysis.py
import argparse
import os

_DEFAULT_INPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "spm-inputs", "mock")
_DEFAULT_OUT   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "spm-outputs", "mock")


def run(input_dir, out_dir):
    from scripts.load     import load_all
    from scripts.metrics  import compute_metrics, _coverage_matrix
    from scripts.facts    import write_facts, write_csvs
    from scripts.scoring  import score_all, enrich_coverage_matrix
    from scripts.findings import generate_findings
    from scripts.profile  import write_profile
    from scripts.html_deck import write_deck

    client = os.path.basename(os.path.normpath(out_dir))
    os.makedirs(out_dir, exist_ok=True)
    data_dir = os.path.join(out_dir, "data")

    print(f"[1/7] Loading exports from {input_dir} ...")
    buckets = load_all(input_dir)
    print(f"      {len(buckets)} tables/sidecars loaded.")

    print("[2/7] Computing metrics ...")
    metrics = compute_metrics(buckets, client, input_dir)
    metrics["coverage_matrix"] = _coverage_matrix(metrics["modules"])

    print("[3/7] Writing metrics.json + CSVs ...")
    facts_path = write_facts(metrics, out_dir)
    write_csvs(metrics, data_dir)
    print(f"      metrics.json → {facts_path}")

    print("[4/7] Scoring modules ...")
    scores = score_all(metrics)
    metrics["coverage_matrix"] = enrich_coverage_matrix(metrics, scores)
    write_facts(metrics, out_dir)  # re-write with enriched matrix

    overall_scores = {k: v.get("module_score") for k, v in scores.items()}
    from scripts.scoring import overall_score
    overall = overall_score(overall_scores)
    print(f"      Overall SPM Readiness Score: {overall}%")
    for mod, s in scores.items():
        ms = s.get("module_score")
        r  = s.get("rag", "")
        print(f"        {mod:12s}: {ms}%  [{r}]" if ms is not None else f"        {mod:12s}: not_collected")

    print("[5/7] Generating findings ...")
    findings = generate_findings(metrics, scores)
    print(f"      {len(findings)} findings generated.")

    print("[6/7] Writing markdown profile ...")
    profile_path = write_profile(metrics, scores, findings, out_dir)
    print(f"      Profile → {profile_path}")

    print("[7/7] Rendering HTML leadership deck ...")
    deck_path = write_deck(metrics, scores, findings, out_dir)
    print(f"      Deck → {deck_path}")

    print("\nDone.")
    print(f"  Overall Score : {overall}%")
    if findings:
        worst = min(scores.items(), key=lambda x: x[1].get("module_score") or 101)
        print(f"  Weakest Module: {worst[0]} — {worst[1].get('module_score')}% [{worst[1].get('rag')}]")
        print(f"  Top Finding   : {findings[0]['id']} — {findings[0]['observation']}")
    print(f"\n  Profile : {profile_path}")
    print(f"  Deck    : {deck_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run SPM readiness analysis")
    ap.add_argument("--input", default=_DEFAULT_INPUT, help="Input directory (spm-inputs/<client>)")
    ap.add_argument("--out",   default=_DEFAULT_OUT,   help="Output directory (spm-outputs/<client>)")
    args = ap.parse_args(argv)
    run(args.input, args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/run_analysis.py
git commit -m "feat: add run_analysis orchestrator — full pipeline in one command"
```

---

## Task 20: End-to-End Test

**Goal:** Run the complete pipeline against mock data and verify all outputs exist and are valid.

- [ ] **Step 1: Generate mock data**

```bash
python -m scripts.generate_mock --out spm-inputs/mock
```

Expected: `Mock data written to: spm-inputs/mock`

- [ ] **Step 2: Run full pipeline**

```bash
python -m scripts.run_analysis --input spm-inputs/mock --out spm-outputs/mock
```

Expected: 7 steps print, overall score printed, no exceptions.

- [ ] **Step 3: Verify output files exist**

```bash
python -c "
import os, json
out = 'spm-outputs/mock'
files = [
    'metrics.json',
    'as-is-spm-readiness-profile.md',
    'spm-leadership-deck.html',
    'data/demand_summary.csv',
    'data/project_portfolio.csv',
    'data/resource_utilisation.csv',
    'data/financial_coverage.csv',
    'data/agile_adoption.csv',
    'data/apm_coverage.csv',
    'data/innovation_pipeline.csv',
    'data/readiness_scorecard.csv',
]
for f in files:
    path = os.path.join(out, f)
    assert os.path.exists(path), f'MISSING: {path}'
    print(f'  OK  {f}')

# Validate metrics.json
with open(os.path.join(out, 'metrics.json')) as fh:
    m = json.load(fh)
assert 'modules' in m
assert len(m['modules']) == 7
assert 'coverage_matrix' in m
assert len(m['coverage_matrix']) == 35
print('metrics.json valid — 7 modules, 35 coverage_matrix rows')

# Validate HTML deck is self-contained
html = open(os.path.join(out, 'spm-leadership-deck.html')).read()
assert 'http://' not in html, 'External HTTP reference in deck'
assert 'slide' in html
print('HTML deck valid — self-contained, has slides')
print()
print('All end-to-end checks passed.')
"
```

Expected:
```
  OK  metrics.json
  OK  as-is-spm-readiness-profile.md
  OK  spm-leadership-deck.html
  OK  data/demand_summary.csv
  OK  data/project_portfolio.csv
  OK  data/resource_utilisation.csv
  OK  data/financial_coverage.csv
  OK  data/agile_adoption.csv
  OK  data/apm_coverage.csv
  OK  data/innovation_pipeline.csv
  OK  data/readiness_scorecard.csv
metrics.json valid — 7 modules, 35 coverage_matrix rows
HTML deck valid — self-contained, has slides

All end-to-end checks passed.
```

- [ ] **Step 4: Open deck in browser**

```bash
start spm-outputs/mock/spm-leadership-deck.html
```

Visually verify:
- 6 slides navigable by buttons and arrow keys
- Cover slide shows overall score with RAG colour
- Slide 2 shows radar chart
- Slide 3 shows heat-map table with RAG badges
- Slide 4 shows governance metrics
- Slide 5 shows top findings
- Slide 6 shows "For Discussion" placeholder

- [ ] **Step 5: Run all unit tests one final time**

```bash
python scripts/test_status.py && \
python scripts/test_theme.py && \
python scripts/test_load.py && \
python scripts/test_metrics.py && \
python scripts/test_facts.py && \
python scripts/test_scoring.py && \
python scripts/test_findings.py && \
python scripts/test_profile.py && \
python scripts/test_html_deck.py
```

Expected: all 9 test suites pass.

- [ ] **Step 6: Final commit**

```bash
git add spm-inputs/mock/ spm-outputs/mock/
git commit -m "feat: add mock data + verified end-to-end pipeline output"
```

---

## Plan Complete

All 4 parts implemented and verified. The skill is ready to use:

```bash
# Generate mock data (or drop real client exports into spm-inputs/<client>/)
python -m scripts.generate_mock --out spm-inputs/mock

# Run full analysis
python -m scripts.run_analysis --input spm-inputs/<client> --out spm-outputs/<client>

# Or invoke via Claude Code
/spm-readiness
```

**Outputs:**
- `spm-outputs/<client>/metrics.json` — machine-readable facts
- `spm-outputs/<client>/as-is-spm-readiness-profile.md` — full AS-IS markdown report
- `spm-outputs/<client>/spm-leadership-deck.html` — self-contained leadership presentation
- `spm-outputs/<client>/data/*.csv` — 8 companion CSV files

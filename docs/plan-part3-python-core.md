# SPM Readiness Skill — Implementation Plan Part 3: Python Core

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement task-by-task.

**Goal:** Build the Python data pipeline — file loading, metric computation, serialization, scoring, and findings generation.

**Architecture:** `load.py` → `metrics.py` → `facts.py` + `scoring.py` → `findings.py`. Each module is independently testable. No external dependencies — standard library only.

**Tech Stack:** Python 3.8+, standard library only (`json`, `os`, `re`, `csv`, `datetime`, `math`).

## Global Constraints

- Python 3.8+ standard library only
- Skill root: `C:\Users\elton.price\.claude\skills\spm-readiness\`
- No disposition language in any output
- Every metric `not_collected` when source table is absent
- Run all tests from skill root: `python scripts/test_<module>.py`

---

## Task 11: `load.py` — File Routing

**Files:**
- Create: `scripts/load.py`
- Create: `scripts/test_load.py`

**Interfaces:**
- Produces:
  - `load_all(input_dir: str) -> dict` — returns `{table_name: list[dict], sidecar_name: dict}`
  - Tables keyed by bare filename stem (e.g. `"pm_demand"`)
  - Sidecars keyed by full sidecar name (e.g. `"_sidecar_spm_adoption"`)
  - Chunked files merged in sort order

- [ ] **Step 1: Write `scripts/test_load.py`**

```python
# scripts/test_load.py
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def test_loads_single_table():
    records = [{"sys_id": "abc", "state": "open"}]
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "demand", "pm_demand.txt"),
               json.dumps(records) + "\n// SPM collector: table=pm_demand chunk=0 rows=1 total=1 status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "pm_demand" in buckets
        assert len(buckets["pm_demand"]) == 1
        assert buckets["pm_demand"][0]["state"] == "open"

def test_merges_chunks():
    chunk1 = [{"sys_id": str(i)} for i in range(3)]
    chunk2 = [{"sys_id": str(i)} for i in range(3, 5)]
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "ppm", "pm_project.001.txt"),
               json.dumps(chunk1) + "\n// SPM collector: table=pm_project chunk=0 rows=3 total=5 status=MORE_RECORDS_EXIST\n")
        _write(os.path.join(tmp, "ppm", "pm_project.002.txt"),
               json.dumps(chunk2) + "\n// SPM collector: table=pm_project chunk=1 rows=2 total=5 status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert len(buckets["pm_project"]) == 5

def test_loads_sidecar():
    data = {"plugins": {"com.snc.sdlc.ppm_core": True}, "roles": {}}
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "sidecars", "_sidecar_spm_adoption.txt"),
               json.dumps(data) + "\n// SPM sidecar: name=_sidecar_spm_adoption status=COMPLETE\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "_sidecar_spm_adoption" in buckets
        assert buckets["_sidecar_spm_adoption"]["plugins"]["com.snc.sdlc.ppm_core"] is True

def test_table_not_found_returns_empty():
    with tempfile.TemporaryDirectory() as tmp:
        _write(os.path.join(tmp, "demand", "pm_demand.txt"),
               "[]\n// SPM collector: table=pm_demand chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND\n")
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert buckets.get("pm_demand", []) == []

def test_missing_table_not_in_buckets():
    with tempfile.TemporaryDirectory() as tmp:
        # empty dir
        os.makedirs(os.path.join(tmp, "demand"))
        from scripts.load import load_all
        buckets = load_all(tmp)
        assert "pm_demand" not in buckets

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("load.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_load.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.load'`

- [ ] **Step 3: Write `scripts/load.py`**

```python
# scripts/load.py
import json
import os
import re

_SIDECAR_PREFIX = "_sidecar_"


def load_all(input_dir):
    """Walk input_dir recursively, route .txt files to typed buckets.

    Returns:
        dict: keys are table names or sidecar names, values are list[dict] or dict.
    """
    file_groups = {}  # base_name -> sorted list of paths
    for root, _, fnames in os.walk(input_dir):
        for fname in sorted(fnames):
            if not fname.endswith(".txt"):
                continue
            path = os.path.join(root, fname)
            base = _base_name(fname)
            file_groups.setdefault(base, []).append(path)

    buckets = {}
    for base, paths in file_groups.items():
        paths.sort()  # ensures .001 before .002
        if base.startswith(_SIDECAR_PREFIX):
            data = _parse_sidecar(_read(paths[0]))
            if data:
                buckets[base] = data
        else:
            records = []
            for path in paths:
                records.extend(_parse_records(_read(path)))
            if records:
                buckets[base] = records
    return buckets


def _base_name(fname):
    # Strip chunk suffix: pm_demand.001.txt -> pm_demand
    # Strip plain suffix: pm_demand.txt -> pm_demand
    name = re.sub(r"\.\d{3}\.txt$", "", fname)
    name = re.sub(r"\.txt$", "", name)
    return name


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _strip_footer(text):
    lines = text.strip().splitlines()
    while lines and lines[-1].strip().startswith("//"):
        lines.pop()
    return "\n".join(lines).strip()


def _parse_records(text):
    clean = _strip_footer(text)
    if not clean or clean in ("[]", ""):
        return []
    try:
        data = json.loads(clean)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _parse_sidecar(text):
    clean = _strip_footer(text)
    if not clean or clean in ("{}", ""):
        return {}
    try:
        data = json.loads(clean)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_load.py
```

Expected:
```
  PASS  test_loads_single_table
  PASS  test_merges_chunks
  PASS  test_loads_sidecar
  PASS  test_table_not_found_returns_empty
  PASS  test_missing_table_not_in_buckets
load.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/load.py scripts/test_load.py
git commit -m "feat: add load module with chunk merging and sidecar routing"
```

---

## Task 12: `metrics.py` — Metric Computation

**Files:**
- Create: `scripts/metrics.py`
- Create: `scripts/test_metrics.py`

**Interfaces:**
- Consumes: `load_all()` output dict, `client: str`, `input_dir: str`
- Produces:
  - `compute_metrics(buckets, client, input_dir) -> dict` — full metrics dict matching §10 of spec
  - Top-level keys: `modules`, `governance`, `roles`, `pa_adoption`, `data_quality`, `spm_workspace_active`, `coverage_matrix`, `_context`

- [ ] **Step 1: Write `scripts/test_metrics.py`**

```python
# scripts/test_metrics.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.metrics import compute_metrics

def _minimal_buckets():
    return {
        "pm_demand": [
            {"sys_id": "d1", "state": "open", "assigned_to": "user1",
             "project": "p1", "sys_created_on": "2026-01-01 00:00:00", "priority": "2"},
            {"sys_id": "d2", "state": "closed", "assigned_to": "",
             "project": "", "sys_created_on": "2025-06-01 00:00:00", "priority": ""},
        ],
        "pm_project": [
            {"sys_id": "p1", "state": "in_progress", "program": "pg1",
             "business_owner": "owner1", "start_date": "2026-01-01",
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
            "active_users_90d": {"pm_demand": 4, "pm_project": 6}
        },
        "_sidecar_portfolio_health": {
            "project_completeness_pct": 65,
            "demand_priority_set_pct": 50,
            "resource_plan_named_pct": None,
            "projects_stale_90d": 0,
            "projects_stale_90d_pct": 0,
            "demands_stale_90d": 1,
            "demands_stale_90d_pct": 50,
        },
    }

def test_top_level_keys():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    for key in ["modules", "governance", "roles", "pa_adoption",
                "data_quality", "spm_workspace_active", "coverage_matrix", "_context"]:
        assert key in m, f"Missing top-level key: {key}"

def test_module_keys():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    for mod in ["demand", "ppm", "resource", "financial", "agile", "apm", "innovation"]:
        assert mod in m["modules"], f"Missing module: {mod}"

def test_demand_total():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["modules"]["demand"]["total"] == 2

def test_demand_no_owner_pct():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    # 1 of 2 records has empty assigned_to
    assert m["modules"]["demand"]["no_owner_pct"] == 50.0

def test_ppm_total():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["modules"]["ppm"]["total"] == 1

def test_resource_not_collected_when_absent():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    # pm_resource_plan not in buckets
    assert m["modules"]["resource"]["total"] == 0

def test_context_client():
    m = compute_metrics(_minimal_buckets(), "acme", "/tmp/test")
    assert m["_context"]["client"] == "acme"

def test_coverage_matrix_length():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert len(m["coverage_matrix"]) == 35  # 5 dimensions × 7 modules

def test_roles_populated():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["roles"]["portfolio_manager"] == 2
    assert m["roles"]["project_manager"] == 5

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("metrics.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_metrics.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.metrics'`

- [ ] **Step 3: Write `scripts/metrics.py`**

```python
# scripts/metrics.py
from datetime import datetime, timezone

from scripts import status as st

_TODAY = datetime.now(timezone.utc)

_OPEN_STATES = {"open", "in_progress", "new", "draft", "planning", "active"}
_CLOSED_STATES = {"closed", "cancelled", "rejected", "complete", "completed"}

_PLUGIN_MAP = {
    "demand":     "com.snc.sdlc.ppm_core",
    "ppm":        "com.snc.sdlc.ppm_core",
    "resource":   "com.snc.rm",
    "financial":  "com.snc.financial_mgmt",
    "agile":      "com.snc.agile",
    "apm":        "com.snc.apm",
    "innovation": "com.snc.innovation_mgmt",
}


def compute_metrics(buckets, client, input_dir):
    adoption = buckets.get("_sidecar_spm_adoption") or {}
    health   = buckets.get("_sidecar_portfolio_health") or {}
    plugins  = adoption.get("plugins") or {}

    modules = {
        "demand":     _demand(buckets, plugins, health),
        "ppm":        _ppm(buckets, plugins, health),
        "resource":   _resource(buckets, plugins, health),
        "financial":  _financial(buckets, plugins),
        "agile":      _agile(buckets, plugins),
        "apm":        _apm(buckets, plugins),
        "innovation": _innovation(buckets, plugins),
    }

    return {
        "modules":            modules,
        "governance":         _governance(buckets),
        "roles":              adoption.get("roles") or {},
        "pa_adoption":        _pa_adoption(buckets),
        "data_quality": {
            "projects_stale_90d":     health.get("projects_stale_90d"),
            "projects_stale_90d_pct": health.get("projects_stale_90d_pct"),
            "demands_stale_90d":      health.get("demands_stale_90d"),
            "demands_stale_90d_pct":  health.get("demands_stale_90d_pct"),
        },
        "spm_workspace_active": adoption.get("spm_workspace_active"),
        "coverage_matrix":    _coverage_matrix(modules),
        "_context": {
            "exports_dir":  str(input_dir),
            "generated_on": _TODAY.strftime("%Y-%m-%d"),
            "client":       client,
        },
    }


# ── Demand ────────────────────────────────────────────────────────────────────

def _demand(buckets, plugins, health):
    records = buckets.get("pm_demand") or []
    n = len(records)
    approvals = buckets.get("sysapproval_approver") or []

    by_state = _count_by(records, "state")
    open_recs = [r for r in records if _is_open(r.get("state"))]

    ages = [_age_days(r.get("sys_created_on")) for r in open_recs]
    ages = [a for a in ages if a is not None]
    avg_age = round(sum(ages) / len(ages)) if ages else None

    linked  = sum(1 for r in records if r.get("project"))
    no_own  = sum(1 for r in records if not r.get("assigned_to"))
    dem_ids = {r.get("sys_id") for r in records}
    appr_d  = {a.get("source_id") for a in approvals
               if a.get("source_table") == "pm_demand" and a.get("source_id") in dem_ids}

    return {
        "total":                n,
        "by_state":             by_state,
        "avg_age_open_days":    avg_age,
        "linked_to_project_pct": st.pct(linked, n),
        "no_owner_pct":         st.pct(no_own, n),
        "with_approval_pct":    st.pct(len(appr_d), n),
        "demand_priority_set_pct": health.get("demand_priority_set_pct"),
        "plugin_active":        plugins.get(_PLUGIN_MAP["demand"], False),
        "footprint_status": {
            "total":             st.measured(n) if n else st.not_collected("pm_demand not collected"),
            "linked_pct":        st.measured(st.pct(linked, n)) if n else st.not_collected(),
            "with_approval_pct": st.measured(st.pct(len(appr_d), n)) if n else st.not_collected(),
        },
    }


# ── PPM ───────────────────────────────────────────────────────────────────────

def _ppm(buckets, plugins, health):
    projects = buckets.get("pm_project") or []
    tasks    = buckets.get("pm_project_task") or []
    programs = buckets.get("pm_program") or []
    statuses = buckets.get("pm_project_status") or []
    approvals = buckets.get("sysapproval_approver") or []
    n = len(projects)

    by_state   = _count_by(projects, "state")
    proj_ids   = {p.get("sys_id") for p in projects}

    # Projects under a program
    with_prog  = sum(1 for p in projects if p.get("program"))

    # Shell projects (no tasks)
    task_proj_ids = {t.get("project") for t in tasks}
    shell = sum(1 for p in projects if p.get("sys_id") not in task_proj_ids)

    # No business owner
    no_owner = sum(1 for p in projects
                   if not p.get("business_owner") and not p.get("assigned_to"))

    # Avg schedule variance (planned end - actual end, days)
    variances = []
    for p in projects:
        pe = _parse_date(p.get("end_date"))
        ae = _parse_date(p.get("actual_end_date"))
        if pe and ae:
            variances.append(abs((ae - pe).days))
    avg_variance = round(sum(variances) / len(variances)) if variances else None

    # Status report in last 30 days
    cutoff_30 = _days_ago(30)
    recent_status_proj = {s.get("project") for s in statuses
                          if _parse_date(s.get("sys_created_on")) and
                          _parse_date(s.get("sys_created_on")) >= cutoff_30}
    active_proj = {p.get("sys_id") for p in projects if _is_open(p.get("state"))}
    status_30d_pct = st.pct(len(recent_status_proj & active_proj), len(active_proj)) \
                     if statuses and active_proj else None

    # Approvals
    appr_proj = {a.get("source_id") for a in approvals
                 if a.get("source_table") == "pm_project" and a.get("source_id") in proj_ids}

    return {
        "total":                  n,
        "by_state":               by_state,
        "program_count":          len(programs),
        "with_program_pct":       st.pct(with_prog, n),
        "shell_project_pct":      st.pct(shell, n),
        "no_owner_pct":           st.pct(no_owner, n),
        "avg_schedule_variance_days": avg_variance,
        "status_report_30d_pct":  status_30d_pct,
        "with_approval_pct":      st.pct(len(appr_proj), n),
        "project_completeness_pct": health.get("project_completeness_pct"),
        "plugin_active":          plugins.get(_PLUGIN_MAP["ppm"], False),
        "footprint_status": {
            "total":         st.measured(n) if n else st.not_collected("pm_project not collected"),
            "shell_pct":     st.measured(st.pct(shell, n)) if n else st.not_collected(),
            "status_30d_pct": st.measured(status_30d_pct) if status_30d_pct is not None
                              else st.not_collected("pm_project_status not collected"),
        },
    }


# ── Resource ──────────────────────────────────────────────────────────────────

def _resource(buckets, plugins, health):
    plans       = buckets.get("pm_resource_plan") or []
    allocations = buckets.get("pm_resource_allocation") or []
    timesheets  = buckets.get("timesheet_entry") or []
    n = len(plans)

    linked    = sum(1 for p in plans if p.get("project"))
    no_named  = sum(1 for p in plans if not p.get("resource"))

    # Utilisation: allocated / available where both present
    util_pairs = [(float(p["planned_hours"]), float(p["available_hours"]))
                  for p in plans
                  if _safe_float(p.get("planned_hours")) and _safe_float(p.get("available_hours"))]
    util_rate = None
    if util_pairs:
        total_alloc = sum(x[0] for x in util_pairs)
        total_avail = sum(x[1] for x in util_pairs)
        util_rate   = st.pct(total_alloc, total_avail)

    # Alloc records with both allocated + actual
    alloc_with_actual = sum(1 for a in allocations
                            if _safe_float(a.get("allocated_hours"))
                            and _safe_float(a.get("actual_hours")))
    alloc_coverage = st.pct(alloc_with_actual, len(allocations)) if allocations else None

    # Timesheet cross-read
    plan_ids = {p.get("sys_id") for p in plans}
    ts_plan_ids = {t.get("timesheet") for t in timesheets}  # approximate: timesheet ref
    ts_coverage = st.pct(len(plan_ids & ts_plan_ids), n) if timesheets and n else None

    return {
        "total":               n,
        "linked_to_project_pct": st.pct(linked, n),
        "no_named_resource_pct": st.pct(no_named, n),
        "utilisation_rate":    util_rate,
        "alloc_actual_coverage_pct": alloc_coverage,
        "timesheet_coverage_pct": ts_coverage,
        "resource_plan_named_pct": health.get("resource_plan_named_pct"),
        "plugin_active":       plugins.get(_PLUGIN_MAP["resource"], False),
        "footprint_status": {
            "total":       st.measured(n) if n else st.not_collected("pm_resource_plan not collected"),
            "util_rate":   st.measured(util_rate) if util_rate is not None else st.not_collected(),
            "ts_coverage": st.measured(ts_coverage) if ts_coverage is not None
                           else st.not_collected("timesheet_entry not collected"),
        },
    }


# ── Financial ─────────────────────────────────────────────────────────────────

def _financial(buckets, plugins):
    projects  = buckets.get("pm_project") or []
    financials = buckets.get("pm_project_financials") or []
    cost_plans = buckets.get("pm_cost_plan") or []
    budgets    = buckets.get("pm_budget_plan") or []
    n_proj = len(projects)

    proj_ids = {p.get("sys_id") for p in projects}
    fin_proj  = {f.get("project") for f in financials}
    cost_proj = {c.get("project") for c in cost_plans}
    bud_proj  = {b.get("project") for b in budgets}

    with_fin     = st.pct(len(fin_proj  & proj_ids), n_proj) if n_proj else None
    with_cost    = st.pct(len(cost_proj & proj_ids), n_proj) if n_proj else None
    with_budget  = st.pct(len(bud_proj  & proj_ids), n_proj) if n_proj else None
    no_financial = st.pct(
        len(proj_ids - fin_proj - cost_proj - bud_proj), n_proj
    ) if n_proj else None

    # Budget vs actual variance availability
    bva_count = sum(1 for f in financials
                    if _safe_float(f.get("planned_cost")) and _safe_float(f.get("actual_cost")))
    bva_pct = st.pct(bva_count, len(financials)) if financials else None

    # Cost plan by type
    by_type = _count_by(cost_plans, "cost_type")

    return {
        "projects_with_financials_pct": with_fin,
        "projects_with_cost_plan_pct":  with_cost,
        "projects_with_budget_plan_pct": with_budget,
        "projects_no_financial_pct":    no_financial,
        "budget_vs_actual_availability_pct": bva_pct,
        "cost_plan_by_type":            by_type,
        "plugin_active":                plugins.get(_PLUGIN_MAP["financial"], False),
        "footprint_status": {
            "financials_collected": st.measured(len(financials)) if financials
                                    else st.not_collected("pm_project_financials not collected"),
            "cost_plans_collected": st.measured(len(cost_plans)) if cost_plans
                                    else st.not_collected("pm_cost_plan not collected"),
            "budgets_collected":    st.measured(len(budgets)) if budgets
                                    else st.not_collected("pm_budget_plan not collected"),
        },
    }


# ── Agile ─────────────────────────────────────────────────────────────────────

def _agile(buckets, plugins):
    stories = buckets.get("rm_story") or []
    sprints = buckets.get("rm_sprint") or []
    teams   = buckets.get("rm_team") or []
    n_s = len(stories)

    by_state     = _count_by(stories, "state")
    no_sprint    = sum(1 for s in stories if not s.get("sprint"))
    no_team      = sum(1 for s in stories if not s.get("team"))

    # Avg velocity: completed_points per completed sprint
    completed_sp = [s for s in sprints if (s.get("state") or "").lower() in ("complete", "closed")]
    velocity_vals = [_safe_float(s.get("completed_points")) for s in completed_sp]
    velocity_vals = [v for v in velocity_vals if v is not None]
    avg_velocity = round(sum(velocity_vals) / len(velocity_vals), 1) if velocity_vals else None

    stories_per_team = {}
    for s in stories:
        t = s.get("team") or "_unassigned"
        stories_per_team[t] = stories_per_team.get(t, 0) + 1

    return {
        "total_stories":         n_s,
        "by_state":              by_state,
        "team_count":            len(teams),
        "sprint_count":          len(sprints),
        "completed_sprint_count": len(completed_sp),
        "avg_velocity":          avg_velocity,
        "no_sprint_pct":         st.pct(no_sprint, n_s),
        "no_team_pct":           st.pct(no_team, n_s),
        "stories_per_team_dist": stories_per_team,
        "plugin_active":         plugins.get(_PLUGIN_MAP["agile"], False),
        "footprint_status": {
            "stories":  st.measured(n_s) if n_s else st.not_collected("rm_story not collected"),
            "sprints":  st.measured(len(sprints)) if sprints else st.not_collected("rm_sprint not collected"),
            "teams":    st.measured(len(teams)) if teams else st.not_collected("rm_team not collected"),
        },
    }


# ── APM ───────────────────────────────────────────────────────────────────────

def _apm(buckets, plugins):
    apps      = buckets.get("apm_appl_now") or []
    lifecycle = buckets.get("apm_appl_lifecycle") or []
    n = len(apps)

    lifecycle_app_ids = {lc.get("application") for lc in lifecycle}
    with_lifecycle = sum(1 for a in apps if a.get("sys_id") in lifecycle_app_ids)
    with_stage     = sum(1 for a in apps if a.get("lifecycle_stage"))
    with_owner     = sum(1 for a in apps if a.get("business_owner"))
    with_cmdb      = sum(1 for a in apps if a.get("cmdb_ci"))

    return {
        "total":                n,
        "with_lifecycle_pct":  st.pct(with_lifecycle, n),
        "with_lifecycle_stage_pct": st.pct(with_stage, n),
        "with_owner_pct":      st.pct(with_owner, n),
        "with_cmdb_link_pct":  st.pct(with_cmdb, n),
        "plugin_active":       plugins.get(_PLUGIN_MAP["apm"], False),
        "footprint_status": {
            "total":     st.measured(n) if n else st.not_collected("apm_appl_now not collected"),
            "lifecycle": st.measured(st.pct(with_lifecycle, n)) if n else st.not_collected(),
            "owner":     st.measured(st.pct(with_owner, n)) if n else st.not_collected(),
        },
    }


# ── Innovation ────────────────────────────────────────────────────────────────

def _innovation(buckets, plugins):
    ideas      = buckets.get("innovation_idea") or []
    challenges = buckets.get("innovation_challenge") or []
    n = len(ideas)

    by_state  = _count_by(ideas, "state")
    no_owner  = sum(1 for i in ideas if not i.get("assigned_to"))
    linked    = sum(1 for i in ideas if i.get("demand") or i.get("project"))

    chal_dist = {}
    for i in ideas:
        c = i.get("challenge") or "_none"
        chal_dist[c] = chal_dist.get(c, 0) + 1

    ideas_per_challenge = (round(n / len(challenges), 1)
                           if challenges and n else None)

    return {
        "total":                   n,
        "challenge_count":         len(challenges),
        "by_state":                by_state,
        "no_owner_pct":            st.pct(no_owner, n),
        "linked_to_demand_or_project_pct": st.pct(linked, n),
        "ideas_per_challenge":     ideas_per_challenge,
        "plugin_active":           plugins.get(_PLUGIN_MAP["innovation"], False),
        "footprint_status": {
            "ideas":      st.measured(n) if n else st.not_collected("innovation_idea not collected"),
            "challenges": st.measured(len(challenges)) if challenges
                          else st.not_collected("innovation_challenge not collected"),
        },
    }


# ── Governance ────────────────────────────────────────────────────────────────

def _governance(buckets):
    ts_periods  = buckets.get("timesheet_period") or []
    ts_entries  = buckets.get("timesheet_entry") or []
    approvals   = buckets.get("sysapproval_approver") or []
    statuses    = buckets.get("pm_project_status") or []
    criteria    = buckets.get("pm_scoring_criterion") or []
    scores      = buckets.get("pm_portfolio_score") or []

    active_periods = sum(1 for p in ts_periods if (p.get("state") or "").lower() == "open")
    entries_per_period = (round(len(ts_entries) / active_periods, 1)
                          if active_periods else None)

    demand_approvals  = [a for a in approvals if a.get("source_table") == "pm_demand"]
    project_approvals = [a for a in approvals if a.get("source_table") == "pm_project"]

    demand_with_approvals  = len({a.get("source_id") for a in demand_approvals})
    project_with_approvals = len({a.get("source_id") for a in project_approvals})

    # Scoring model coverage
    scored_ids = {s.get("source_id") for s in scores}
    demand_scored = sum(1 for s in scores if s.get("source_table") == "pm_demand")

    return {
        "timesheets": {
            "active_periods":       active_periods,
            "total_entries":        len(ts_entries),
            "entries_per_period":   entries_per_period,
            "collected":            bool(ts_periods or ts_entries),
        },
        "approvals": {
            "demand_records_with_approvals":  demand_with_approvals,
            "project_records_with_approvals": project_with_approvals,
            "collected":                      bool(approvals),
        },
        "status_reports": {
            "total":      len(statuses),
            "collected":  bool(statuses),
        },
        "scoring_models": {
            "criteria_count":     len(criteria),
            "scored_records":     len(scored_ids),
            "demand_scored":      demand_scored,
            "collected":          bool(criteria or scores),
        },
    }


# ── PA Adoption ───────────────────────────────────────────────────────────────

def _pa_adoption(buckets):
    scorecards = buckets.get("pa_scorecard") or []
    return {
        "scorecard_count": len(scorecards),
        "collected":       bool(scorecards),
    }


# ── Coverage Matrix ───────────────────────────────────────────────────────────

_DIMENSIONS = ["activation", "data_volume", "data_completeness",
               "process_adoption", "integration"]

_MODULE_LABELS = {
    "demand":     "Demand Management",
    "ppm":        "Project Portfolio Mgmt",
    "resource":   "Resource Management",
    "financial":  "Financial Management",
    "agile":      "Agile Development",
    "apm":        "Application Portfolio",
    "innovation": "Innovation Management",
}


def _coverage_matrix(modules):
    rows = []
    for mod_key, mod_label in _MODULE_LABELS.items():
        mod = modules[mod_key]
        for dim in _DIMENSIONS:
            status = "measured" if mod.get("plugin_active") is not None else "not_collected"
            rows.append({
                "module":    mod_key,
                "module_label": mod_label,
                "dimension": dim,
                "status":    status,
                "value_token": None,  # filled by scoring.py after scoring
                "rag":       None,    # filled by scoring.py
                "note":      "",
            })
    return rows


# ── Helpers ───────────────────────────────────────────────────────────────────

def _count_by(records, field):
    counts = {}
    for r in records:
        v = (r.get(field) or "unknown").lower().strip()
        counts[v] = counts.get(v, 0) + 1
    return counts


def _is_open(state):
    return (state or "").lower().strip() in _OPEN_STATES


def _age_days(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (_TODAY - dt).days
    except ValueError:
        return None


def _parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _days_ago(n):
    from datetime import timedelta
    return _TODAY - timedelta(days=n)


def _safe_float(val):
    try:
        return float(val) if val not in (None, "", "null") else None
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_metrics.py
```

Expected:
```
  PASS  test_top_level_keys
  PASS  test_module_keys
  PASS  test_demand_total
  PASS  test_demand_no_owner_pct
  PASS  test_ppm_total
  PASS  test_resource_not_collected_when_absent
  PASS  test_context_client
  PASS  test_coverage_matrix_length
  PASS  test_roles_populated
metrics.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/metrics.py scripts/test_metrics.py
git commit -m "feat: add metrics computation module for all 7 SPM modules"
```

---

## Task 13: `facts.py` — Serialize metrics.json + CSVs

**Files:**
- Create: `scripts/facts.py`
- Create: `scripts/test_facts.py`

**Interfaces:**
- Consumes: `metrics` dict from `compute_metrics()`
- Produces:
  - `write_facts(metrics, out_dir) -> str` — writes `metrics.json`, returns path
  - `write_csvs(metrics, data_dir)` — writes 8 CSV files to `data_dir`

- [ ] **Step 1: Write `scripts/test_facts.py`**

```python
# scripts/test_facts.py
import sys, os, json, csv, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _minimal_metrics():
    return {
        "modules": {
            "demand":     {"total": 100, "by_state": {"open": 60, "closed": 40},
                           "no_owner_pct": 15.0, "linked_to_project_pct": 44.0,
                           "with_approval_pct": 38.0, "avg_age_open_days": 47,
                           "demand_priority_set_pct": 70.0, "plugin_active": True, "footprint_status": {}},
            "ppm":        {"total": 50, "by_state": {}, "program_count": 5,
                           "with_program_pct": 60.0, "shell_project_pct": 10.0,
                           "no_owner_pct": 8.0, "avg_schedule_variance_days": 12,
                           "status_report_30d_pct": 55.0, "with_approval_pct": 40.0,
                           "project_completeness_pct": 65, "plugin_active": True, "footprint_status": {}},
            "resource":   {"total": 30, "linked_to_project_pct": 90.0,
                           "no_named_resource_pct": 10.0, "utilisation_rate": 75.0,
                           "alloc_actual_coverage_pct": 60.0, "timesheet_coverage_pct": None,
                           "resource_plan_named_pct": 90, "plugin_active": True, "footprint_status": {}},
            "financial":  {"projects_with_cost_plan_pct": 55.0, "projects_with_budget_plan_pct": 40.0,
                           "projects_no_financial_pct": 20.0, "budget_vs_actual_availability_pct": 35.0,
                           "cost_plan_by_type": {}, "projects_with_financials_pct": 60.0,
                           "plugin_active": False, "footprint_status": {}},
            "agile":      {"total_stories": 200, "by_state": {}, "team_count": 8, "sprint_count": 20,
                           "completed_sprint_count": 15, "avg_velocity": 22.5,
                           "no_sprint_pct": 12.0, "no_team_pct": 5.0,
                           "stories_per_team_dist": {}, "plugin_active": True, "footprint_status": {}},
            "apm":        {"total": 45, "with_lifecycle_pct": 60.0, "with_lifecycle_stage_pct": 55.0,
                           "with_owner_pct": 70.0, "with_cmdb_link_pct": 40.0,
                           "plugin_active": False, "footprint_status": {}},
            "innovation": {"total": 25, "challenge_count": 3, "by_state": {},
                           "no_owner_pct": 20.0, "linked_to_demand_or_project_pct": 32.0,
                           "ideas_per_challenge": 8.3, "plugin_active": False, "footprint_status": {}},
        },
        "governance":  {"timesheets": {"active_periods": 2, "total_entries": 500,
                                        "entries_per_period": 250, "collected": True},
                         "approvals":  {"demand_records_with_approvals": 38,
                                        "project_records_with_approvals": 20, "collected": True},
                         "status_reports": {"total": 55, "collected": True},
                         "scoring_models": {"criteria_count": 5, "scored_records": 30,
                                            "demand_scored": 10, "collected": True}},
        "roles":       {"portfolio_manager": 4, "project_manager": 12},
        "pa_adoption": {"scorecard_count": 3, "collected": True},
        "data_quality": {"projects_stale_90d": 5, "projects_stale_90d_pct": 10,
                          "demands_stale_90d": 8, "demands_stale_90d_pct": 8},
        "spm_workspace_active": True,
        "coverage_matrix": [],
        "_context": {"exports_dir": "/tmp", "generated_on": "2026-08-04", "client": "test"},
    }

def test_writes_metrics_json():
    with tempfile.TemporaryDirectory() as tmp:
        from scripts.facts import write_facts
        path = write_facts(_minimal_metrics(), tmp)
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "modules" in data
        assert data["_context"]["client"] == "test"

def test_writes_all_csvs():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        from scripts.facts import write_csvs
        write_csvs(_minimal_metrics(), data_dir)
        expected = [
            "demand_summary.csv", "project_portfolio.csv", "resource_utilisation.csv",
            "financial_coverage.csv", "agile_adoption.csv", "apm_coverage.csv",
            "innovation_pipeline.csv", "readiness_scorecard.csv",
        ]
        for fname in expected:
            assert os.path.exists(os.path.join(data_dir, fname)), f"Missing: {fname}"

def test_csv_has_header():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = os.path.join(tmp, "data")
        from scripts.facts import write_csvs
        write_csvs(_minimal_metrics(), data_dir)
        with open(os.path.join(data_dir, "demand_summary.csv"), newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert len(header) > 0

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("facts.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_facts.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.facts'`

- [ ] **Step 3: Write `scripts/facts.py`**

```python
# scripts/facts.py
import csv
import json
import os


def write_facts(metrics, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "metrics.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)
    return path


def write_csvs(metrics, data_dir):
    os.makedirs(data_dir, exist_ok=True)
    mods = metrics.get("modules", {})
    _write_demand_summary(mods.get("demand", {}), data_dir)
    _write_project_portfolio(mods.get("ppm", {}), data_dir)
    _write_resource_utilisation(mods.get("resource", {}), data_dir)
    _write_financial_coverage(mods.get("financial", {}), data_dir)
    _write_agile_adoption(mods.get("agile", {}), data_dir)
    _write_apm_coverage(mods.get("apm", {}), data_dir)
    _write_innovation_pipeline(mods.get("innovation", {}), data_dir)
    _write_readiness_scorecard(metrics.get("coverage_matrix", []), data_dir)


def _csv_writer(data_dir, fname, fieldnames):
    path = os.path.join(data_dir, fname)
    f = open(path, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    return f, writer


def _write_demand_summary(d, data_dir):
    f, w = _csv_writer(data_dir, "demand_summary.csv",
                        ["state", "count", "metric", "value"])
    for state, count in (d.get("by_state") or {}).items():
        w.writerow({"state": state, "count": count, "metric": "", "value": ""})
    for metric, val in [
        ("total", d.get("total")),
        ("avg_age_open_days", d.get("avg_age_open_days")),
        ("linked_to_project_pct", d.get("linked_to_project_pct")),
        ("no_owner_pct", d.get("no_owner_pct")),
        ("with_approval_pct", d.get("with_approval_pct")),
        ("priority_set_pct", d.get("demand_priority_set_pct")),
    ]:
        w.writerow({"state": "", "count": "", "metric": metric, "value": val})
    f.close()


def _write_project_portfolio(d, data_dir):
    f, w = _csv_writer(data_dir, "project_portfolio.csv",
                        ["metric", "value"])
    for metric, val in [
        ("total", d.get("total")),
        ("program_count", d.get("program_count")),
        ("with_program_pct", d.get("with_program_pct")),
        ("shell_project_pct", d.get("shell_project_pct")),
        ("no_owner_pct", d.get("no_owner_pct")),
        ("avg_schedule_variance_days", d.get("avg_schedule_variance_days")),
        ("status_report_30d_pct", d.get("status_report_30d_pct")),
        ("with_approval_pct", d.get("with_approval_pct")),
        ("project_completeness_pct", d.get("project_completeness_pct")),
    ]:
        w.writerow({"metric": metric, "value": val})
    for state, count in (d.get("by_state") or {}).items():
        w.writerow({"metric": f"state:{state}", "value": count})
    f.close()


def _write_resource_utilisation(d, data_dir):
    f, w = _csv_writer(data_dir, "resource_utilisation.csv", ["metric", "value"])
    for metric, val in [
        ("total_plans", d.get("total")),
        ("linked_to_project_pct", d.get("linked_to_project_pct")),
        ("no_named_resource_pct", d.get("no_named_resource_pct")),
        ("utilisation_rate", d.get("utilisation_rate")),
        ("alloc_actual_coverage_pct", d.get("alloc_actual_coverage_pct")),
        ("timesheet_coverage_pct", d.get("timesheet_coverage_pct")),
        ("resource_plan_named_pct", d.get("resource_plan_named_pct")),
    ]:
        w.writerow({"metric": metric, "value": val})
    f.close()


def _write_financial_coverage(d, data_dir):
    f, w = _csv_writer(data_dir, "financial_coverage.csv", ["metric", "value"])
    for metric, val in [
        ("projects_with_cost_plan_pct", d.get("projects_with_cost_plan_pct")),
        ("projects_with_budget_plan_pct", d.get("projects_with_budget_plan_pct")),
        ("projects_no_financial_pct", d.get("projects_no_financial_pct")),
        ("budget_vs_actual_availability_pct", d.get("budget_vs_actual_availability_pct")),
    ]:
        w.writerow({"metric": metric, "value": val})
    for ctype, count in (d.get("cost_plan_by_type") or {}).items():
        w.writerow({"metric": f"cost_type:{ctype}", "value": count})
    f.close()


def _write_agile_adoption(d, data_dir):
    f, w = _csv_writer(data_dir, "agile_adoption.csv", ["metric", "value"])
    for metric, val in [
        ("total_stories", d.get("total_stories")),
        ("team_count", d.get("team_count")),
        ("sprint_count", d.get("sprint_count")),
        ("completed_sprint_count", d.get("completed_sprint_count")),
        ("avg_velocity", d.get("avg_velocity")),
        ("no_sprint_pct", d.get("no_sprint_pct")),
        ("no_team_pct", d.get("no_team_pct")),
    ]:
        w.writerow({"metric": metric, "value": val})
    for state, count in (d.get("by_state") or {}).items():
        w.writerow({"metric": f"state:{state}", "value": count})
    f.close()


def _write_apm_coverage(d, data_dir):
    f, w = _csv_writer(data_dir, "apm_coverage.csv", ["metric", "value"])
    for metric, val in [
        ("total", d.get("total")),
        ("with_lifecycle_pct", d.get("with_lifecycle_pct")),
        ("with_lifecycle_stage_pct", d.get("with_lifecycle_stage_pct")),
        ("with_owner_pct", d.get("with_owner_pct")),
        ("with_cmdb_link_pct", d.get("with_cmdb_link_pct")),
    ]:
        w.writerow({"metric": metric, "value": val})
    f.close()


def _write_innovation_pipeline(d, data_dir):
    f, w = _csv_writer(data_dir, "innovation_pipeline.csv", ["metric", "value"])
    for metric, val in [
        ("total_ideas", d.get("total")),
        ("challenge_count", d.get("challenge_count")),
        ("no_owner_pct", d.get("no_owner_pct")),
        ("linked_to_demand_or_project_pct", d.get("linked_to_demand_or_project_pct")),
        ("ideas_per_challenge", d.get("ideas_per_challenge")),
    ]:
        w.writerow({"metric": metric, "value": val})
    for state, count in (d.get("by_state") or {}).items():
        w.writerow({"metric": f"state:{state}", "value": count})
    f.close()


def _write_readiness_scorecard(coverage_matrix, data_dir):
    f, w = _csv_writer(data_dir, "readiness_scorecard.csv",
                        ["module", "module_label", "dimension", "status",
                         "value_token", "rag", "note"])
    for row in coverage_matrix:
        w.writerow(row)
    f.close()
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_facts.py
```

Expected:
```
  PASS  test_writes_metrics_json
  PASS  test_writes_all_csvs
  PASS  test_csv_has_header
facts.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/facts.py scripts/test_facts.py
git commit -m "feat: add facts module — metrics.json + 8 companion CSVs"
```

---

## Task 14: `scoring.py` — RAG + % Engine

**Files:**
- Create: `scripts/scoring.py`
- Create: `scripts/test_scoring.py`

**Interfaces:**
- Consumes: `metrics` dict from `compute_metrics()`
- Produces:
  - `score_all(metrics) -> dict` — `{module_slug: {dimension: score, module_score, rag}}`
  - `overall_score(module_scores) -> int | None`
  - `enrich_coverage_matrix(metrics, scores) -> list[dict]` — fills `value_token` + `rag` in coverage_matrix rows

- [ ] **Step 1: Write `scripts/test_scoring.py`**

```python
# scripts/test_scoring.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.scoring import score_all, overall_score, rag, enrich_coverage_matrix

def _metrics_green():
    # Demand module in great shape
    return {
        "modules": {
            "demand": {
                "total": 500, "plugin_active": True,
                "linked_to_project_pct": 75.0, "no_owner_pct": 5.0,
                "with_approval_pct": 80.0, "demand_priority_set_pct": 85.0,
                "by_state": {"open": 300, "closed": 200}, "footprint_status": {},
            },
            "ppm": {"total": 80, "plugin_active": True, "with_program_pct": 75.0,
                    "shell_project_pct": 5.0, "status_report_30d_pct": 80.0,
                    "with_approval_pct": 70.0, "project_completeness_pct": 75,
                    "no_owner_pct": 5.0, "avg_schedule_variance_days": 3,
                    "by_state": {}, "program_count": 10, "footprint_status": {}},
            "resource": {"total": 0, "linked_to_project_pct": None,
                         "no_named_resource_pct": None, "utilisation_rate": None,
                         "alloc_actual_coverage_pct": None, "timesheet_coverage_pct": None,
                         "resource_plan_named_pct": None, "plugin_active": False, "footprint_status": {}},
            "financial": {"projects_with_cost_plan_pct": 0, "projects_with_budget_plan_pct": 0,
                          "projects_no_financial_pct": 100, "budget_vs_actual_availability_pct": None,
                          "cost_plan_by_type": {}, "projects_with_financials_pct": 0,
                          "plugin_active": False, "footprint_status": {}},
            "agile": {"total_stories": 0, "team_count": 0, "sprint_count": 0,
                      "completed_sprint_count": 0, "avg_velocity": None,
                      "no_sprint_pct": None, "no_team_pct": None,
                      "stories_per_team_dist": {}, "by_state": {},
                      "plugin_active": False, "footprint_status": {}},
            "apm": {"total": 0, "with_lifecycle_pct": None, "with_lifecycle_stage_pct": None,
                    "with_owner_pct": None, "with_cmdb_link_pct": None,
                    "plugin_active": False, "footprint_status": {}},
            "innovation": {"total": 0, "challenge_count": 0, "by_state": {},
                           "no_owner_pct": None, "linked_to_demand_or_project_pct": None,
                           "ideas_per_challenge": None, "plugin_active": False, "footprint_status": {}},
        },
        "governance": {
            "timesheets": {"active_periods": 3, "total_entries": 800,
                           "entries_per_period": 267, "collected": True},
            "approvals":  {"demand_records_with_approvals": 400,
                           "project_records_with_approvals": 50, "collected": True},
            "status_reports": {"total": 90, "collected": True},
            "scoring_models": {"criteria_count": 8, "scored_records": 60,
                               "demand_scored": 25, "collected": True},
        },
        "coverage_matrix": [],
    }

def test_rag_green():
    assert rag(70) == "green"
    assert rag(100) == "green"

def test_rag_amber():
    assert rag(40) == "amber"
    assert rag(69) == "amber"

def test_rag_red():
    assert rag(0) == "red"
    assert rag(39) == "red"

def test_rag_not_collected():
    assert rag(None) == "not_collected"

def test_demand_has_module_score():
    scores = score_all(_metrics_green())
    assert "module_score" in scores["demand"]
    assert scores["demand"]["module_score"] is not None

def test_demand_activation_100_when_plugin_active():
    scores = score_all(_metrics_green())
    assert scores["demand"]["activation"] == 100

def test_demand_data_volume_high():
    scores = score_all(_metrics_green())
    # 500 demands > threshold of 50 → 100%
    assert scores["demand"]["data_volume"] == 100

def test_resource_not_collected_gives_none_score():
    scores = score_all(_metrics_green())
    assert scores["resource"]["module_score"] is None

def test_overall_score_is_average():
    module_scores = {"demand": 80, "ppm": 70, "resource": None,
                     "financial": 0, "agile": 0, "apm": 0, "innovation": 0}
    result = overall_score(module_scores)
    # average of 80, 70, 0, 0, 0, 0 (None excluded) = 150/6 = 25
    assert result == 25

def test_enrich_fills_coverage_matrix():
    import copy
    from scripts.metrics import _coverage_matrix as build_cm
    m = _metrics_green()
    m["coverage_matrix"] = build_cm(m["modules"])
    scores = score_all(m)
    enriched = enrich_coverage_matrix(m, scores)
    # All rows should have rag filled
    for row in enriched:
        assert row["rag"] is not None, f"rag not set for {row['module']} / {row['dimension']}"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("scoring.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_scoring.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.scoring'`

- [ ] **Step 3: Write `scripts/scoring.py`**

```python
# scripts/scoring.py

WEIGHTS = {
    "activation":        0.20,
    "data_volume":       0.20,
    "data_completeness": 0.25,
    "process_adoption":  0.25,
    "integration":       0.10,
}

# Records needed to score 100% on data_volume
_VOLUME_100 = {"demand": 50, "ppm": 20, "resource": 10, "financial": 10,
               "agile": 50, "apm": 10, "innovation": 5}
_VOLUME_60  = {"demand": 10, "ppm": 5,  "resource": 5,  "financial": 3,
               "agile": 10, "apm": 3,   "innovation": 2}


def rag(score):
    if score is None:
        return "not_collected"
    if score >= 70:
        return "green"
    if score >= 40:
        return "amber"
    return "red"


def overall_score(module_scores):
    vals = [v for v in module_scores.values() if v is not None]
    if not vals:
        return None
    return round(sum(vals) / len(vals))


def module_score(dimension_scores):
    total_w = total_v = 0.0
    for dim, score in dimension_scores.items():
        if score is None or dim not in WEIGHTS:
            continue
        w = WEIGHTS[dim]
        total_w += w
        total_v += w * score
    if not total_w:
        return None
    return round(total_v / total_w)


def score_all(metrics):
    mods = metrics.get("modules", {})
    gov  = metrics.get("governance", {})
    results = {}
    for mod_key in ["demand", "ppm", "resource", "financial", "agile", "apm", "innovation"]:
        mod = mods.get(mod_key, {})
        dims = _score_module(mod_key, mod, gov)
        ms   = module_score(dims)
        results[mod_key] = {**dims, "module_score": ms, "rag": rag(ms)}
    return results


def enrich_coverage_matrix(metrics, scores):
    rows = metrics.get("coverage_matrix", [])
    _dim_scores = {}  # (module, dimension) -> score
    for mod_key, mod_data in scores.items():
        for dim in WEIGHTS:
            _dim_scores[(mod_key, dim)] = mod_data.get(dim)

    enriched = []
    for row in rows:
        r = dict(row)
        key = (r.get("module"), r.get("dimension"))
        score = _dim_scores.get(key)
        r["rag"] = rag(score)
        r["value_token"] = f"{score}%" if score is not None else "not_collected"
        enriched.append(r)
    return enriched


# ── Per-module scoring ─────────────────────────────────────────────────────────

def _score_module(mod_key, mod, gov):
    return {
        "activation":        _activation(mod_key, mod),
        "data_volume":       _data_volume(mod_key, mod),
        "data_completeness": _data_completeness(mod_key, mod, gov),
        "process_adoption":  _process_adoption(mod_key, mod, gov),
        "integration":       _integration(mod_key, mod),
    }


def _activation(mod_key, mod):
    plugin = mod.get("plugin_active")
    if plugin is None:
        return None  # sidecar not collected
    return 100 if plugin else 0


def _data_volume(mod_key, mod):
    total_key = "total" if mod_key != "agile" else "total_stories"
    total = mod.get(total_key) or 0
    t100 = _VOLUME_100.get(mod_key, 10)
    t60  = _VOLUME_60.get(mod_key, 3)
    if total >= t100:
        return 100
    if total >= t60:
        return 60
    if total > 0:
        return 20
    return 0


def _data_completeness(mod_key, mod, gov):
    if mod_key == "demand":
        # avg of: priority set %, (100 - no_owner_pct)
        vals = [_v(mod.get("demand_priority_set_pct")),
                _inv(mod.get("no_owner_pct"))]
        return _avg_non_none(vals)
    if mod_key == "ppm":
        vals = [_v(mod.get("project_completeness_pct")),
                _inv(mod.get("shell_project_pct")),
                _inv(mod.get("no_owner_pct"))]
        return _avg_non_none(vals)
    if mod_key == "resource":
        vals = [_v(mod.get("resource_plan_named_pct")),
                _v(mod.get("alloc_actual_coverage_pct"))]
        return _avg_non_none(vals)
    if mod_key == "financial":
        vals = [_v(mod.get("projects_with_cost_plan_pct")),
                _v(mod.get("projects_with_budget_plan_pct")),
                _v(mod.get("budget_vs_actual_availability_pct"))]
        return _avg_non_none(vals)
    if mod_key == "agile":
        vals = [_inv(mod.get("no_sprint_pct")),
                _inv(mod.get("no_team_pct"))]
        return _avg_non_none(vals)
    if mod_key == "apm":
        vals = [_v(mod.get("with_lifecycle_stage_pct")),
                _v(mod.get("with_owner_pct"))]
        return _avg_non_none(vals)
    if mod_key == "innovation":
        vals = [_inv(mod.get("no_owner_pct"))]
        return _avg_non_none(vals)
    return None


def _process_adoption(mod_key, mod, gov):
    approvals = gov.get("approvals", {})
    timesheets = gov.get("timesheets", {})
    status_rep = gov.get("status_reports", {})
    scoring    = gov.get("scoring_models", {})

    if mod_key == "demand":
        vals = [_v(mod.get("with_approval_pct")),
                100 if scoring.get("demand_scored", 0) > 0 else 0]
        return _avg_non_none(vals)
    if mod_key == "ppm":
        vals = [_v(mod.get("status_report_30d_pct")),
                _v(mod.get("with_approval_pct"))]
        return _avg_non_none(vals)
    if mod_key == "resource":
        # timesheet adoption as proxy
        entries = timesheets.get("total_entries") or 0
        ts_score = 100 if entries > 200 else (60 if entries > 50 else (20 if entries > 0 else 0))
        return ts_score if timesheets.get("collected") else None
    if mod_key == "financial":
        # approvals on cost/budget plans
        n_appr = approvals.get("project_records_with_approvals") or 0
        return 100 if n_appr > 10 else (60 if n_appr > 2 else (20 if n_appr > 0 else 0)) \
               if approvals.get("collected") else None
    if mod_key == "agile":
        # velocity as proxy — presence of completed sprints
        completed = mod.get("completed_sprint_count") or 0
        return 100 if completed > 5 else (60 if completed > 1 else (20 if completed > 0 else 0))
    if mod_key == "apm":
        return None  # no direct process adoption signal for APM
    if mod_key == "innovation":
        converted = mod.get("linked_to_demand_or_project_pct") or 0
        return _v(converted)
    return None


def _integration(mod_key, mod):
    if mod_key == "demand":
        return _v(mod.get("linked_to_project_pct"))
    if mod_key == "ppm":
        return _v(mod.get("with_program_pct"))
    if mod_key == "resource":
        return _v(mod.get("linked_to_project_pct"))
    if mod_key == "financial":
        return _v(mod.get("projects_with_financials_pct"))
    if mod_key == "agile":
        # stories assigned to a team = integration with team management
        return _inv(mod.get("no_team_pct"))
    if mod_key == "apm":
        return _v(mod.get("with_cmdb_link_pct"))
    if mod_key == "innovation":
        return _v(mod.get("linked_to_demand_or_project_pct"))
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _v(val):
    """Return val clamped 0-100, or None if None."""
    if val is None:
        return None
    return max(0.0, min(100.0, float(val)))


def _inv(val):
    """Invert a percentage (100 - val), e.g. no_owner_pct=20 → 80."""
    if val is None:
        return None
    return max(0.0, 100.0 - float(val))


def _avg_non_none(vals):
    clean = [v for v in vals if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean))
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_scoring.py
```

Expected:
```
  PASS  test_rag_green
  PASS  test_rag_amber
  PASS  test_rag_red
  PASS  test_rag_not_collected
  PASS  test_demand_has_module_score
  PASS  test_demand_activation_100_when_plugin_active
  PASS  test_demand_data_volume_high
  PASS  test_resource_not_collected_gives_none_score
  PASS  test_overall_score_is_average
  PASS  test_enrich_fills_coverage_matrix
scoring.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/scoring.py scripts/test_scoring.py
git commit -m "feat: add scoring engine — RAG thresholds, weighted module scores, coverage matrix enrichment"
```

---

## Task 15: `findings.py` — Structured Findings

**Files:**
- Create: `scripts/findings.py`
- Create: `scripts/test_findings.py`

**Interfaces:**
- Consumes: `metrics` dict, `scores` dict from `score_all()`
- Produces:
  - `generate_findings(metrics, scores) -> list[dict]` — returns list of finding dicts
  - Each finding: `{id, module, dimension, rag, observation, significance}`

- [ ] **Step 1: Write `scripts/test_findings.py`**

```python
# scripts/test_findings.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _scores_with_reds():
    return {
        "demand":     {"activation": 100, "data_volume": 100, "data_completeness": 35,
                       "process_adoption": 30, "integration": 44, "module_score": 55, "rag": "amber"},
        "ppm":        {"activation": 100, "data_volume": 60,  "data_completeness": 65,
                       "process_adoption": 25, "integration": 60, "module_score": 54, "rag": "amber"},
        "resource":   {"activation": None, "data_volume": None, "data_completeness": None,
                       "process_adoption": None, "integration": None, "module_score": None, "rag": "not_collected"},
        "financial":  {"activation": 0,   "data_volume": 0,   "data_completeness": 0,
                       "process_adoption": 0,  "integration": 0,  "module_score": 0, "rag": "red"},
        "agile":      {"activation": 0,   "data_volume": 0,   "data_completeness": None,
                       "process_adoption": 0,  "integration": None, "module_score": 0, "rag": "red"},
        "apm":        {"activation": 0,   "data_volume": 20,  "data_completeness": 55,
                       "process_adoption": None, "integration": 40, "module_score": 28, "rag": "red"},
        "innovation": {"activation": 0,   "data_volume": 0,   "data_completeness": None,
                       "process_adoption": None, "integration": None, "module_score": 0, "rag": "red"},
    }

def _minimal_metrics():
    return {
        "modules": {
            "demand":     {"total": 500, "with_approval_pct": 30.0, "no_owner_pct": 18.0},
            "ppm":        {"total": 80,  "status_report_30d_pct": 25.0},
            "resource":   {"total": 0},
            "financial":  {"projects_with_cost_plan_pct": 0.0},
            "agile":      {"total_stories": 0},
            "apm":        {"total": 45},
            "innovation": {"total": 0},
        },
    }

def test_returns_list():
    from scripts.findings import generate_findings
    f = generate_findings(_minimal_metrics(), _scores_with_reds())
    assert isinstance(f, list)

def test_findings_have_required_keys():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for f in findings:
        for key in ["id", "module", "dimension", "rag", "observation", "significance"]:
            assert key in f, f"Missing key '{key}' in finding {f.get('id')}"

def test_ids_are_sequential():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for i, f in enumerate(findings, 1):
        assert f["id"] == f"SPM-{i:03d}", f"Expected SPM-{i:03d}, got {f['id']}"

def test_red_modules_produce_findings():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    modules_with_findings = {f["module"] for f in findings}
    assert "financial" in modules_with_findings
    assert "agile" in modules_with_findings

def test_not_collected_does_not_produce_finding():
    from scripts.findings import generate_findings
    findings = generate_findings(_minimal_metrics(), _scores_with_reds())
    for f in findings:
        assert f["rag"] != "not_collected"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("findings.py tests passed.")
```

- [ ] **Step 2: Run test — expect failure**

```bash
python scripts/test_findings.py
```

Expected: `ModuleNotFoundError: No module named 'scripts.findings'`

- [ ] **Step 3: Write `scripts/findings.py`**

```python
# scripts/findings.py

_MODULE_LABELS = {
    "demand":     "Demand Management",
    "ppm":        "Project Portfolio Management",
    "resource":   "Resource Management",
    "financial":  "Financial Management",
    "agile":      "Agile Development",
    "apm":        "Application Portfolio Management",
    "innovation": "Innovation Management",
}

_DIM_LABELS = {
    "activation":        "Plugin Activation",
    "data_volume":       "Data Volume",
    "data_completeness": "Data Completeness",
    "process_adoption":  "Process Adoption",
    "integration":       "Cross-Module Integration",
}

_SIGNIFICANCE = {
    ("demand",     "process_adoption"):  "Low approval chain coverage limits governance auditability for demand decisions.",
    ("demand",     "data_completeness"): "Incomplete demand records reduce prioritisation signal reliability.",
    ("demand",     "integration"):       "Demands not linked to projects cannot be tracked through to delivery.",
    ("ppm",        "process_adoption"):  "Infrequent status reports indicate project health is not being actively monitored.",
    ("ppm",        "data_completeness"): "Incomplete project records undermine portfolio visibility and reporting accuracy.",
    ("ppm",        "integration"):       "Projects not grouped under programs limits portfolio-level planning.",
    ("resource",   "activation"):        "Resource management module is not active — resource demand and supply cannot be managed in platform.",
    ("resource",   "data_completeness"): "Resource plans lack named resources, reducing capacity planning reliability.",
    ("resource",   "process_adoption"):  "Low timesheet adoption means actual effort is not captured against plans.",
    ("financial",  "activation"):        "Financial management module is not active — cost and budget tracking is absent from platform.",
    ("financial",  "data_completeness"): "Projects lack cost or budget plans, making financial governance via SPM impossible.",
    ("financial",  "process_adoption"):  "Absence of approval records on financial plans indicates bypassed governance controls.",
    ("agile",      "activation"):        "Agile module is not active — sprint-based delivery tracking is not in use.",
    ("agile",      "data_volume"):       "Very few agile records indicate the module is not being used operationally.",
    ("agile",      "process_adoption"):  "No completed sprints means velocity and throughput cannot be measured.",
    ("apm",        "activation"):        "APM module is not active — application portfolio is not managed in platform.",
    ("apm",        "data_completeness"): "Applications lack lifecycle stage or business owner, reducing portfolio decision quality.",
    ("apm",        "integration"):       "Applications not linked to CMDB services limits impact analysis capability.",
    ("innovation", "activation"):        "Innovation management module is not active — idea pipeline is not tracked in platform.",
    ("innovation", "data_volume"):       "Very few innovation records indicate the module is not being used.",
    ("innovation", "integration"):       "Ideas not linked to demands or projects cannot be tracked through to delivery.",
}


def generate_findings(metrics, scores):
    findings = []
    mods = metrics.get("modules", {})

    for mod_key in ["demand", "ppm", "resource", "financial", "agile", "apm", "innovation"]:
        mod_scores = scores.get(mod_key, {})
        mod_data   = mods.get(mod_key, {})

        for dim in ["activation", "data_volume", "data_completeness",
                    "process_adoption", "integration"]:
            score = mod_scores.get(dim)
            r = _rag(score)
            if r in ("red", "amber") and score is not None:
                obs = _observation(mod_key, dim, score, mod_data)
                sig = _SIGNIFICANCE.get((mod_key, dim), "")
                if obs:
                    findings.append({
                        "module":      mod_key,
                        "module_label": _MODULE_LABELS[mod_key],
                        "dimension":   dim,
                        "rag":         r,
                        "observation": obs,
                        "significance": sig,
                    })

    # Assign sequential IDs
    for i, f in enumerate(findings, 1):
        f["id"] = f"SPM-{i:03d}"

    return findings


def _rag(score):
    if score is None:
        return "not_collected"
    if score >= 70:
        return "green"
    if score >= 40:
        return "amber"
    return "red"


def _observation(mod_key, dim, score, mod_data):
    if dim == "activation":
        return f"{_MODULE_LABELS[mod_key]}: plugin is inactive (activation score: {score}%)."
    if dim == "data_volume":
        total_key = "total_stories" if mod_key == "agile" else "total"
        total = mod_data.get(total_key) or 0
        return f"{_MODULE_LABELS[mod_key]}: {total} records found (data volume score: {score}%)."
    if dim == "data_completeness":
        return f"{_MODULE_LABELS[mod_key]}: data completeness score {score}% — key fields are partially populated."
    if dim == "process_adoption":
        return f"{_MODULE_LABELS[mod_key]}: process adoption score {score}% — governance mechanisms are underutilised."
    if dim == "integration":
        return f"{_MODULE_LABELS[mod_key]}: cross-module integration score {score}% — records are not fully linked across SPM modules."
    return ""
```

- [ ] **Step 4: Run test — expect pass**

```bash
python scripts/test_findings.py
```

Expected:
```
  PASS  test_returns_list
  PASS  test_findings_have_required_keys
  PASS  test_ids_are_sequential
  PASS  test_red_modules_produce_findings
  PASS  test_not_collected_does_not_produce_finding
findings.py tests passed.
```

- [ ] **Step 5: Commit**

```bash
git add scripts/findings.py scripts/test_findings.py
git commit -m "feat: add findings module — SPM-NNN structured findings from scoring results"
```

---

## Part 3 Complete

Run all Part 3 tests together:

```bash
python scripts/test_load.py && \
python scripts/test_metrics.py && \
python scripts/test_facts.py && \
python scripts/test_scoring.py && \
python scripts/test_findings.py
```

Expected: all 5 test suites pass.

**Proceed to:** `plan-part4-output-e2e.md`

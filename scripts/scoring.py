# scripts/scoring.py

WEIGHTS = {
    "activation":        0.20,
    "data_volume":       0.20,
    "data_completeness": 0.25,
    "process_adoption":  0.25,
    "integration":       0.10,
}

_VOLUME_100 = {"demand": 50, "ppm": 20, "resource": 10, "financial": 10,
               "agile": 50, "apm": 10, "innovation": 5, "csdm": 500,
               "timesheet": 500}
_VOLUME_60  = {"demand": 10, "ppm": 5,  "resource": 5,  "financial": 3,
               "agile": 10, "apm": 3,   "innovation": 2, "csdm": 50,
               "timesheet": 100}


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
    for mod_key in ["demand", "ppm", "resource", "financial", "agile",
                    "apm", "innovation", "csdm", "timesheet"]:
        mod  = mods.get(mod_key, {})
        dims = _score_module(mod_key, mod, gov)
        ms   = module_score(dims)
        results[mod_key] = {**dims, "module_score": ms, "rag": rag(ms)}
    return results


def enrich_coverage_matrix(metrics, scores):
    rows = metrics.get("coverage_matrix", [])
    _dim_scores = {}
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


def _score_module(mod_key, mod, gov):
    return {
        "activation":        _activation(mod_key, mod),
        "data_volume":       _data_volume(mod_key, mod),
        "data_completeness": _data_completeness(mod_key, mod, gov),
        "process_adoption":  _process_adoption(mod_key, mod, gov),
        "integration":       _integration(mod_key, mod),
    }


def _activation(mod_key, mod):
    if mod_key == "timesheet":
        # Non-use is recorded but not penalised — return None when not in use
        return 100 if mod.get("in_use") else None
    plugin = mod.get("plugin_active")
    if plugin is None or plugin is False:
        return None
    # demand shares a plugin ID with PPM — only score active if records exist
    if mod_key == "demand" and not (mod.get("total") or 0):
        return None
    return 100


def _data_volume(mod_key, mod):
    if mod_key == "timesheet":
        if not mod.get("in_use"):
            return None
        total = mod.get("total_entries") or 0
        if not total:
            return None
        if total >= _VOLUME_100["timesheet"]: return 100
        if total >= _VOLUME_60["timesheet"]:  return 60
        return 20
    if mod_key == "csdm":
        total = mod.get("total_ci") or 0
        if not total:
            return None
        if total >= _VOLUME_100["csdm"]: return 100
        if total >= _VOLUME_60["csdm"]:  return 60
        return 20
    total_key = "total" if mod_key != "agile" else "total_stories"
    total = mod.get(total_key) or 0
    if not total:
        return None
    t100 = _VOLUME_100.get(mod_key, 10)
    t60  = _VOLUME_60.get(mod_key, 3)
    if total >= t100:
        return 100
    if total >= t60:
        return 60
    return 20


def _data_completeness(mod_key, mod, gov):
    if mod_key == "demand":
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
    if mod_key == "csdm":
        vals = [_v(mod.get("ci_with_operational_status_pct")),
                _v(mod.get("ci_with_owner_pct")),
                _v(mod.get("ci_with_support_group_pct")),
                _v(mod.get("ci_with_environment_pct"))]
        return _avg_non_none(vals)
    if mod_key == "timesheet":
        if not mod.get("in_use"):
            return None
        # Score based on entries-per-period density: >20/period=100, >5=60, >0=20
        epp = mod.get("entries_per_period") or 0
        return 100 if epp > 20 else (60 if epp > 5 else (20 if epp > 0 else 0))
    return None


def _process_adoption(mod_key, mod, gov):
    approvals  = gov.get("approvals", {})
    timesheets = gov.get("timesheets", {})
    scoring    = gov.get("scoring_models", {})

    if mod_key == "demand":
        if not (mod.get("total") or 0):
            return None
        vals = [
            _v(mod.get("with_approval_pct")),
            # Portfolio scoring models in use
            100 if scoring.get("demand_scored", 0) > 0 else 0,
            # Demand workbench governance proxy: recent activity on review-ready demands (items 7, 8)
            _v(mod.get("demand_reviewed_14d_pct")),
            # Lifecycle throughput: demands progressing beyond submission (item 13)
            _v(mod.get("demand_throughput_pct")),
            # Staleness quality: fewer stale demands = better governance (item 1)
            _inv(mod.get("stale_60d_pct")),
        ]
        return _avg_non_none(vals)

    if mod_key == "ppm":
        vals = [
            _v(mod.get("status_report_30d_pct")),
            _v(mod.get("with_approval_pct")),
            # Project staleness: active projects not updated monthly signal poor oversight (item 2)
            _inv(mod.get("stale_30d_pct")),
        ]
        return _avg_non_none(vals)

    if mod_key == "resource":
        if not (mod.get("total") or 0):
            return None
        vals = []
        # Timesheet adoption as primary process signal
        if timesheets.get("collected"):
            entries = timesheets.get("total_entries") or 0
            ts_score = 100 if entries > 200 else (60 if entries > 50 else (20 if entries > 0 else 0))
            vals.append(ts_score)
        # Resource request staleness (item 9)
        stale_pct = mod.get("resource_requests_stale_30d_pct")
        if stale_pct is not None:
            vals.append(_inv(stale_pct))
        return _avg_non_none(vals) if vals else None

    if mod_key == "financial":
        n_appr = approvals.get("project_records_with_approvals") or 0
        return (100 if n_appr > 10 else (60 if n_appr > 2 else (20 if n_appr > 0 else 0))) \
               if approvals.get("collected") else None

    if mod_key == "agile":
        completed = mod.get("completed_sprint_count") or 0
        sprint_score = 100 if completed > 5 else (60 if completed > 1 else (20 if completed > 0 else 0))
        # Backlog staleness: stale backlog items signal poor hygiene (item 3)
        stale_pct = mod.get("backlog_stale_45d_pct")
        if stale_pct is not None:
            return _avg_non_none([sprint_score, _inv(stale_pct)])
        return sprint_score

    if mod_key == "apm":
        return None

    if mod_key == "innovation":
        if not mod.get("plugin_active"):
            return None
        converted = mod.get("linked_to_demand_or_project_pct") or 0
        return _v(converted)

    if mod_key == "csdm":
        vals = [_v(mod.get("ci_discovered_pct")),
                _v(mod.get("services_with_owner_pct"))]
        return _avg_non_none(vals)

    if mod_key == "timesheet":
        if not mod.get("in_use"):
            return None
        n_periods = mod.get("total_periods") or 0
        closed    = mod.get("closed_periods") or 0
        # % of periods properly closed and processed
        return st_pct(closed, n_periods) if n_periods else None

    return None


def _integration(mod_key, mod):
    if mod_key == "demand":
        # Include portfolio + program linkage alongside project linkage (items 4, 5, 6)
        vals = [_v(mod.get("linked_to_project_pct"))]
        portfolio_pct = mod.get("demand_with_portfolio_pct")
        program_pct   = mod.get("demand_with_program_pct")
        if portfolio_pct is not None:
            vals.append(_v(portfolio_pct))
        if program_pct is not None:
            vals.append(_v(program_pct))
        return _avg_non_none(vals)

    if mod_key == "ppm":
        # Projects not grouped under programs (item 6 — already existed, retained prominently)
        return _v(mod.get("with_program_pct"))

    if mod_key == "resource":
        return _v(mod.get("linked_to_project_pct"))

    if mod_key == "financial":
        return _v(mod.get("projects_with_financials_pct"))

    if mod_key == "agile":
        return _inv(mod.get("no_team_pct"))

    if mod_key == "apm":
        return _v(mod.get("with_cmdb_link_pct"))

    if mod_key == "innovation":
        return _v(mod.get("linked_to_demand_or_project_pct"))

    if mod_key == "csdm":
        total_ci   = mod.get("total_ci") or 0
        total_rels = mod.get("total_relationships") or 0
        if not total_ci:
            return None
        ratio = total_rels / total_ci
        return 100 if ratio >= 2.0 else (60 if ratio >= 0.5 else 20)

    if mod_key == "timesheet":
        if not mod.get("in_use"):
            return None
        # Coverage of resource plans with timesheet entries
        return _v(mod.get("resource_plan_coverage_pct"))

    return None


def _v(val):
    if val is None:
        return None
    return max(0.0, min(100.0, float(val)))


def _inv(val):
    if val is None:
        return None
    return max(0.0, 100.0 - float(val))


def _avg_non_none(vals):
    clean = [v for v in vals if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean))


def st_pct(numerator, denominator):
    """Percentage helper for use within this module (avoids circular import)."""
    if not denominator:
        return None
    return round(100 * numerator / denominator, 1)

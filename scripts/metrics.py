# scripts/metrics.py
from datetime import datetime, timezone

from scripts import status as st

_TODAY = datetime.now(timezone.utc)

# Human-readable labels + ServiceNow numeric choice codes (e.g. 1=Open, 2=Work In Progress)
_OPEN_STATES = {"open", "in_progress", "new", "draft", "planning", "active", "1", "2", "-5"}
_CLOSED_STATES = {"closed", "cancelled", "rejected", "complete", "completed"}

# Demand states that indicate the demand has progressed beyond initial submission
_DEMAND_PROGRESSED_STATES = {
    "qualified", "approved", "implementing", "implemented",
    "complete", "completed", "closed",
}

# Demand states that indicate the record is awaiting governance review
_DEMAND_REVIEW_STATES = {
    "qualified", "under_review", "submitted", "pending_approval",
    "awaiting_approval",
}

# Resource plan states considered "open / awaiting fulfilment"
_RESOURCE_OPEN_STATES = {"open", "requested", "pending", "submitted", "draft"}

# Story states considered backlog — includes ServiceNow numeric choice codes:
# -6=Backlog, -7=Ready, -5=Draft; and human-readable labels used in mock/export data
_STORY_BACKLOG_STATES = {"open", "new", "backlog", "ready", "todo", "-5", "-6", "-7", "1"}

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
        "csdm":       _csdm(buckets),
        "timesheet":  _timesheet(buckets),
    }

    return {
        "modules":            modules,
        "governance":         _governance(buckets),
        "roles":              adoption.get("roles") or {},
        "pa_adoption":        _pa_adoption(buckets),
        "data_quality": {
            "projects_stale_30d":     health.get("projects_stale_30d"),
            "projects_stale_30d_pct": health.get("projects_stale_30d_pct"),
            "demands_stale_60d":      health.get("demands_stale_60d"),
            "demands_stale_60d_pct":  health.get("demands_stale_60d_pct"),
        },
        "spm_workspace_active": adoption.get("spm_workspace_active"),
        "coverage_matrix":    _coverage_matrix(modules),
        "_context": {
            "exports_dir":  str(input_dir),
            "generated_on": _TODAY.strftime("%Y-%m-%d"),
            "client":       client,
        },
    }


def _demand(buckets, plugins, health):
    records   = buckets.get("pm_demand") or []
    n         = len(records)
    approvals = buckets.get("sysapproval_approver") or []

    by_state  = _count_by(records, "state")
    open_recs = [r for r in records if _is_open(r.get("state"))]

    ages = [_age_days(r.get("sys_created_on")) for r in open_recs]
    ages = [a for a in ages if a is not None]
    avg_age = round(sum(ages) / len(ages)) if ages else None

    linked  = sum(1 for r in records if r.get("project"))
    no_own  = sum(1 for r in records if not r.get("assigned_to"))
    dem_ids = {r.get("sys_id") for r in records}
    appr_d  = {_ref_id(a.get("document_id")) for a in approvals
               if a.get("source_table") == "pm_demand"
               and _ref_id(a.get("document_id")) in dem_ids}

    # Portfolio and program linkage (items 4, 5)
    with_portfolio = sum(1 for r in records if r.get("portfolio"))
    with_program   = sum(1 for r in records if r.get("program"))

    # Demand throughput: % of demands that have progressed beyond initial submission (item 13)
    throughput_count = sum(
        count for state, count in by_state.items()
        if state in _DEMAND_PROGRESSED_STATES
    )
    demand_throughput_pct = st.pct(throughput_count, n) if n else None

    # Demand workbench governance proxy: % of review-ready demands touched in last 14 days (items 7, 8)
    cutoff_14 = _days_ago(14)
    review_recs = [r for r in records if (r.get("state") or "").lower().strip() in _DEMAND_REVIEW_STATES]
    demand_reviewed_14d_pct = None
    if review_recs:
        reviewed = sum(
            1 for r in review_recs
            if _parse_date(r.get("sys_updated_on")) and
               _parse_date(r.get("sys_updated_on")) >= cutoff_14
        )
        demand_reviewed_14d_pct = st.pct(reviewed, len(review_recs))

    # Staleness from sidecar (60-day threshold for demands, item 1)
    stale_60d_pct = health.get("demands_stale_60d_pct")

    return {
        "total":                    n,
        "by_state":                 by_state,
        "avg_age_open_days":        avg_age,
        "linked_to_project_pct":   st.pct(linked, n),
        "demand_with_portfolio_pct": st.pct(with_portfolio, n),
        "demand_with_program_pct":  st.pct(with_program, n),
        "no_owner_pct":             st.pct(no_own, n),
        "with_approval_pct":        st.pct(len(appr_d), n),
        "demand_priority_set_pct":  health.get("demand_priority_set_pct"),
        "demand_throughput_pct":    demand_throughput_pct,
        "demand_reviewed_14d_pct":  demand_reviewed_14d_pct,
        "stale_60d_pct":            stale_60d_pct,
        "plugin_active":            plugins.get(_PLUGIN_MAP["demand"], False),
        "footprint_status": {
            "total":             st.measured(n) if n else st.not_collected("pm_demand not collected"),
            "linked_pct":        st.measured(st.pct(linked, n)) if n else st.not_collected(),
            "with_approval_pct": st.measured(st.pct(len(appr_d), n)) if n else st.not_collected(),
            "portfolio_pct":     st.measured(st.pct(with_portfolio, n)) if n else st.not_collected(),
            "program_pct":       st.measured(st.pct(with_program, n)) if n else st.not_collected(),
        },
    }


def _ppm(buckets, plugins, health):
    projects  = buckets.get("pm_project") or []
    tasks     = buckets.get("pm_project_task") or []
    programs  = buckets.get("pm_program") or []
    statuses  = buckets.get("pm_project_status") or []
    approvals = buckets.get("sysapproval_approver") or []
    n = len(projects)

    by_state   = _count_by(projects, "state")
    proj_ids   = {p.get("sys_id") for p in projects}

    with_prog  = sum(1 for p in projects if p.get("program"))

    task_proj_ids = {t.get("project") for t in tasks}
    shell = sum(1 for p in projects if p.get("sys_id") not in task_proj_ids)

    no_owner = sum(1 for p in projects
                   if not p.get("business_owner") and not p.get("assigned_to"))

    variances = []
    for p in projects:
        pe = _parse_date(p.get("end_date"))
        ae = _parse_date(p.get("actual_end_date"))
        if pe and ae:
            variances.append(abs((ae - pe).days))
    avg_variance = round(sum(variances) / len(variances)) if variances else None

    cutoff_30 = _days_ago(30)
    recent_status_proj = {s.get("project") for s in statuses
                          if _parse_date(s.get("sys_created_on")) and
                          _parse_date(s.get("sys_created_on")) >= cutoff_30}
    active_proj = {p.get("sys_id") for p in projects if _is_open(p.get("state"))}
    status_30d_pct = st.pct(len(recent_status_proj & active_proj), len(active_proj)) \
                     if statuses and active_proj else None

    appr_proj = {_ref_id(a.get("document_id")) for a in approvals
                 if a.get("source_table") == "pm_project"
                 and _ref_id(a.get("document_id")) in proj_ids}

    # Project staleness (30-day threshold — active projects should be updated monthly, item 2)
    stale_30d_pct = health.get("projects_stale_30d_pct")

    return {
        "total":                      n,
        "by_state":                   by_state,
        "program_count":              len(programs),
        "with_program_pct":           st.pct(with_prog, n),
        "shell_project_pct":          st.pct(shell, n),
        "no_owner_pct":               st.pct(no_owner, n),
        "avg_schedule_variance_days": avg_variance,
        "status_report_30d_pct":      status_30d_pct,
        "with_approval_pct":          st.pct(len(appr_proj), n),
        "project_completeness_pct":   health.get("project_completeness_pct"),
        "stale_30d_pct":              stale_30d_pct,
        "plugin_active":              plugins.get(_PLUGIN_MAP["ppm"], False),
        "footprint_status": {
            "total":          st.measured(n) if n else st.not_collected("pm_project not collected"),
            "shell_pct":      st.measured(st.pct(shell, n)) if n else st.not_collected(),
            "status_30d_pct": st.measured(status_30d_pct) if status_30d_pct is not None
                              else st.not_collected("pm_project_status not collected"),
        },
    }


def _resource(buckets, plugins, health):
    plans       = buckets.get("pm_resource_plan") or []
    allocations = buckets.get("pm_resource_allocation") or []
    timesheets  = buckets.get("timesheet_entry") or []
    n = len(plans)

    linked    = sum(1 for p in plans if p.get("project"))
    no_named  = sum(1 for p in plans if not p.get("resource"))

    util_pairs = [(float(p["planned_hours"]), float(p["available_hours"]))
                  for p in plans
                  if _safe_float(p.get("planned_hours")) and _safe_float(p.get("available_hours"))]
    util_rate = None
    if util_pairs:
        total_alloc = sum(x[0] for x in util_pairs)
        total_avail = sum(x[1] for x in util_pairs)
        util_rate   = st.pct(total_alloc, total_avail)

    alloc_with_actual = sum(1 for a in allocations
                            if _safe_float(a.get("allocated_hours"))
                            and _safe_float(a.get("actual_hours")))
    alloc_coverage = st.pct(alloc_with_actual, len(allocations)) if allocations else None

    plan_ids = {p.get("sys_id") for p in plans}
    ts_plan_ids = {t.get("timesheet") for t in timesheets}
    ts_coverage = st.pct(len(plan_ids & ts_plan_ids), n) if timesheets and n else None

    # Resource request staleness: open plans not updated in 30 days (item 9)
    cutoff_30 = _days_ago(30)
    open_plans = [p for p in plans
                  if (p.get("state") or "").lower().strip() in _RESOURCE_OPEN_STATES]
    resource_requests_stale_30d_pct = None
    if open_plans:
        stale = sum(
            1 for p in open_plans
            if _parse_date(p.get("sys_updated_on")) and
               _parse_date(p.get("sys_updated_on")) < cutoff_30
        )
        resource_requests_stale_30d_pct = st.pct(stale, len(open_plans))

    return {
        "total":                      n,
        "linked_to_project_pct":      st.pct(linked, n),
        "no_named_resource_pct":      st.pct(no_named, n),
        "utilisation_rate":           util_rate,
        "alloc_actual_coverage_pct":  alloc_coverage,
        "timesheet_coverage_pct":     ts_coverage,
        "resource_plan_named_pct":    health.get("resource_plan_named_pct"),
        "resource_requests_stale_30d_pct": resource_requests_stale_30d_pct,
        "plugin_active":              plugins.get(_PLUGIN_MAP["resource"], False),
        "footprint_status": {
            "total":       st.measured(n) if n else st.not_collected("pm_resource_plan not collected"),
            "util_rate":   st.measured(util_rate) if util_rate is not None else st.not_collected(),
            "ts_coverage": st.measured(ts_coverage) if ts_coverage is not None
                           else st.not_collected("timesheet_entry not collected"),
        },
    }


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

    bva_count = sum(1 for f in financials
                    if _safe_float(f.get("planned_cost")) and _safe_float(f.get("actual_cost")))
    bva_pct = st.pct(bva_count, len(financials)) if financials else None

    by_type = _count_by(cost_plans, "cost_type")

    return {
        "projects_with_financials_pct":  with_fin,
        "projects_with_cost_plan_pct":   with_cost,
        "projects_with_budget_plan_pct": with_budget,
        "projects_no_financial_pct":     no_financial,
        "budget_vs_actual_availability_pct": bva_pct,
        "cost_plan_by_type":             by_type,
        "plugin_active":                 plugins.get(_PLUGIN_MAP["financial"], False),
        "footprint_status": {
            "financials_collected": st.measured(len(financials)) if financials
                                    else st.not_collected("pm_project_financials not collected"),
            "cost_plans_collected": st.measured(len(cost_plans)) if cost_plans
                                    else st.not_collected("pm_cost_plan not collected"),
            "budgets_collected":    st.measured(len(budgets)) if budgets
                                    else st.not_collected("pm_budget_plan not collected"),
        },
    }


def _agile(buckets, plugins):
    stories = buckets.get("rm_story") or []
    sprints = buckets.get("rm_sprint") or []
    teams   = buckets.get("rm_team") or []
    n_s = len(stories)

    by_state     = _count_by(stories, "state")
    no_sprint    = sum(1 for s in stories if not s.get("sprint"))
    no_team      = sum(1 for s in stories if not s.get("team"))

    # rm_sprint state=3 = Complete in ServiceNow numeric codes
    completed_sp = [s for s in sprints if (s.get("state") or "").lower() in ("complete", "closed", "3")]
    velocity_vals = [_safe_float(s.get("completed_points")) for s in completed_sp]
    velocity_vals = [v for v in velocity_vals if v is not None]
    avg_velocity = round(sum(velocity_vals) / len(velocity_vals), 1) if velocity_vals else None

    stories_per_team = {}
    for s in stories:
        t = s.get("team") or "_unassigned"
        stories_per_team[t] = stories_per_team.get(t, 0) + 1

    # Backlog staleness: stories in backlog states not updated in 45 days (item 3)
    cutoff_45 = _days_ago(45)
    backlog_stories = [s for s in stories
                       if (s.get("state") or "").lower().strip() in _STORY_BACKLOG_STATES]
    backlog_stale_45d_pct = None
    if backlog_stories:
        stale = sum(
            1 for s in backlog_stories
            if _parse_date(s.get("sys_updated_on")) and
               _parse_date(s.get("sys_updated_on")) < cutoff_45
        )
        backlog_stale_45d_pct = st.pct(stale, len(backlog_stories))

    return {
        "total_stories":          n_s,
        "by_state":               by_state,
        "team_count":             len(teams),
        "sprint_count":           len(sprints),
        "completed_sprint_count": len(completed_sp),
        "avg_velocity":           avg_velocity,
        "no_sprint_pct":          st.pct(no_sprint, n_s),
        "no_team_pct":            st.pct(no_team, n_s),
        "backlog_stale_45d_pct":  backlog_stale_45d_pct,
        "stories_per_team_dist":  stories_per_team,
        "plugin_active":          plugins.get(_PLUGIN_MAP["agile"], False),
        "footprint_status": {
            "stories":  st.measured(n_s) if n_s else st.not_collected("rm_story not collected"),
            "sprints":  st.measured(len(sprints)) if sprints else st.not_collected("rm_sprint not collected"),
            "teams":    st.measured(len(teams)) if teams else st.not_collected("rm_team not collected"),
        },
    }


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
        "total":                    n,
        "with_lifecycle_pct":       st.pct(with_lifecycle, n),
        "with_lifecycle_stage_pct": st.pct(with_stage, n),
        "with_owner_pct":           st.pct(with_owner, n),
        "with_cmdb_link_pct":       st.pct(with_cmdb, n),
        "plugin_active":            plugins.get(_PLUGIN_MAP["apm"], False),
        "footprint_status": {
            "total":     st.measured(n) if n else st.not_collected("apm_appl_now not collected"),
            "lifecycle": st.measured(st.pct(with_lifecycle, n)) if n else st.not_collected(),
            "owner":     st.measured(st.pct(with_owner, n)) if n else st.not_collected(),
        },
    }


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
        "total":                          n,
        "challenge_count":                len(challenges),
        "by_state":                       by_state,
        "no_owner_pct":                   st.pct(no_owner, n),
        "linked_to_demand_or_project_pct": st.pct(linked, n),
        "ideas_per_challenge":            ideas_per_challenge,
        "plugin_active":                  plugins.get(_PLUGIN_MAP["innovation"], False),
        "footprint_status": {
            "ideas":      st.measured(n) if n else st.not_collected("innovation_idea not collected"),
            "challenges": st.measured(len(challenges)) if challenges
                          else st.not_collected("innovation_challenge not collected"),
        },
    }


def _csdm(buckets):
    cis      = buckets.get("cmdb_ci") or []
    services = buckets.get("cmdb_ci_service") or []
    rel_raw  = buckets.get("cmdb_rel_ci") or []
    if isinstance(rel_raw, list) and len(rel_raw) == 1 and isinstance(rel_raw[0], dict):
        rel_data = rel_raw[0]
    elif isinstance(rel_raw, dict):
        rel_data = rel_raw
    else:
        rel_data = {}

    n   = len(cis)
    nsv = len(services)

    def _has(r, field):
        v = r.get(field)
        return bool(v and str(v).strip() not in ("", "0", "null", "None"))

    with_op_status   = sum(1 for r in cis if _has(r, "operational_status")) if n else 0
    with_owner       = sum(1 for r in cis if _has(r, "owned_by")) if n else 0
    with_managed_by  = sum(1 for r in cis if _has(r, "managed_by")) if n else 0
    with_support_grp = sum(1 for r in cis if _has(r, "support_group")) if n else 0
    with_environment = sum(1 for r in cis if _has(r, "environment")) if n else 0

    discovered = sum(1 for r in cis
                     if _has(r, "discovery_source") and
                     r.get("discovery_source", "").lower() not in ("manual", "manual input", "")) if n else 0

    biz_services  = sum(1 for s in services
                        if (s.get("service_classification") or "").lower() in
                           ("business service", "businessservice")) if nsv else 0
    tech_services = sum(1 for s in services
                        if (s.get("service_classification") or "").lower() in
                           ("technical service", "technicalservice")) if nsv else 0
    svc_with_owner = sum(1 for s in services if _has(s, "owned_by")) if nsv else 0

    total_rels      = rel_data.get("total_relationships") or 0
    sampled_parents = rel_data.get("sampled_parent_count") or 0

    return {
        "total_ci":                       n,
        "total_services":                 nsv,
        "business_service_count":         biz_services,
        "technical_service_count":        tech_services,
        "total_relationships":            total_rels,
        "ci_with_operational_status_pct": st.pct(with_op_status, n),
        "ci_with_owner_pct":              st.pct(with_owner, n),
        "ci_with_managed_by_pct":         st.pct(with_managed_by, n),
        "ci_with_support_group_pct":      st.pct(with_support_grp, n),
        "ci_with_environment_pct":        st.pct(with_environment, n),
        "ci_discovered_pct":              st.pct(discovered, n),
        "services_with_owner_pct":        st.pct(svc_with_owner, nsv),
        "plugin_active":                  n > 0,
        "footprint_status": {
            "ci_total":       st.measured(n) if n else st.not_collected("cmdb_ci not collected"),
            "services_total": st.measured(nsv) if nsv else st.not_collected("cmdb_ci_service not collected"),
            "relationships":  st.measured(total_rels) if total_rels else st.not_collected("cmdb_rel_ci not collected"),
        },
    }


def _timesheet(buckets):
    """Timesheet assessment module (item 12).

    If the org has not configured timesheet periods, in_use=False and all
    dimension scores return None — non-use is recorded, not penalised.
    """
    periods    = buckets.get("timesheet_period") or []
    entries    = buckets.get("timesheet_entry") or []
    plans      = buckets.get("pm_resource_plan") or []

    n_periods  = len(periods)
    n_entries  = len(entries)
    in_use     = n_periods > 0

    active_periods = sum(1 for p in periods
                         if (p.get("state") or "").lower() in ("open", "active"))
    closed_periods = sum(1 for p in periods
                         if (p.get("state") or "").lower() in ("closed", "complete", "processed"))

    entries_per_period = round(n_entries / n_periods, 1) if n_periods and n_entries else None

    # Coverage: % of resource plans with at least one timesheet entry
    plan_ids    = {p.get("sys_id") for p in plans}
    ts_plan_ids = {t.get("timesheet") for t in entries}
    resource_plan_coverage_pct = (
        st.pct(len(plan_ids & ts_plan_ids), len(plan_ids))
        if plan_ids and entries else None
    )

    return {
        "in_use":                    in_use,
        "total_periods":             n_periods,
        "active_periods":            active_periods,
        "closed_periods":            closed_periods,
        "total_entries":             n_entries,
        "entries_per_period":        entries_per_period,
        "resource_plan_coverage_pct": resource_plan_coverage_pct,
        "plugin_active":             in_use,
        "footprint_status": {
            "periods": st.measured(n_periods) if in_use
                       else st.not_applicable("no timesheet periods configured"),
            "entries": st.measured(n_entries) if in_use
                       else st.not_applicable("timesheets not in use"),
        },
    }


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

    demand_with_approvals  = len({_ref_id(a.get("document_id")) for a in demand_approvals
                                  if _ref_id(a.get("document_id"))})
    project_with_approvals = len({_ref_id(a.get("document_id")) for a in project_approvals
                                  if _ref_id(a.get("document_id"))})

    scored_ids   = {s.get("source_id") for s in scores}
    demand_scored = sum(1 for s in scores if s.get("source_table") == "pm_demand")

    return {
        "timesheets": {
            "active_periods":     active_periods,
            "total_entries":      len(ts_entries),
            "entries_per_period": entries_per_period,
            "collected":          bool(ts_periods or ts_entries),
        },
        "approvals": {
            "demand_records_with_approvals":  demand_with_approvals,
            "project_records_with_approvals": project_with_approvals,
            "collected":                      bool(approvals),
        },
        "status_reports": {
            "total":     len(statuses),
            "collected": bool(statuses),
        },
        "scoring_models": {
            "criteria_count":  len(criteria),
            "scored_records":  len(scored_ids),
            "demand_scored":   demand_scored,
            "collected":       bool(criteria or scores),
        },
    }


def _pa_adoption(buckets):
    scorecards = buckets.get("pa_scorecard") or []
    return {
        "scorecard_count": len(scorecards),
        "collected":       bool(scorecards),
    }


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
    "csdm":       "CSDM/CMDB Health",
    "timesheet":  "Timesheet Management",
}


def _coverage_matrix(modules):
    rows = []
    for mod_key, mod_label in _MODULE_LABELS.items():
        mod = modules.get(mod_key, {})
        for dim in _DIMENSIONS:
            status = "measured" if mod.get("plugin_active") is not None else "not_collected"
            rows.append({
                "module":       mod_key,
                "module_label": mod_label,
                "dimension":    dim,
                "status":       status,
                "value_token":  None,
                "rag":          None,
                "note":         "",
            })
    return rows


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


def _ref_id(field_val):
    """Extract sys_id from a ServiceNow reference field (dict with 'value' key, or plain string)."""
    if isinstance(field_val, dict):
        return field_val.get("value") or None
    return field_val or None

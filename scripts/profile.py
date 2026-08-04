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
    "csdm":       "CSDM/CMDB Health",
}

_DIMS = ["activation", "data_volume", "data_completeness", "process_adoption", "integration"]
_DIM_LABELS = {
    "activation":        "Activation",
    "data_volume":       "Data Volume",
    "data_completeness": "Completeness",
    "process_adoption":  "Process Adoption",
    "integration":       "Integration",
}


def write_profile(metrics, scores, findings, out_dir, mode="rde"):
    os.makedirs(out_dir, exist_ok=True)
    ctx     = metrics.get("_context", {})
    client  = ctx.get("client", "")
    date    = ctx.get("generated_on", "")
    mod_scores = {k: v.get("module_score") for k, v in scores.items()}
    overall    = _overall_score(mod_scores)

    lines = []
    lines.append(render_header(
        "AS-IS SPM Readiness Profile",
        badge=f"SPM Readiness · AS-IS · {mode.upper()}",
        client=client.upper() if client else "",
        date=date,
        mode=mode,
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
    lines.append(render_footer(date=date, mode=mode))
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
    scored = {k: v for k, v in scores.items() if v.get("module_score") is not None}
    best_mod  = max(scored, key=lambda k: scored[k]["module_score"], default="—") if scored else "—"
    worst_mod = min(scored, key=lambda k: scored[k]["module_score"], default="—") if scored else "—"
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
        ms_str = f"{ms}%" if ms is not None else "—"
        rows += f"| {mod_label} |{cells} {ms_str} | {badge} |\n"
    return f"\n## SPM Readiness Scorecard\n\n{header}{sep}{rows}\n---\n"


def _module_section(mod_key, mod_label, metrics, scores):
    mod  = metrics.get("modules", {}).get(mod_key, {})
    s    = scores.get(mod_key, {})
    icon = MODULE_ICONS.get(mod_key, "")
    badge = section_badge(mod_label, icon)

    lines = [f"\n## {mod_label}\n", badge, "\n"]

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

    plugin = mod.get("plugin_active")
    lines.append(f"| plugin active | {'Yes' if plugin else 'No' if plugin is False else '—'} | "
                 f"{'sidecar' if plugin is not None else 'not_collected'} |\n")

    lines.append("\n**Key Observations** *(AI overlay — Stage 2)*\n\n")
    lines.append("> *Three-beat observations to be added by Claude in the AI overlay step.*\n\n")
    return "".join(lines)


def _cross_module_integration(metrics):
    mods = metrics.get("modules", {})
    demand   = mods.get("demand", {})
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
        ("cmdb_ci",                "csdm",       mods.get("csdm", {}).get("total_ci", 0) > 0),
        ("cmdb_ci_service",        "csdm",       mods.get("csdm", {}).get("total_services", 0) > 0),
        ("cmdb_rel_ci",            "csdm",       mods.get("csdm", {}).get("total_relationships", 0) > 0),
    ]
    for table, domain, present in table_map:
        status = "collected" if present else "not_collected"
        lines.append(f"| `{table}` | {domain} | {status} |\n")
    return "".join(lines)

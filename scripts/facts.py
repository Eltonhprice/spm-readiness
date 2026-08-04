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
    f, w = _csv_writer(data_dir, "project_portfolio.csv", ["metric", "value"])
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

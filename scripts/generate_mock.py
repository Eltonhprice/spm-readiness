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

    # CSDM / CMDB
    ci_classes = [
        "cmdb_ci_server", "cmdb_ci_appl", "cmdb_ci_computer", "cmdb_ci_ip_switch",
        "cmdb_ci_linux_server", "cmdb_ci_win_server", "cmdb_ci_database",
    ]
    discovery_sources = ["ServiceNow Discovery", "SCCM", "AWS Service", "Azure Resource", ""]
    cis = [
        {
            "sys_id":             _uid(),
            "name":               f"CI-{i:04d}",
            "sys_class_name":     random.choice(ci_classes),
            "operational_status": str(random.randint(1, 6)) if i % 8 != 0 else "",
            "managed_by":         _uid() if i % 5 != 0 else "",
            "owned_by":           _uid() if i % 4 != 0 else "",
            "support_group":      _uid() if i % 3 != 0 else "",
            "environment":        random.choice(["production", "development", "test", ""]) if i % 6 != 0 else "",
            "discovery_source":   random.choice(discovery_sources) if random.random() < 0.60 else "",
            "install_status":     "1",
            "sys_updated_on":     _date(random.randint(1, 180)),
        }
        for i in range(1, 151)
    ]
    _write(out_dir, "csdm", "cmdb_ci", cis)

    svc_classifications = [
        "Business Service", "Business Service", "Business Service",
        "Technical Service", "Technical Service",
    ]
    services = [
        {
            "sys_id":                  _uid(),
            "name":                    f"Service {i}",
            "sys_class_name":          "cmdb_ci_service",
            "operational_status":      "1",
            "service_classification":  random.choice(svc_classifications),
            "managed_by_group":        _uid() if i % 4 != 0 else "",
            "owned_by":                _uid() if i % 3 != 0 else "",
            "portfolio_status":        random.choice(["pipeline", "catalog", "retired", ""]),
            "sys_updated_on":          _date(random.randint(1, 120)),
        }
        for i in range(1, 21)
    ]
    _write(out_dir, "csdm", "cmdb_ci_service", services)

    # cmdb_rel_ci — collector outputs a single JSON object; wrap as 1-element array
    _write(out_dir, "csdm", "cmdb_rel_ci",
           [{"total_relationships": 180, "sampled_parent_count": 90}])

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
    print(f"  Demands: 140 | Projects: 60 | Stories: 200 | Apps: 45 | Ideas: 25 | CIs: 150 | Services: 20")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate mock SPM input data")
    ap.add_argument("--out", default="engagement/mock", help="Output directory")
    args = ap.parse_args(argv)
    generate_mock(args.out)


if __name__ == "__main__":
    main()

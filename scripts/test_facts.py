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

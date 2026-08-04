# scripts/test_scoring.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.scoring import score_all, overall_score, rag, enrich_coverage_matrix

def _metrics_green():
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
    assert scores["demand"]["data_volume"] == 100

def test_resource_not_collected_gives_none_score():
    scores = score_all(_metrics_green())
    assert scores["resource"]["module_score"] is None

def test_overall_score_is_average():
    module_scores = {"demand": 80, "ppm": 70, "resource": None,
                     "financial": 0, "agile": 0, "apm": 0, "innovation": 0}
    result = overall_score(module_scores)
    assert result == 25

def test_enrich_fills_coverage_matrix():
    from scripts.metrics import _coverage_matrix as build_cm
    m = _metrics_green()
    m["coverage_matrix"] = build_cm(m["modules"])
    scores = score_all(m)
    enriched = enrich_coverage_matrix(m, scores)
    for row in enriched:
        assert row["rag"] is not None, f"rag not set for {row['module']} / {row['dimension']}"

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("scoring.py tests passed.")

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
    assert m["modules"]["demand"]["no_owner_pct"] == 50.0

def test_ppm_total():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["modules"]["ppm"]["total"] == 1

def test_resource_not_collected_when_absent():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["modules"]["resource"]["total"] == 0

def test_context_client():
    m = compute_metrics(_minimal_buckets(), "acme", "/tmp/test")
    assert m["_context"]["client"] == "acme"

def test_coverage_matrix_length():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert len(m["coverage_matrix"]) == 45  # 9 modules × 5 dimensions

def test_roles_populated():
    m = compute_metrics(_minimal_buckets(), "test", "/tmp/test")
    assert m["roles"]["portfolio_manager"] == 2
    assert m["roles"]["project_manager"] == 5

if __name__ == "__main__":
    for name, fn in [(k, v) for k, v in globals().items() if k.startswith("test_")]:
        fn()
        print(f"  PASS  {name}")
    print("metrics.py tests passed.")

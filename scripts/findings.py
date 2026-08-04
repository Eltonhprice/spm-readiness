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

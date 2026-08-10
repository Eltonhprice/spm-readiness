(function() {
  var SIDECAR_NAME = "_sidecar_portfolio_health";

  var result = {
    project_completeness_pct: null,
    demand_priority_set_pct: null,
    resource_plan_named_pct: null,
    projects_stale_30d: null,
    projects_stale_30d_pct: null,
    demands_stale_60d: null,
    demands_stale_60d_pct: null
  };

  // Separate cutoffs: projects updated monthly expected; demands allow longer qualification periods
  var cutoff30 = new GlideDateTime();
  cutoff30.addSeconds(-30 * 86400);
  var cutoff30Str = cutoff30.getDisplayValue();

  var cutoff60 = new GlideDateTime();
  cutoff60.addSeconds(-60 * 86400);
  var cutoff60Str = cutoff60.getDisplayValue();

  // Project completeness: name + assigned_to + state + start_date + end_date all populated
  var projTest = new GlideRecord("pm_project");
  if (projTest.isValid()) {
    var gaTotal = new GlideAggregate("pm_project");
    gaTotal.addAggregate("COUNT"); gaTotal.query();
    var totalProj = 0;
    if (gaTotal.next()) { totalProj = parseInt(gaTotal.getAggregate("COUNT"), 10); }

    var gaComplete = new GlideAggregate("pm_project");
    gaComplete.addAggregate("COUNT");
    gaComplete.addEncodedQuery(
      "short_descriptionISNOTEMPTY^assigned_toISNOTEMPTY^" +
      "stateISNOTEMPTY^start_dateISNOTEMPTY^end_dateISNOTEMPTY"
    );
    gaComplete.query();
    var completeProj = 0;
    if (gaComplete.next()) { completeProj = parseInt(gaComplete.getAggregate("COUNT"), 10); }

    result.project_completeness_pct = totalProj > 0
      ? Math.round(100 * completeProj / totalProj) : null;

    // Active projects not updated in 30 days — monthly update cadence expected for in-flight work
    var gaStale = new GlideAggregate("pm_project");
    gaStale.addAggregate("COUNT");
    gaStale.addEncodedQuery("sys_updated_on<" + cutoff30Str + "^stateNOT INclosed,cancelled");
    gaStale.query();
    result.projects_stale_30d = 0;
    if (gaStale.next()) { result.projects_stale_30d = parseInt(gaStale.getAggregate("COUNT"), 10); }
    result.projects_stale_30d_pct = totalProj > 0
      ? Math.round(100 * result.projects_stale_30d / totalProj) : null;
  }

  // Demand priority set + staleness (60d — demands can legitimately sit in qualification longer)
  var demTest = new GlideRecord("pm_demand");
  if (demTest.isValid()) {
    var gaDemTotal = new GlideAggregate("pm_demand");
    gaDemTotal.addAggregate("COUNT"); gaDemTotal.query();
    var totalDem = 0;
    if (gaDemTotal.next()) { totalDem = parseInt(gaDemTotal.getAggregate("COUNT"), 10); }

    var gaDemPri = new GlideAggregate("pm_demand");
    gaDemPri.addAggregate("COUNT");
    gaDemPri.addEncodedQuery("priorityISNOTEMPTY");
    gaDemPri.query();
    var priDem = 0;
    if (gaDemPri.next()) { priDem = parseInt(gaDemPri.getAggregate("COUNT"), 10); }
    result.demand_priority_set_pct = totalDem > 0
      ? Math.round(100 * priDem / totalDem) : null;

    var gaDemStale = new GlideAggregate("pm_demand");
    gaDemStale.addAggregate("COUNT");
    gaDemStale.addEncodedQuery("sys_updated_on<" + cutoff60Str + "^stateNOT INclosed,cancelled,rejected");
    gaDemStale.query();
    result.demands_stale_60d = 0;
    if (gaDemStale.next()) { result.demands_stale_60d = parseInt(gaDemStale.getAggregate("COUNT"), 10); }
    result.demands_stale_60d_pct = totalDem > 0
      ? Math.round(100 * result.demands_stale_60d / totalDem) : null;
  }

  // Resource plan named resource %
  var rpTest = new GlideRecord("pm_resource_plan");
  if (rpTest.isValid()) {
    var gaRpTotal = new GlideAggregate("pm_resource_plan");
    gaRpTotal.addAggregate("COUNT"); gaRpTotal.query();
    var totalRp = 0;
    if (gaRpTotal.next()) { totalRp = parseInt(gaRpTotal.getAggregate("COUNT"), 10); }

    var gaRpNamed = new GlideAggregate("pm_resource_plan");
    gaRpNamed.addAggregate("COUNT");
    gaRpNamed.addEncodedQuery("resourceISNOTEMPTY");
    gaRpNamed.query();
    var namedRp = 0;
    if (gaRpNamed.next()) { namedRp = parseInt(gaRpNamed.getAggregate("COUNT"), 10); }
    result.resource_plan_named_pct = totalRp > 0
      ? Math.round(100 * namedRp / totalRp) : null;
  }

  gs.print(JSON.stringify(result));
  gs.print("// SPM sidecar: name=" + SIDECAR_NAME + " status=COMPLETE");
})();

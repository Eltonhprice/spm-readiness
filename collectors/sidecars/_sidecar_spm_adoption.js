(function() {
  var SIDECAR_NAME = "_sidecar_spm_adoption";

  var result = {
    plugins: {},
    roles: {},
    spm_workspace_active: false,
    active_users_90d: {}
  };

  // Plugin activation check
  var pluginIds = [
    "com.snc.sdlc.ppm_core",
    "com.snc.rm",
    "com.snc.financial_mgmt",
    "com.snc.agile",
    "com.snc.apm",
    "com.snc.innovation_mgmt"
  ];
  var pm = GlidePluginManager;
  for (var i = 0; i < pluginIds.length; i++) {
    try {
      result.plugins[pluginIds[i]] = pm.isActive(pluginIds[i]);
    } catch(e) {
      result.plugins[pluginIds[i]] = false;
    }
  }

  // SPM workspace check
  try {
    var wxGr = new GlideRecord("sys_ux_app_config");
    if (wxGr.isValid()) {
      wxGr.addEncodedQuery("sys_idLIKEspm^ORnameLIKEspm");
      wxGr.setLimit(1);
      wxGr.query();
      result.spm_workspace_active = wxGr.next();
    }
  } catch(e) { result.spm_workspace_active = false; }

  // Role counts via GlideAggregate
  var spmRoles = [
    "portfolio_manager", "project_manager", "resource_manager",
    "financial_analyst", "it_demand_manager"
  ];
  var uhrTable = "sys_user_has_role";
  var uhrTest = new GlideRecord(uhrTable);
  if (uhrTest.isValid()) {
    for (var r = 0; r < spmRoles.length; r++) {
      var ga = new GlideAggregate(uhrTable);
      ga.addAggregate("COUNT");
      ga.addEncodedQuery("role.nameLIKE" + spmRoles[r] + "^inherited=false^user.active=true");
      ga.query();
      result.roles[spmRoles[r]] = 0;
      if (ga.next()) { result.roles[spmRoles[r]] = parseInt(ga.getAggregate("COUNT"), 10); }
    }
  }

  // Active users last 90 days by key SPM table
  var auTables = ["pm_demand", "pm_project", "pm_resource_plan", "rm_story", "apm_appl_now"];
  var cutoff = new GlideDateTime();
  cutoff.addSeconds(-90 * 86400);
  var cutoffStr = cutoff.getDisplayValue();

  for (var t = 0; t < auTables.length; t++) {
    var tName = auTables[t];
    var tTest = new GlideRecord(tName);
    if (!tTest.isValid()) { result.active_users_90d[tName] = null; continue; }
    var aga = new GlideAggregate(tName);
    aga.addAggregate("COUNT", "sys_updated_by");
    aga.groupBy("sys_updated_by");
    aga.addEncodedQuery("sys_updated_on>=" + cutoffStr);
    aga.query();
    var userCount = 0;
    while (aga.next()) { userCount++; }
    result.active_users_90d[tName] = userCount;
  }

  gs.print(JSON.stringify(result));
  gs.print("// SPM sidecar: name=" + SIDECAR_NAME + " status=COMPLETE");
})();

// ServiceNow Scripts-Background — cmdb_ci_service collector
// Run in Global scope
var fields = [
  "sys_id", "name", "sys_class_name", "operational_status",
  "service_classification", "managed_by_group", "owned_by",
  "portfolio_status", "sys_updated_on"
];

var gr = new GlideRecord("cmdb_ci_service");
gr.orderBy("sys_updated_on");
gr.setLimit(1000);
gr.query();

var out = [];
while (gr.next()) {
  var rec = {};
  for (var i = 0; i < fields.length; i++) {
    var f = fields[i];
    rec[f] = gr.getValue(f) || "";
  }
  out.push(rec);
}

gs.print(JSON.stringify(out));
// status=OK total=' + out.length

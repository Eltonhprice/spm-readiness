// ServiceNow Scripts-Background — cmdb_ci collector
// Run in Global scope
var CHUNK_INDEX = 0;
var CHUNK_SIZE  = 500;

var fields = [
  "sys_id", "name", "sys_class_name", "operational_status",
  "managed_by", "owned_by", "support_group", "environment",
  "discovery_source", "install_status", "sys_updated_on"
];

var gr = new GlideRecord("cmdb_ci");
gr.addQuery("install_status", "!=", "7"); // exclude retired
gr.orderBy("sys_updated_on");
gr.chooseWindow(CHUNK_INDEX * CHUNK_SIZE, (CHUNK_INDEX + 1) * CHUNK_SIZE);
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
// status=OK chunk=0 total_in_chunk=' + out.length

// ServiceNow Scripts-Background — cmdb_rel_ci collector (counts + sample)
// Run in Global scope
var countGr = new GlideAggregate("cmdb_rel_ci");
countGr.addAggregate("COUNT");
countGr.query();
var total_relationships = 0;
if (countGr.next()) {
  total_relationships = parseInt(countGr.getAggregate("COUNT")) || 0;
}

// Unique parent CIs in relationships (sample 500)
var parentSet = {};
var gr = new GlideRecord("cmdb_rel_ci");
gr.setLimit(500);
gr.query();
while (gr.next()) {
  var p = gr.getValue("parent");
  if (p) parentSet[p] = true;
}

gs.print(JSON.stringify({
  total_relationships: total_relationships,
  sampled_parent_count: Object.keys(parentSet).length
}));
// status=OK

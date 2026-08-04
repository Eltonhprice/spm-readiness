(function() {
  var TABLE      = "pm_resource_allocation";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "resource_plan", "resource", "start_date", "end_date",
    "allocated_hours", "actual_hours", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE);
  ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER);
  ga.query();
  var total = 0;
  if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }

  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true);
  gr.query();

  var rows = [];
  while (gr.next()) {
    var row = {};
    for (var i = 0; i < FIELDS.length; i++) { row[FIELDS[i]] = gr.getValue(FIELDS[i]); }
    rows.push(row);
  }
  gs.print(JSON.stringify(rows));
  var status = (start + rows.length < total) ? "MORE_RECORDS_EXIST" : "COMPLETE";
  gs.print("// SPM collector: table=" + TABLE + " chunk=" + CHUNK_INDEX +
           " rows=" + rows.length + " total=" + total + " status=" + status);
})();

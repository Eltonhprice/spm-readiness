# SPM Readiness Skill — Implementation Plan Part 2: Collectors

> **For agentic workers:** Use `subagent-driven-development` or `executing-plans` to implement task-by-task.

**Goal:** Write all 21 ServiceNow background script collectors and 2 sidecar scripts. These are the `.js` files a consultant pastes into Scripts-Background to pull SPM data from a client instance.

**Architecture:** All collectors follow the same IIFE pattern. Each outputs a JSON array (or object for sidecars) plus a footer comment line. Chunked output is supported for large tables.

**Tech Stack:** ServiceNow server-side JavaScript (GlideRecord, GlideAggregate, GlidePluginManager). No external libraries.

## Global Constraints

- All scripts are IIFEs: `(function() { ... })();`
- `isValid()` guard on every table — print empty result + `TABLE_NOT_FOUND` status if absent
- Footer format: `// SPM collector: table=X chunk=N rows=N total=N status=COMPLETE|MORE_RECORDS_EXIST`
- Sidecar footer format: `// SPM sidecar: name=X status=COMPLETE|TABLE_NOT_FOUND`
- `CHUNK_SIZE = 5000` for all table collectors
- Saved as `<table>.txt` in `spm-inputs/<client>/<domain>/`
- Chunked files saved as `<table>.001.txt`, `<table>.002.txt`, etc.

---

## Collector Template

Every table collector follows this exact template. Study it once — all 21 collectors are instances of it with different TABLE/FILTER/FIELDS values.

```javascript
(function() {
  var TABLE      = "pm_demand";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;  // increment for chunks 1, 2, ...
  var FILTER     = "active=true";   // encoded query string, or "" for no filter
  var FIELDS     = [
    "sys_id", "state", "category", "assigned_to", "project",
    "sys_created_on", "priority", "short_description"
  ];

  // Guard: table must exist
  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE +
             " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }

  // Count total matching records
  var ga = new GlideAggregate(TABLE);
  ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER);
  ga.query();
  var total = 0;
  if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }

  // Window query
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true);
  gr.query();

  var rows = [];
  while (gr.next()) {
    var row = {};
    for (var i = 0; i < FIELDS.length; i++) {
      row[FIELDS[i]] = gr.getValue(FIELDS[i]);
    }
    rows.push(row);
  }

  gs.print(JSON.stringify(rows));

  var status = (start + rows.length < total) ? "MORE_RECORDS_EXIST" : "COMPLETE";
  gs.print("// SPM collector: table=" + TABLE +
           " chunk=" + CHUNK_INDEX +
           " rows=" + rows.length +
           " total=" + total +
           " status=" + status);
})();
```

---

## Task 5: Demand Collectors

**Files:**
- Create: `collectors/demand/pm_demand.js`
- Create: `collectors/demand/pm_demand_category.js`

**Interfaces:**
- Produces: `.txt` files saved to `spm-inputs/<client>/demand/`

- [ ] **Step 1: Write `collectors/demand/pm_demand.js`**

```javascript
(function() {
  var TABLE      = "pm_demand";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "category",
    "assigned_to", "project", "sys_created_on", "priority",
    "business_justification", "requested_by"
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
```

- [ ] **Step 2: Write `collectors/demand/pm_demand_category.js`**

```javascript
(function() {
  var TABLE      = "pm_demand_category";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = ["sys_id", "name", "active", "parent"];

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
```

- [ ] **Step 3: Commit**

```bash
git add collectors/demand/
git commit -m "feat: add demand collectors (pm_demand, pm_demand_category)"
```

---

## Task 6: PPM Collectors

**Files:**
- Create: `collectors/ppm/pm_project.js`
- Create: `collectors/ppm/pm_project_task.js`
- Create: `collectors/ppm/pm_program.js`

- [ ] **Step 1: Write `collectors/ppm/pm_project.js`**

```javascript
(function() {
  var TABLE      = "pm_project";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "phase", "program",
    "assigned_to", "business_owner", "start_date", "end_date",
    "actual_start_date", "actual_end_date", "sys_created_on",
    "percent_complete", "priority", "sys_updated_on"
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
```

- [ ] **Step 2: Write `collectors/ppm/pm_project_task.js`**

```javascript
(function() {
  var TABLE      = "pm_project_task";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "project",
    "assigned_to", "start_date", "end_date", "percent_complete",
    "sys_created_on"
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
```

- [ ] **Step 3: Write `collectors/ppm/pm_program.js`**

```javascript
(function() {
  var TABLE      = "pm_program";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "assigned_to",
    "start_date", "end_date", "sys_created_on"
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
```

- [ ] **Step 4: Commit**

```bash
git add collectors/ppm/
git commit -m "feat: add PPM collectors (pm_project, pm_project_task, pm_program)"
```

---

## Task 7: Resource + Financial Collectors

**Files:**
- Create: `collectors/resource/pm_resource_plan.js`
- Create: `collectors/resource/pm_resource_allocation.js`
- Create: `collectors/financial/pm_project_financials.js`
- Create: `collectors/financial/pm_cost_plan.js`
- Create: `collectors/financial/pm_budget_plan.js`

- [ ] **Step 1: Write `collectors/resource/pm_resource_plan.js`**

```javascript
(function() {
  var TABLE      = "pm_resource_plan";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "project", "resource", "role", "state",
    "planned_hours", "actual_hours", "available_hours",
    "start_date", "end_date", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 2: Write `collectors/resource/pm_resource_allocation.js`**

```javascript
(function() {
  var TABLE      = "pm_resource_allocation";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "resource_plan", "resource", "start_date",
    "end_date", "allocated_hours", "actual_hours", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 3: Write `collectors/financial/pm_project_financials.js`**

```javascript
(function() {
  var TABLE      = "pm_project_financials";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "project", "planned_cost", "actual_cost",
    "planned_benefit", "actual_benefit", "currency", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 4: Write `collectors/financial/pm_cost_plan.js`**

```javascript
(function() {
  var TABLE      = "pm_cost_plan";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "project", "cost_type", "planned_cost",
    "actual_cost", "state", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 5: Write `collectors/financial/pm_budget_plan.js`**

```javascript
(function() {
  var TABLE      = "pm_budget_plan";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "project", "budget_amount", "actual_amount",
    "state", "fiscal_year", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 6: Commit**

```bash
git add collectors/resource/ collectors/financial/
git commit -m "feat: add resource and financial collectors"
```

---

## Task 8: Agile + APM + Innovation Collectors

**Files:**
- Create: `collectors/agile/rm_story.js`
- Create: `collectors/agile/rm_sprint.js`
- Create: `collectors/agile/rm_team.js`
- Create: `collectors/apm/apm_appl_now.js`
- Create: `collectors/apm/apm_appl_lifecycle.js`
- Create: `collectors/innovation/innovation_idea.js`
- Create: `collectors/innovation/innovation_challenge.js`

- [ ] **Step 1: Write `collectors/agile/rm_story.js`**

```javascript
(function() {
  var TABLE      = "rm_story";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "sprint", "team",
    "story_points", "assigned_to", "sys_created_on", "sys_updated_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 2: Write `collectors/agile/rm_sprint.js`**

```javascript
(function() {
  var TABLE      = "rm_sprint";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "team",
    "start_date", "end_date", "planned_points", "completed_points",
    "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 3: Write `collectors/agile/rm_team.js`**

```javascript
(function() {
  var TABLE      = "rm_team";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "name", "team_type", "active",
    "manager", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 4: Write `collectors/apm/apm_appl_now.js`**

```javascript
(function() {
  var TABLE      = "apm_appl_now";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "name", "lifecycle_stage", "business_owner",
    "cmdb_ci", "vendor", "install_status", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 5: Write `collectors/apm/apm_appl_lifecycle.js`**

```javascript
(function() {
  var TABLE      = "apm_appl_lifecycle";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "application", "stage", "target_retirement_date",
    "migration_path", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 6: Write `collectors/innovation/innovation_idea.js`**

```javascript
(function() {
  var TABLE      = "innovation_idea";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "category",
    "assigned_to", "demand", "project", "challenge",
    "sys_created_on", "sys_updated_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 7: Write `collectors/innovation/innovation_challenge.js`**

```javascript
(function() {
  var TABLE      = "innovation_challenge";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "short_description", "state", "assigned_to",
    "start_date", "end_date", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 8: Commit**

```bash
git add collectors/agile/ collectors/apm/ collectors/innovation/
git commit -m "feat: add agile, APM, and innovation collectors"
```

---

## Task 9: Governance + Scoring + PA Collectors

**Files:**
- Create: `collectors/governance/timesheet_period.js`
- Create: `collectors/governance/timesheet_entry.js`
- Create: `collectors/governance/pm_project_status.js`
- Create: `collectors/governance/sysapproval_approver.js`
- Create: `collectors/scoring/pm_scoring_criterion.js`
- Create: `collectors/scoring/pm_portfolio_score.js`
- Create: `collectors/pa/pa_scorecard.js`

- [ ] **Step 1: Write `collectors/governance/timesheet_period.js`**

```javascript
(function() {
  var TABLE      = "timesheet_period";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "state", "start_date", "end_date",
    "name", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 2: Write `collectors/governance/timesheet_entry.js`**

```javascript
(function() {
  var TABLE      = "timesheet_entry";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "timesheet", "task", "hours",
    "state", "user", "work_date", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 3: Write `collectors/governance/pm_project_status.js`**

```javascript
(function() {
  var TABLE      = "pm_project_status";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "project", "overall_status", "schedule_status",
    "cost_status", "risk_status", "sys_created_on", "created_by"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 4: Write `collectors/governance/sysapproval_approver.js`**

Note: filtered to SPM source tables only to avoid pulling the entire approval table.

```javascript
(function() {
  var TABLE      = "sysapproval_approver";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  // Filter to SPM tables only — avoids pulling millions of ITSM approvals
  var FILTER     = "source_tableINpm_demand,pm_project,pm_program,pm_cost_plan,pm_budget_plan";
  var FIELDS     = [
    "sys_id", "source_id", "source_table", "approver",
    "state", "sys_created_on", "sys_updated_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 5: Write `collectors/scoring/pm_scoring_criterion.js`**

```javascript
(function() {
  var TABLE      = "pm_scoring_criterion";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "name", "active", "weight",
    "scoring_model", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 6: Write `collectors/scoring/pm_portfolio_score.js`**

```javascript
(function() {
  var TABLE      = "pm_portfolio_score";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  var FILTER     = "";
  var FIELDS     = [
    "sys_id", "source_id", "source_table", "score",
    "scoring_model", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 7: Write `collectors/pa/pa_scorecard.js`**

Filtered to SPM-related scorecards only.

```javascript
(function() {
  var TABLE      = "pa_scorecard";
  var CHUNK_SIZE = 5000;
  var CHUNK_INDEX = 0;
  // Filter to SPM-related scorecards by indicator source table prefix
  var FILTER     = "indicator_source.tableLIKEpm_^ORindicator_source.tableLIKErm_";
  var FIELDS     = [
    "sys_id", "name", "indicator_source", "active",
    "owner", "sys_created_on"
  ];

  var test = new GlideRecord(TABLE);
  if (!test.isValid()) {
    gs.print("[]");
    gs.print("// SPM collector: table=" + TABLE + " chunk=0 rows=0 total=0 status=TABLE_NOT_FOUND");
    return;
  }
  var ga = new GlideAggregate(TABLE); ga.addAggregate("COUNT");
  if (FILTER) ga.addEncodedQuery(FILTER); ga.query();
  var total = 0; if (ga.next()) { total = parseInt(ga.getAggregate("COUNT"), 10); }
  var gr = new GlideRecord(TABLE);
  if (FILTER) gr.addEncodedQuery(FILTER);
  var start = CHUNK_INDEX * CHUNK_SIZE;
  gr.chooseWindow(start, start + CHUNK_SIZE, true); gr.query();
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
```

- [ ] **Step 8: Commit**

```bash
git add collectors/governance/ collectors/scoring/ collectors/pa/
git commit -m "feat: add governance, scoring, and PA collectors"
```

---

## Task 10: Sidecar Scripts

**Files:**
- Create: `collectors/sidecars/_sidecar_spm_adoption.js`
- Create: `collectors/sidecars/_sidecar_portfolio_health.js`

- [ ] **Step 1: Write `collectors/sidecars/_sidecar_spm_adoption.js`**

```javascript
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
```

- [ ] **Step 2: Write `collectors/sidecars/_sidecar_portfolio_health.js`**

```javascript
(function() {
  var SIDECAR_NAME = "_sidecar_portfolio_health";

  var result = {
    project_completeness_pct: null,
    demand_priority_set_pct: null,
    resource_plan_named_pct: null,
    projects_stale_90d: null,
    projects_stale_90d_pct: null,
    demands_stale_90d: null,
    demands_stale_90d_pct: null
  };

  var cutoff = new GlideDateTime();
  cutoff.addSeconds(-90 * 86400);
  var cutoffStr = cutoff.getDisplayValue();

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

    // Stale projects
    var gaStale = new GlideAggregate("pm_project");
    gaStale.addAggregate("COUNT");
    gaStale.addEncodedQuery("sys_updated_on<" + cutoffStr + "^stateNOT INclosed,cancelled");
    gaStale.query();
    result.projects_stale_90d = 0;
    if (gaStale.next()) { result.projects_stale_90d = parseInt(gaStale.getAggregate("COUNT"), 10); }
    result.projects_stale_90d_pct = totalProj > 0
      ? Math.round(100 * result.projects_stale_90d / totalProj) : null;
  }

  // Demand priority set
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

    // Stale demands
    var gaDemStale = new GlideAggregate("pm_demand");
    gaDemStale.addAggregate("COUNT");
    gaDemStale.addEncodedQuery("sys_updated_on<" + cutoffStr + "^stateNOT INclosed,cancelled");
    gaDemStale.query();
    result.demands_stale_90d = 0;
    if (gaDemStale.next()) { result.demands_stale_90d = parseInt(gaDemStale.getAggregate("COUNT"), 10); }
    result.demands_stale_90d_pct = totalDem > 0
      ? Math.round(100 * result.demands_stale_90d / totalDem) : null;
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
```

- [ ] **Step 3: Commit**

```bash
git add collectors/sidecars/
git commit -m "feat: add spm_adoption and portfolio_health sidecar scripts"
```

---

## Part 2 Complete

Verify all collector files exist:

```powershell
$root = "$env:USERPROFILE\.claude\skills\spm-readiness\collectors"
Get-ChildItem $root -Recurse -Filter "*.js" | Select-Object Name | Sort-Object Name
```

Expected: 23 files total (21 table collectors + 2 sidecars).

**Proceed to:** `plan-part3-python-core.md`

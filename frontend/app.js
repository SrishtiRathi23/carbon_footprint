/*
  GreenRoute frontend logic -- vanilla JavaScript, no frameworks.
  The frontend NEVER talks to Google APIs directly; it only calls this
  project's own backend, which holds all secret keys.

  Set BACKEND_URL to your deployed Cloud Run URL after deployment.
  For local development it points at the local FastAPI server.
*/
"use strict";

var BACKEND_URL = "https://greenroute-api-rwhbntkrla-el.a.run.app";

// Friendly display names + labels for the four commute modes.
var MODE_LABELS = {
  driving: "Driving",
  transit: "Transit",
  walking: "Walking",
  cycling: "Cycling"
};

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------
function el(id) {
  return document.getElementById(id);
}

function setStatus(node, message, isError) {
  node.textContent = message;
  node.classList.toggle("error", Boolean(isError));
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) {
    return "duration n/a";
  }
  var mins = Math.round(seconds / 60);
  if (mins < 60) {
    return mins + " min";
  }
  var h = Math.floor(mins / 60);
  var m = mins % 60;
  return h + " h " + m + " min";
}

async function postJson(path, body) {
  var response = await fetch(BACKEND_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  var data = await response.json().catch(function () {
    return {};
  });
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function getJson(path) {
  var response = await fetch(BACKEND_URL + path);
  if (!response.ok) {
    throw new Error("Request failed");
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Tabs (accessible: arrow keys + click, roving tabindex)
// ---------------------------------------------------------------------------
function setupTabs() {
  var tabs = [el("tab-commute"), el("tab-appliance")];
  var panels = { "tab-commute": el("panel-commute"), "tab-appliance": el("panel-appliance") };

  function activate(tab) {
    tabs.forEach(function (t) {
      var selected = t === tab;
      t.setAttribute("aria-selected", String(selected));
      t.tabIndex = selected ? 0 : -1;
      panels[t.id].hidden = !selected;
    });
    tab.focus();
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () {
      activate(tab);
    });
    tab.addEventListener("keydown", function (event) {
      if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
        event.preventDefault();
        var dir = event.key === "ArrowRight" ? 1 : -1;
        var next = (index + dir + tabs.length) % tabs.length;
        activate(tabs[next]);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Weekly stats
// ---------------------------------------------------------------------------
async function loadWeeklyStats() {
  try {
    var stats = await getJson("/api/stats/weekly");
    el("stat-combined").textContent = stats.combined_co2_kg.toFixed(2);
    el("stat-saved").textContent = stats.commute_co2_saved_kg.toFixed(2);
    el("stat-appliance").textContent = stats.appliance_co2_emitted_kg.toFixed(2);
  } catch (err) {
    // Stats are non-critical; leave placeholders rather than blocking the app.
    el("stat-combined").textContent = "--";
  }
}

// ---------------------------------------------------------------------------
// Commute comparison
// ---------------------------------------------------------------------------
function renderResults(data) {
  var list = el("commute-results");
  list.textContent = "";

  data.options.forEach(function (option) {
    var li = document.createElement("li");
    li.className = "card";
    if (option.recommended) {
      li.classList.add("recommended");
    }
    if (!option.viable) {
      li.classList.add("not-viable");
    }

    var mode = document.createElement("div");
    mode.className = "card-mode";
    mode.textContent = MODE_LABELS[option.mode] || option.mode;
    if (option.recommended) {
      var badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "Recommended";
      mode.appendChild(badge);
    }

    var meta = document.createElement("div");
    meta.className = "card-meta";
    meta.textContent = option.distance_km + " km, " + formatDuration(option.duration_seconds);

    var co2 = document.createElement("div");
    co2.className = "card-co2";
    co2.innerHTML =
      option.co2_emitted_kg.toFixed(2) +
      " kg<small>CO2 (saves " +
      option.co2_saved_vs_driving_kg.toFixed(2) +
      " vs driving)</small>";

    li.appendChild(mode);
    li.appendChild(co2);
    li.appendChild(meta);

    if (!option.viable) {
      var note = document.createElement("div");
      note.className = "card-note";
      note.textContent = "Note: not recommended for this distance.";
      li.appendChild(note);
    }

    // Log this choice when selected.
    var logBtn = document.createElement("button");
    logBtn.type = "button";
    logBtn.className = "btn-secondary";
    logBtn.textContent = "+ Log this trip";
    logBtn.setAttribute(
      "aria-label",
      "Log " + (MODE_LABELS[option.mode] || option.mode) + " as your chosen trip"
    );
    logBtn.addEventListener("click", function () {
      logCommute(data, option, logBtn);
    });
    var actionWrap = document.createElement("div");
    actionWrap.className = "card-note";
    actionWrap.appendChild(logBtn);
    li.appendChild(actionWrap);

    list.appendChild(li);
  });
}

async function logCommute(data, option, button) {
  button.disabled = true;
  try {
    await postJson("/api/log/commute", {
      start: data.start,
      destination: data.destination,
      mode: option.mode,
      distance_km: option.distance_km,
      co2_emitted: option.co2_emitted_kg,
      co2_saved_vs_driving: option.co2_saved_vs_driving_kg
    });
    button.textContent = "✓ Logged";
    await loadWeeklyStats();
  } catch (err) {
    button.disabled = false;
    button.textContent = "+ Log this trip";
    setStatus(el("commute-status"), "Could not log trip: " + err.message, true);
  }
}

var lastComparison = null;

var MODE_COLORS = {
  driving: "#d98b2b",
  transit: "#65a30d",
  walking: "#4d7c0f",
  cycling: "#84cc16"
};

function renderChart(data) {
  var chart = el("commute-chart");
  chart.textContent = "";
  var options = data.options || [];
  var maxCo2 = Math.max.apply(null, options.map(function (o) { return o.co2_emitted_kg; }).concat([0.001]));

  var heading = document.createElement("div");
  heading.className = "chart-title";
  heading.textContent = "CO2 by mode (kg)";
  chart.appendChild(heading);

  options.forEach(function (option) {
    var row = document.createElement("div");
    row.className = "bar-row";

    var label = document.createElement("span");
    label.className = "bar-label";
    label.textContent = MODE_LABELS[option.mode] || option.mode;

    var track = document.createElement("span");
    track.className = "bar-track";
    var fill = document.createElement("span");
    fill.className = "bar-fill";
    var pct = Math.round((option.co2_emitted_kg / maxCo2) * 100);
    fill.style.width = Math.max(pct, 2) + "%";
    fill.style.background = MODE_COLORS[option.mode] || "#65a30d";
    track.appendChild(fill);

    var value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = option.co2_emitted_kg.toFixed(2);

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(value);
    chart.appendChild(row);
  });
}

function setupChips() {
  var chips = document.querySelectorAll(".chip");
  Array.prototype.forEach.call(chips, function (chip) {
    chip.addEventListener("click", function () {
      el("start").value = chip.getAttribute("data-start");
      el("destination").value = chip.getAttribute("data-dest");
      el("commute-form").requestSubmit
        ? el("commute-form").requestSubmit()
        : el("commute-form").dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });
}

function setupCommuteForm() {
  el("commute-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var status = el("commute-status");
    var insight = el("commute-insight");
    el("commute-results").textContent = "";
    el("commute-chart").textContent = "";
    insight.textContent = "";
    el("followup").hidden = true;
    el("ask-answer").textContent = "";
    setStatus(status, "Comparing routes...", false);

    try {
      var data = await postJson("/api/compare", {
        start: el("start").value,
        destination: el("destination").value
      });
      lastComparison = data;
      setStatus(status, "", false);
      insight.textContent = data.tip || "";
      renderChart(data);
      renderResults(data);
      el("followup").hidden = false;
    } catch (err) {
      setStatus(status, err.message, true);
    }
  });
}

function setupFollowup() {
  el("ask-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var status = el("ask-status");
    var answer = el("ask-answer");
    var question = el("ask-input").value.trim();
    if (!question) {
      setStatus(status, "Please type a question.", true);
      return;
    }
    if (!lastComparison) {
      setStatus(status, "Run a comparison first.", true);
      return;
    }
    setStatus(status, "Thinking...", false);
    answer.textContent = "";
    try {
      var data = await postJson("/api/ask", {
        question: question,
        context: { options: lastComparison.options }
      });
      setStatus(status, "", false);
      answer.textContent = data.answer || "";
    } catch (err) {
      setStatus(status, err.message, true);
    }
  });
}

// ---------------------------------------------------------------------------
// Appliance estimator
// ---------------------------------------------------------------------------
var lastApplianceEstimate = null;

function renderApplianceInputs(inputType) {
  var container = el("appliance-inputs");
  container.textContent = "";

  function numberField(id, labelText, min, step) {
    var field = document.createElement("div");
    field.className = "field";
    var label = document.createElement("label");
    label.setAttribute("for", id);
    label.textContent = labelText;
    var input = document.createElement("input");
    input.type = "number";
    input.id = id;
    input.min = String(min);
    input.step = String(step || 1);
    input.required = true;
    input.setAttribute("aria-required", "true");
    field.appendChild(label);
    field.appendChild(input);
    container.appendChild(field);
  }

  if (inputType === "hours_per_day") {
    numberField("usage-hours", "Hours per day", 0, 0.5);
  } else if (inputType === "minutes_per_day") {
    numberField("usage-minutes", "Minutes per day", 0, 1);
  } else if (inputType === "loads_per_week") {
    numberField("usage-loads", "Loads per week", 0, 1);
  } else if (inputType === "hours_per_day_x_count") {
    numberField("usage-hours", "Hours per day (per bulb)", 0, 0.5);
    numberField("usage-count", "Number of bulbs", 1, 1);
  } else if (inputType === "size") {
    var field = document.createElement("div");
    field.className = "field";
    var label = document.createElement("label");
    label.setAttribute("for", "usage-size");
    label.textContent = "Size";
    var select = document.createElement("select");
    select.id = "usage-size";
    select.required = true;
    ["small", "medium", "large"].forEach(function (size) {
      var opt = document.createElement("option");
      opt.value = size;
      opt.textContent = size.charAt(0).toUpperCase() + size.slice(1);
      select.appendChild(opt);
    });
    field.appendChild(label);
    field.appendChild(select);
    container.appendChild(field);
  }
}

function collectApplianceParams(inputType) {
  if (inputType === "hours_per_day") {
    return { hours_per_day: parseFloat(el("usage-hours").value) };
  }
  if (inputType === "minutes_per_day") {
    return { minutes_per_day: parseFloat(el("usage-minutes").value) };
  }
  if (inputType === "loads_per_week") {
    return { loads_per_week: parseFloat(el("usage-loads").value) };
  }
  if (inputType === "hours_per_day_x_count") {
    return {
      hours_per_day: parseFloat(el("usage-hours").value),
      count: parseInt(el("usage-count").value, 10)
    };
  }
  if (inputType === "size") {
    return { size: el("usage-size").value };
  }
  return {};
}

async function setupApplianceForm() {
  var select = el("appliance");
  var inputTypes = {};

  try {
    var catalogue = await getJson("/api/appliances");
    catalogue.appliances.forEach(function (item) {
      inputTypes[item.key] = item.input;
      var opt = document.createElement("option");
      opt.value = item.key;
      opt.textContent = item.label;
      select.appendChild(opt);
    });
  } catch (err) {
    setStatus(el("appliance-status"), "Could not load appliance list.", true);
    return;
  }

  select.addEventListener("change", function () {
    el("appliance-result").textContent = "";
    if (select.value) {
      renderApplianceInputs(inputTypes[select.value]);
    } else {
      el("appliance-inputs").textContent = "";
    }
  });

  el("appliance-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    var status = el("appliance-status");
    if (!select.value) {
      setStatus(status, "Please select an appliance.", true);
      return;
    }
    setStatus(status, "Calculating...", false);
    try {
      var params = collectApplianceParams(inputTypes[select.value]);
      var data = await postJson("/api/appliances/estimate", {
        appliance: select.value,
        params: params
      });
      lastApplianceEstimate = { appliance: select.value, params: params };
      setStatus(status, "", false);
      renderApplianceResult(data);
    } catch (err) {
      setStatus(status, err.message, true);
    }
  });
}

function renderApplianceResult(data) {
  var container = el("appliance-result");
  container.innerHTML =
    '<div class="result-box"><dl>' +
    "<dt>Appliance</dt><dd>" + data.label + "</dd>" +
    "<dt>Daily energy</dt><dd>" + data.daily_kwh + " kWh</dd>" +
    "<dt>Daily CO2</dt><dd>" + data.co2_emitted_kg.toFixed(2) + " kg</dd>" +
    "<dt>Weekly CO2 (typical day x 7)</dt><dd>" + data.co2_emitted_weekly_kg.toFixed(2) + " kg</dd>" +
    "</dl></div>";

  var logBtn = document.createElement("button");
  logBtn.type = "button";
  logBtn.className = "btn-secondary";
  logBtn.textContent = "+ Log this appliance";
  logBtn.addEventListener("click", function () {
    logAppliance(logBtn);
  });
  container.appendChild(logBtn);
}

async function logAppliance(button) {
  if (!lastApplianceEstimate) {
    return;
  }
  button.disabled = true;
  try {
    await postJson("/api/log/appliance", lastApplianceEstimate);
    button.textContent = "✓ Logged";
    await loadWeeklyStats();
  } catch (err) {
    button.disabled = false;
    button.textContent = "+ Log this appliance";
    setStatus(el("appliance-status"), "Could not log: " + err.message, true);
  }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  setupTabs();
  setupCommuteForm();
  setupChips();
  setupFollowup();
  setupApplianceForm();
  loadWeeklyStats();
});

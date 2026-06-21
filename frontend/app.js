/*
  GreenRoute frontend logic -- vanilla JavaScript, no frameworks.
  The frontend NEVER talks to Google APIs directly; it only calls this
  project's own backend, which holds all secret keys.

  Set BACKEND_URL to your deployed Cloud Run URL after deployment.
  For local development it points at the local FastAPI server.

  Session: a UUID is generated on first load and stored in localStorage.
  It is sent with every log request and used to filter weekly stats so each
  browser sees its own totals. No login, no credentials, no auth -- just an
  opaque filter key.
*/
"use strict";

// ---------------------------------------------------------------------------
// Anonymous per-browser session (Fix #18)
// ---------------------------------------------------------------------------
function generateSessionId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for browsers without crypto.randomUUID (very rare in 2024+).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getSessionId() {
  let id = localStorage.getItem("gr_session_id");
  if (!id) {
    id = generateSessionId();
    localStorage.setItem("gr_session_id", id);
  }
  return id;
}

const BACKEND_URL = "https://greenroute-api-rwhbntkrla-el.a.run.app";
const SESSION_ID = getSessionId();

// Friendly display names for the four commute modes.
const MODE_LABELS = {
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
  const mins = Math.round(seconds / 60);
  if (mins < 60) {
    return mins + " min";
  }
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return h + " h " + m + " min";
}

async function postJson(path, body) {
  const response = await fetch(BACKEND_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(function () {
    return {};
  });
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

async function getJson(path) {
  const response = await fetch(BACKEND_URL + path);
  if (!response.ok) {
    throw new Error("Request failed");
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Tabs (accessible: arrow keys + click, roving tabindex)
// ---------------------------------------------------------------------------
function setupTabs() {
  const tabs = [el("tab-commute"), el("tab-appliance")];
  const panels = {
    "tab-commute": el("panel-commute"),
    "tab-appliance": el("panel-appliance")
  };

  function activate(tab) {
    tabs.forEach(function (t) {
      const selected = t === tab;
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
        const dir = event.key === "ArrowRight" ? 1 : -1;
        const next = (index + dir + tabs.length) % tabs.length;
        activate(tabs[next]);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Weekly stats -- filtered to this browser's session (Fix #18)
// Fix #17: show only the two clearly-labeled numbers; remove combined label.
// ---------------------------------------------------------------------------
async function loadWeeklyStats() {
  try {
    const stats = await getJson("/api/stats/weekly?session_id=" + SESSION_ID);
    el("stat-saved").textContent = stats.commute_co2_saved_kg.toFixed(2);
    el("stat-appliance").textContent = stats.appliance_co2_emitted_kg.toFixed(2);
  } catch (err) {
    // Stats are non-critical; leave placeholders rather than blocking the app.
    el("stat-saved").textContent = "--";
  }
}

// ---------------------------------------------------------------------------
// Commute comparison
// ---------------------------------------------------------------------------
const MODE_COLORS = {
  driving: "#d98b2b",
  transit: "#65a30d",
  walking: "#4d7c0f",
  cycling: "#84cc16"
};

// Fix #15: render an accessible visually-hidden table alongside the bar chart
// so screen reader users get the same comparison data as sighted users.
function renderChart(data) {
  const chart = el("commute-chart");
  chart.textContent = "";
  const options = data.options || [];
  const maxCo2 = Math.max.apply(
    null,
    options.map(function (o) { return o.co2_emitted_kg; }).concat([0.001])
  );

  const heading = document.createElement("div");
  heading.className = "chart-title";
  heading.textContent = "CO2 by mode (kg)";
  chart.appendChild(heading);

  // Visual bar chart (aria-hidden -- covered by the table below).
  const barsWrap = document.createElement("div");
  barsWrap.setAttribute("aria-hidden", "true");

  options.forEach(function (option) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const barLabel = document.createElement("span");
    barLabel.className = "bar-label";
    barLabel.textContent = MODE_LABELS[option.mode] || option.mode;

    const track = document.createElement("span");
    track.className = "bar-track";
    const fill = document.createElement("span");
    fill.className = "bar-fill";
    const pct = Math.round((option.co2_emitted_kg / maxCo2) * 100);
    fill.style.width = Math.max(pct, 2) + "%";
    fill.style.background = MODE_COLORS[option.mode] || "#65a30d";
    track.appendChild(fill);

    const value = document.createElement("span");
    value.className = "bar-value";
    value.textContent = option.co2_emitted_kg.toFixed(2);

    row.appendChild(barLabel);
    row.appendChild(track);
    row.appendChild(value);
    barsWrap.appendChild(row);
  });
  chart.appendChild(barsWrap);

  // Accessible table (visually hidden, read by screen readers).
  const srTable = document.createElement("table");
  srTable.className = "visually-hidden";
  srTable.setAttribute("aria-label", "CO2 by commute mode");

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  [
    { text: "Mode", scope: "col" },
    { text: "Distance (km)", scope: "col" },
    { text: "CO2 emitted (kg)", scope: "col" },
    { text: "CO2 saved vs driving (kg)", scope: "col" }
  ].forEach(function (col) {
    const th = document.createElement("th");
    th.scope = col.scope;
    th.textContent = col.text;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  srTable.appendChild(thead);

  const tbody = document.createElement("tbody");
  options.forEach(function (option) {
    const tr = document.createElement("tr");
    const tdMode = document.createElement("td");
    tdMode.textContent =
      (MODE_LABELS[option.mode] || option.mode) +
      (option.recommended ? " (recommended)" : "");
    const tdDist = document.createElement("td");
    tdDist.textContent = option.distance_km;
    const tdCo2 = document.createElement("td");
    tdCo2.textContent = option.co2_emitted_kg.toFixed(2);
    const tdSaved = document.createElement("td");
    tdSaved.textContent = option.co2_saved_vs_driving_kg.toFixed(2);
    tr.appendChild(tdMode);
    tr.appendChild(tdDist);
    tr.appendChild(tdCo2);
    tr.appendChild(tdSaved);
    tbody.appendChild(tr);
  });
  srTable.appendChild(tbody);
  chart.appendChild(srTable);
}

function renderResults(data) {
  const list = el("commute-results");
  list.textContent = "";

  data.options.forEach(function (option) {
    const li = document.createElement("li");
    li.className = "card";
    if (option.recommended) {
      li.classList.add("recommended");
    }
    if (!option.viable) {
      li.classList.add("not-viable");
    }

    const modeDiv = document.createElement("div");
    modeDiv.className = "card-mode";
    modeDiv.textContent = MODE_LABELS[option.mode] || option.mode;
    if (option.recommended) {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = "Recommended";
      modeDiv.appendChild(badge);
    }

    const meta = document.createElement("div");
    meta.className = "card-meta";
    meta.textContent =
      option.distance_km + " km, " + formatDuration(option.duration_seconds);

    // Build the CO2 cell using DOM API to avoid innerHTML string concatenation.
    const co2Div = document.createElement("div");
    co2Div.className = "card-co2";
    const co2Text = document.createTextNode(
      option.co2_emitted_kg.toFixed(2) + " kg"
    );
    const co2Small = document.createElement("small");
    co2Small.textContent =
      "CO2 (saves " + option.co2_saved_vs_driving_kg.toFixed(2) + " vs driving)";
    co2Div.appendChild(co2Text);
    co2Div.appendChild(co2Small);

    if (option.smartphone_charges_saved > 0) {
      const equivSmall = document.createElement("small");
      equivSmall.className = "equivalency";
      equivSmall.textContent = "Equivalent to " + option.smartphone_charges_saved + " smartphone charges saved";
      co2Div.appendChild(equivSmall);
    }

    li.appendChild(modeDiv);
    li.appendChild(co2Div);
    li.appendChild(meta);

    if (!option.viable) {
      const note = document.createElement("div");
      note.className = "card-note";
      note.textContent = "Note: not recommended for this distance.";
      li.appendChild(note);
    }

    // Log this choice when selected.
    const logBtn = document.createElement("button");
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
    const actionWrap = document.createElement("div");
    actionWrap.className = "card-note";
    actionWrap.appendChild(logBtn);
    li.appendChild(actionWrap);

    list.appendChild(li);
  });
}

// Fix #18: send SESSION_ID with every log request.
async function logCommute(data, option, button) {
  button.disabled = true;
  try {
    await postJson("/api/log/commute", {
      start: data.start,
      destination: data.destination,
      mode: option.mode,
      distance_km: option.distance_km,
      session_id: SESSION_ID
    });
    button.textContent = "\u2713 Logged";
    await loadWeeklyStats();
  } catch (err) {
    button.disabled = false;
    button.textContent = "+ Log this trip";
    setStatus(el("commute-status"), "Could not log trip: " + err.message, true);
  }
}

let lastComparison = null;

function setupChips() {
  const chips = document.querySelectorAll(".chip");
  Array.prototype.forEach.call(chips, function (chip) {
    chip.addEventListener("click", function () {
      el("start").value = chip.getAttribute("data-start");
      el("destination").value = chip.getAttribute("data-dest");
      if (el("commute-form").requestSubmit) {
        el("commute-form").requestSubmit();
      } else {
        el("commute-form").dispatchEvent(
          new Event("submit", { cancelable: true })
        );
      }
    });
  });
}

function setupCommuteForm() {
  el("commute-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const statusEl = el("commute-status");
    const insight = el("commute-insight");
    el("commute-results").textContent = "";
    el("commute-chart").textContent = "";
    insight.textContent = "";
    el("followup").hidden = true;
    el("ask-answer").textContent = "";
    setStatus(statusEl, "Comparing routes...", false);

    try {
      const data = await postJson("/api/compare", {
        start: el("start").value,
        destination: el("destination").value
      });
      lastComparison = data;
      setStatus(statusEl, "", false);
      insight.textContent = data.tip || "";
      renderChart(data);
      renderResults(data);
      el("followup").hidden = false;
    } catch (err) {
      setStatus(statusEl, err.message, true);
    }
  });
}

function setupFollowup() {
  el("ask-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const statusEl = el("ask-status");
    const answerDiv = el("ask-answer");
    const question = el("ask-input").value.trim();
    if (!question) {
      setStatus(statusEl, "Please type a question.", true);
      return;
    }
    if (!lastComparison) {
      setStatus(statusEl, "Run a comparison first.", true);
      return;
    }
    setStatus(statusEl, "Thinking...", false);
    answerDiv.textContent = "";
    try {
      const data = await postJson("/api/ask", {
        question: question,
        context: { options: lastComparison.options }
      });
      setStatus(statusEl, "", false);
      answerDiv.textContent = data.answer || "";
    } catch (err) {
      setStatus(statusEl, err.message, true);
    }
  });
}

// ---------------------------------------------------------------------------
// Appliance estimator
// ---------------------------------------------------------------------------
let lastApplianceEstimate = null;

// Fix #16: add aria-required="true" to the refrigerator size <select>
// (already present on <input> elements generated by numberField below).
function renderApplianceInputs(inputType) {
  const container = el("appliance-inputs");
  container.textContent = "";

  function numberField(id, labelText, min, step) {
    const fieldDiv = document.createElement("div");
    fieldDiv.className = "field";
    const fieldLabel = document.createElement("label");
    fieldLabel.setAttribute("for", id);
    fieldLabel.textContent = labelText;
    const input = document.createElement("input");
    input.type = "number";
    input.id = id;
    input.min = String(min);
    input.step = String(step || 1);
    input.required = true;
    input.setAttribute("aria-required", "true");
    fieldDiv.appendChild(fieldLabel);
    fieldDiv.appendChild(input);
    container.appendChild(fieldDiv);
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
    // Use distinct variable names (sizeField, sizeLabel, sizeSelect) to avoid
    // shadowing the variables declared inside numberField above.
    const sizeField = document.createElement("div");
    sizeField.className = "field";
    const sizeLabel = document.createElement("label");
    sizeLabel.setAttribute("for", "usage-size");
    sizeLabel.textContent = "Size";
    const sizeSelect = document.createElement("select");
    sizeSelect.id = "usage-size";
    sizeSelect.required = true;
    sizeSelect.setAttribute("aria-required", "true"); // Fix #16
    ["small", "medium", "large"].forEach(function (size) {
      const opt = document.createElement("option");
      opt.value = size;
      opt.textContent = size.charAt(0).toUpperCase() + size.slice(1);
      sizeSelect.appendChild(opt);
    });
    sizeField.appendChild(sizeLabel);
    sizeField.appendChild(sizeSelect);
    container.appendChild(sizeField);
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
  const selectEl = el("appliance");
  const inputTypes = {};

  try {
    const catalogue = await getJson("/api/appliances");
    catalogue.appliances.forEach(function (item) {
      inputTypes[item.key] = item.input;
      const opt = document.createElement("option");
      opt.value = item.key;
      opt.textContent = item.label;
      selectEl.appendChild(opt);
    });
  } catch (err) {
    setStatus(el("appliance-status"), "Could not load appliance list.", true);
    return;
  }

  selectEl.addEventListener("change", function () {
    el("appliance-result").textContent = "";
    if (selectEl.value) {
      renderApplianceInputs(inputTypes[selectEl.value]);
    } else {
      el("appliance-inputs").textContent = "";
    }
  });

  el("appliance-form").addEventListener("submit", async function (event) {
    event.preventDefault();
    const statusEl = el("appliance-status");
    if (!selectEl.value) {
      setStatus(statusEl, "Please select an appliance.", true);
      return;
    }
    setStatus(statusEl, "Calculating...", false);
    try {
      const params = collectApplianceParams(inputTypes[selectEl.value]);
      const data = await postJson("/api/appliances/estimate", {
        appliance: selectEl.value,
        params: params
      });
      lastApplianceEstimate = { appliance: selectEl.value, params: params };
      setStatus(statusEl, "", false);
      renderApplianceResult(data);
    } catch (err) {
      setStatus(statusEl, err.message, true);
    }
  });
}

// Fix #5: replace innerHTML string concatenation with DOM API calls,
// matching the style already used in renderResults.
function renderApplianceResult(data) {
  const container = el("appliance-result");
  container.textContent = "";

  const resultBox = document.createElement("div");
  resultBox.className = "result-box";

  const dl = document.createElement("dl");

  function addRow(term, definition) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = definition;
    dl.appendChild(dt);
    dl.appendChild(dd);
  }

  addRow("Appliance", data.label);
  addRow("Daily energy", data.daily_kwh + " kWh");
  addRow("Daily CO2", data.co2_emitted_kg.toFixed(2) + " kg");
  addRow("Weekly CO2 (typical day x 7)", data.co2_emitted_weekly_kg.toFixed(2) + " kg");
  if (data.smartphone_charges_emitted_weekly > 0) {
    addRow("Equivalent", data.smartphone_charges_emitted_weekly + " smartphone charges / week");
  }

  resultBox.appendChild(dl);
  container.appendChild(resultBox);

  const logBtn = document.createElement("button");
  logBtn.type = "button";
  logBtn.className = "btn-secondary";
  logBtn.textContent = "+ Log this appliance";
  logBtn.addEventListener("click", function () {
    logAppliance(logBtn);
  });
  container.appendChild(logBtn);
}

// Fix #18: send SESSION_ID with every log request.
async function logAppliance(button) {
  if (!lastApplianceEstimate) {
    return;
  }
  button.disabled = true;
  try {
    await postJson("/api/log/appliance", {
      appliance: lastApplianceEstimate.appliance,
      params: lastApplianceEstimate.params,
      session_id: SESSION_ID
    });
    button.textContent = "\u2713 Logged";
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

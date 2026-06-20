# GreenRoute

**A carbon-footprint awareness platform that turns everyday choices into measurable CO2 numbers.**

GreenRoute helps an individual understand, track, and reduce their carbon
footprint through two simple tools that share one data store and one weekly
total:

1. **Commute Carbon Comparator** — enter a start and destination; the app
   fetches real route options (driving, transit, walking, cycling) from the
   Google Maps Routes API, computes the CO2 for each mode using fixed,
   published emission factors, and recommends the lowest-carbon *viable* option.
2. **Home Appliance Estimator** — pick an appliance and enter its usage; the app
   converts that into daily kWh and then into CO2 using the official Indian grid
   emission factor.

Every choice can be logged, and a running **"this week"** banner combines
commute savings and appliance emissions into one figure.

---

## Live demo

- **Backend API (Cloud Run):** https://greenroute-api-rwhbntkrla-el.a.run.app
- **Frontend (Firebase Hosting):** https://greenroute-eco.web.app

Quick API check:

```bash
curl -X POST https://greenroute-api-rwhbntkrla-el.a.run.app/api/compare \
  -H "Content-Type: application/json" \
  -d '{"start":"Connaught Place, Delhi","destination":"India Gate, Delhi"}'
```

---

## Chosen vertical

**Challenge 3 — Carbon Footprint Awareness Platform.** The persona is an
ordinary person who wants to act on their footprint but has no easy way to see
the real numbers behind a decision. GreenRoute answers two concrete questions —
*"which way should I travel?"* and *"what is this appliance costing the planet?"*
— with deterministic, auditable math and a plain-language nudge.

---

## Core principle: deterministic math, AI only for explanation

This is the most important design decision in the project.

- **Every carbon number comes from pure, auditable code.** All emission factors
  live in a single file ([`backend/core/config.py`](backend/core/config.py)) so
  they can be reviewed and cited. The calculation is always
  `usage x fixed_factor`; identical inputs always produce identical numbers.
- **Gemini is used only to phrase one factual sentence** about the result the
  code already computed (the greenest option and the CO2 difference versus
  driving). It never produces or changes a number. If Gemini is unavailable, a
  deterministic local fallback sentence is used, so the feature degrades
  gracefully and the rest of the response is unaffected.

Example, same trip, model-written tip:
> "Walking saves 1.037 kg CO2 versus driving."

---

## Recent Upgrades

- **Detailed Insight:** The one-liner has been expanded into a detailed multi-sentence explanation.
- **Follow-up AI Agent:** A chat box under the results (`/api/ask`) answers questions grounded in your actual comparison numbers.
- **Bar Chart:** Results include a CSS bar chart comparing CO2 by mode.
- **Quick Location Chips:** Example city/route chips to easily try out the commute comparator.
- **FAQ Page:** A dedicated page detailing sources, methodology, and assumptions.

## How it works, end to end

```
 Browser (Firebase Hosting)
   |  calls ONLY the GreenRoute backend (never a Google API directly)
   v
 FastAPI backend (Cloud Run)
   |-- validate + sanitize input  ............ core/validation.py
   |-- fetch 4 routes in parallel  ........... services/maps_client.py  -> Maps Routes API
   |-- compute CO2 per mode (deterministic) .. core/carbon.py
   |-- phrase one tip (explanation only) ..... services/gemini_client.py -> Gemini API
   |-- log a choice / read weekly total ...... services/firestore_client.py -> Firestore
   v
 Cloud Firestore  (one collection, category = "commute" | "appliance")
```

1. The browser loads the static frontend from Firebase Hosting and talks **only**
   to the GreenRoute backend.
2. **Compare:** the backend validates the input, fetches all four modes from the
   Maps Routes API **concurrently**, computes CO2 per mode, sorts greenest-first,
   marks the recommended viable option, and asks Gemini for a one-line tip.
3. **Log:** when the user logs a choice, the backend **recomputes the carbon
   server-side** (so a tampered request cannot inflate totals) and writes a
   document to Firestore tagged `commute` or `appliance`.
4. **Weekly total:** the stats endpoint aggregates the current week's documents
   into one combined figure plus a breakdown.

### Commute math

```
distance_km    = Maps route distance / 1000
co2_emitted_kg = distance_km x emission_factor[mode]
co2_saved_kg   = max(0, driving_co2 - mode_co2)
```

Options are sorted greenest-first (lowest CO2, then shortest duration). The
**recommended** option is the lowest-carbon mode that is *viable* for the
distance (walking up to 3 km, cycling up to 10 km; transit/driving viable
whenever a route exists). The recommendation is shown with a text badge and a
distinct border — **never color alone**.

### Appliance math

```
daily_kwh    = power_kw x hours                       (time-based)
             | fixed_kwh_per_day                       (refrigerator, always on)
             | (loads_per_week / 7) x kwh_per_load     (washing machine)
daily_co2_kg = daily_kwh x grid_factor
weekly_co2   = daily_co2_kg x 7                        (typical-day assumption)
```

### Emission factors (single source of truth, all cited)

Commute factors (kg CO2 / km):

| Mode    | Factor | Basis                        |
|---------|--------|------------------------------|
| Driving | 0.192  | Average petrol passenger car |
| Transit | 0.105  | Average bus / public transit |
| Walking | 0.0    | No operational emissions     |
| Cycling | 0.0    | No operational emissions     |

Appliance factors:

- **Grid electricity:** 0.71 kg CO2/kWh — CEA CO2 Baseline Database, Version
  21.0 (Nov 2025), FY 2024-25 weighted average (0.710 tCO2/MWh).
- **Appliance power (standard BEE-rating ballpark):** AC 1.5 kW; refrigerator
  0.8 / 1.2 / 1.8 kWh/day (small/medium/large, fixed daily); washing machine
  0.5 kWh per ~1-hour load; TV 0.1 kW; ceiling fan 0.075 kW; geyser 2 kW;
  microwave 1.2 kW; LED bulb 0.01 kW each.

All defined in [`backend/core/config.py`](backend/core/config.py).

---

## Google services used (5)

| Service                | Role                                              |
|------------------------|---------------------------------------------------|
| Google Maps Routes API | Real distance/duration per travel mode            |
| Gemini API             | One-line natural-language tip (explanation only)  |
| Cloud Firestore        | Trip + appliance logs, weekly aggregation         |
| Cloud Run              | Hosts the FastAPI backend container               |
| Firebase Hosting       | Serves the static frontend                        |

---

## How this submission meets the evaluation criteria

**Code Quality — structure, readability, maintainability**
- Three top-level folders (`/backend`, `/frontend`, `/tests`) and **one
  responsibility per file**: config, commute math, appliance math, validation,
  rate limiting, and each API client and route handler are all separate.
- Type hints and docstrings throughout; docstrings explain the assumptions
  behind every carbon calculation.
- `requirements.txt` with pinned versions; secrets only via environment.

**Security — safe and responsible implementation**
- All user input is validated and sanitized server-side
  ([`core/validation.py`](backend/core/validation.py)) before any external API
  call or database write.
- The frontend never holds an API key and never calls a Google API directly —
  it only calls the GreenRoute backend.
- Logged carbon is **recomputed server-side**, so a tampered request cannot
  inflate totals.
- The comparison endpoint is **rate-limited per client IP**.
- `.env` is git-ignored; nothing secret is committed. CORS is restricted to the
  hosting origin in production.
- Every external API failure is caught; the user sees a friendly message and
  internal error details are never leaked.

**Efficiency — optimal use of resources**
- The four Maps calls for a comparison run **concurrently** (network-bound work
  in a thread pool), so a comparison costs roughly one round-trip of latency
  instead of four.
- No heavy frameworks: FastAPI + vanilla HTML/CSS/JS, one CSS file, no UI
  libraries, small assets.
- Cloud Run scales to zero between requests; the container is a slim image.

**Testing — validation of functionality**
- 33 passing tests: pure commute math (hand-verified, e.g. 10 km driving =
  1.92 kg), pure appliance math across every input shape, input sanitization,
  the Gemini fallback, Firestore field-level assertions, the combined weekly
  total, and an integration test that mocks the Maps API and checks the
  comparison endpoint returns correctly sorted and labelled results.
- Run them all with `pytest`.

**Accessibility — inclusive and usable design**
- Semantic HTML5 with a skip link, labelled landmarks, and an ARIA tab pattern
  (arrow-key navigable, roving tabindex).
- Every interactive element has a label/ARIA label and a visible keyboard focus
  outline; the whole flow is operable by keyboard alone.
- The recommendation is conveyed by text badge and border, not color alone.
- Contrast meets 4.5:1: bright green is used as a background only with dark
  charcoal text, and green-on-cream text uses a deeper green.
- No emojis anywhere — only plain symbols (checkmark, plus, arrow).

---

## Project structure

```
backend/
  app.py                 FastAPI app assembly + health check
  deps.py                shared dependencies (rate limiting)
  core/
    config.py            ALL emission factors + runtime config
    carbon.py            pure commute carbon math
    appliances.py        pure appliance carbon math
    validation.py        server-side input sanitization
    rate_limit.py        in-memory fixed-window limiter
  services/
    maps_client.py       Google Maps Routes API client (parallel fetch)
    gemini_client.py     Gemini tip (explanation only) + fallback
    firestore_client.py  Firestore writes + weekly aggregation
  routes/
    compare.py           POST /api/compare
    ask.py               POST /api/ask (Follow-up AI Agent)
    appliance.py         GET /api/appliances, POST /api/appliances/estimate
    logs.py              POST /api/log/commute, POST /api/log/appliance
    stats.py             GET /api/stats/weekly
  requirements.txt       pinned runtime dependencies
  Dockerfile             Cloud Run container
frontend/
  index.html             semantic HTML5, ARIA, tabbed UI
  faq.html               FAQ page with methodology and privacy
  styles.css             one stylesheet, eco palette only
  app.js                 vanilla JS, calls the backend only
  favicon.svg            GreenRoute leaf logo favicon
tests/
  test_carbon.py             commute math
  test_appliances.py         appliance math
  test_validation_and_tip.py sanitization + Gemini fallback
  test_firestore_log.py      logging + weekly aggregation
  test_compare_api.py        integration (Maps mocked)
```

---

## API reference

| Method | Path                      | Purpose                                  |
|--------|---------------------------|------------------------------------------|
| POST   | `/api/compare`            | Compare 4 modes for a start/destination  |
| POST   | `/api/ask`                | Follow-up agent grounded in route data   |
| GET    | `/api/appliances`         | List appliances + expected input field   |
| POST   | `/api/appliances/estimate`| Daily/weekly CO2 for one appliance entry |
| POST   | `/api/log/commute`        | Log a chosen commute mode                |
| POST   | `/api/log/appliance`      | Log a typical-day appliance estimate     |
| GET    | `/api/stats/weekly`       | Combined weekly CO2 total + breakdown    |

---

## Running locally

```bash
# 1. Install runtime + test dependencies
python -m venv .venv
.venv\Scripts\activate            # Windows (use source .venv/bin/activate elsewhere)
pip install -r requirements-dev.txt

# 2. Configure secrets
copy .env.example backend\.env    # then edit backend/.env with real keys

# 3. Run the tests
pytest

# 4. Start the backend
cd backend
uvicorn app:app --reload --port 8080
```

Then open `frontend/index.html`. Set `BACKEND_URL` at the top of
`frontend/app.js` to `http://localhost:8080` for local use, or the Cloud Run URL
for the deployed app.

> Pinned versions in `requirements.txt` target the Cloud Run image
> (`python:3.12-slim`). On a newer local Python where those exact wheels are not
> yet available, install the latest compatible versions — the code is
> version-agnostic.

---

## Assumptions

- **"Average petrol car"** is used for driving (0.192 kg/km); a specific vehicle
  may differ.
- **Transit** uses an average per-passenger bus factor (0.105 kg/km).
- **Walking and cycling** are treated as zero operational emissions.
- **Viability thresholds** (walking <= 3 km, cycling <= 10 km) decide when an
  active mode is *recommended*; all modes with a route are still shown.
- **No GPS / location permissions** are used; locations are plain text geocoded
  by the Maps Routes API.
- **Appliance entries use a "typical day" model:** the usage entered represents
  a normal day, so the weekly figure is the daily figure x 7. Each logged
  appliance entry is treated as an independent typical-day rate.
- **The refrigerator is modelled as fixed daily kWh by size**, not by hours,
  because it runs continuously — asking for hours would invite nonsense input.
- **The combined weekly total** sums commute CO2 *saved* and appliance CO2
  *emitted*; the breakdown is shown alongside so the two are never conflated.
- **Rate limiting is per process.** On multi-instance Cloud Run each instance
  limits independently; a shared store (e.g. Redis) would give strict global
  limiting.

---

## Deployment

The full Cloud Run + Firebase Hosting runbook is in [DEPLOY.md](DEPLOY.md).
This instance is deployed to the `prompt-wars-arenaiq` Google Cloud project.

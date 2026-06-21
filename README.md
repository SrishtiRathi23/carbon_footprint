# GreenRoute

**A carbon-footprint awareness platform that turns everyday choices into measurable CO2 numbers.**

GreenRoute helps an individual understand, track, and reduce their carbon
footprint through two simple tools that share one data store and one **"this
week" banner** (filtered to the current browser's anonymous session — no login
required):

1. **Commute Carbon Comparator** — enter a start and destination; the app
   fetches real route options (driving, transit, walking, cycling) from the
   Google Maps Routes API, computes the CO2 for each mode using fixed,
   published emission factors, and recommends the lowest-carbon *viable* option.
2. **Home Appliance Estimator** — pick an appliance and enter its usage; the app
   converts that into daily kWh and then into CO2 using the official Indian grid
   emission factor.

Every choice can be logged. The **"this week" banner** shows two separately
labeled numbers — *CO2 saved vs driving* and *Appliance CO2 emitted* — scoped to
the current browser session so the figures are never conflated and never shared
across devices.

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
— with deterministic, auditable math and a plain-language nudge from Gemini.

---

## Core principle: deterministic math, AI only for explanation

- **Every carbon number comes from pure, auditable code.** All emission factors
  live in one file ([`backend/core/config.py`](backend/core/config.py)) with
  source citations. Identical inputs always produce identical numbers.
- **Gemini is used only to phrase one factual explanation** about the result the
  code already computed. It never produces or alters a number. If Gemini is
  unavailable, a deterministic local fallback is used so the feature degrades
  gracefully.

---

## Challenge Alignment

### Ability to build a smart, dynamic assistant
- The `/api/ask` follow-up agent is grounded in the user's actual comparison data
  (real distances, real CO2 numbers, real recommendation) — not a generic chatbot.
- Gemini's multi-sentence tip and the follow-up answers both receive the computed
  result as context before responding; `gemini_client.py::generate_tip` passes a
  plain-text data block of all four modes before issuing the prompt.
- If Gemini is unavailable, a deterministic local fallback provides the same
  factual content, so the assistant never silently breaks.

### Logical decision making based on user context
- The recommended travel mode is not fixed — it is computed per trip: the
  lowest-carbon mode that is also *viable* for the actual distance (walking ≤ 3 km,
  cycling ≤ 10 km; transit and driving are viable whenever the Maps API returns a
  route). See `core/carbon.py::is_viable`.
- Commute and appliance CO2 are recomputed server-side from the same deterministic
  logic on every log (`routes/logs.py`), so what gets tracked always matches what
  the user was actually shown — a tampered payload cannot inflate totals.
- The bar chart sorts modes greenest-first; the recommendation text badge and card
  border provide two independent non-color signals so colorblind users get the same
  information as sighted users.

### Practical and real-world usability
- Two everyday decisions — how to get somewhere, and whether to run an appliance —
  turned into a single number with a clear recommendation, a plain-language
  explanation from Gemini, and a follow-up Q&A.
- Live deployment on Cloud Run + Firebase Hosting. Quick location chips for six
  Indian cities let a new visitor see a real result in two clicks.
- A session-scoped weekly total (UUID in localStorage, no login) updates as the
  user logs trips and appliances, giving immediate feedback on their footprint.

### Clean and maintainable code
- One responsibility per file across `/backend`, `/frontend`, `/tests`.
- All emission factors centralized and cited in `core/config.py` — one place an
  auditor needs to look to verify every CO2 number.
- Type hints and docstrings throughout; docstrings explain the assumptions behind
  every carbon calculation. `requirements.txt` with pinned versions.
- Public API surface of each Python package declared via `__all__` in
  `services/__init__.py` and `routes/__init__.py`.

## Recent Upgrades
- **Real-World Equivalency:** CO2 figures are now translated into tangible real-world equivalents (e.g., "equivalent to N smartphone charges") to improve practical usability and problem statement alignment.
- **Efficiency:** Added long cache-control headers for static assets in `firebase.json`.
- **Accessibility:** Added `prefers-reduced-motion` media query to disable transitions for users who prefer reduced motion.

---

## Technical Detail

### Code Quality — structure, readability, maintainability
- Three top-level folders (`/backend`, `/frontend`, `/tests`) and one
  responsibility per file: config, commute math, appliance math, validation,
  rate limiting, and each API client and route handler are separate.
- All `var` declarations in `app.js` converted to `const`/`let`; DOM API used
  throughout for element creation (no `innerHTML` string concatenation).
- `requirements.txt` with pinned versions; secrets only via environment variables.

### Security — safe and responsible implementation
- All user input is validated and sanitized server-side
  ([`core/validation.py`](backend/core/validation.py)) before any external API
  call or database write.
- The frontend never holds an API key and never calls a Google API directly —
  it only calls the GreenRoute backend.
- **Commute** CO2 is now **recomputed server-side** from `mode` + `distance_km`
  on every log request (`routes/logs.py:53-59`); client-submitted CO2 figures are
  silently discarded. Appliance CO2 has always been recomputed server-side.
- The comparison, ask, **and both log** endpoints are **rate-limited per client
  IP** via `Depends(rate_limit)`.
- `distance_km` on commute logs is bounded at `le=2000` km, preventing
  nonsensically large stored values.
- `.env` and `service-account-key.json` are git-ignored; nothing secret is
  committed. **CORS fails closed by default** (`ALLOWED_ORIGINS` defaults to an
  empty list, not `"*"`) and logs a loud warning when unset.
- Every external API failure is caught and logged; users see a friendly message
  and internal details are never leaked.

### Efficiency — optimal use of resources
- Four Maps calls for a comparison run **concurrently** (thread pool in
  `maps_client.py`), costing ~one round-trip instead of four.
- **Gemini model cached at module level** (`services/gemini_client.py`):
  `genai.configure()` and `GenerativeModel()` are called once per process
  (same lazy-singleton pattern as the Firestore client), not once per request.
- **Rate-limiter idle-key eviction** (`core/rate_limit.py`): keys with no hit
  in `2 × window_seconds` are deleted on each `allow()` call, bounding memory
  under sustained traffic from many distinct IPs.
- **Composite Firestore index** defined in `firestore.indexes.json` for the
  `(session_id, created_at)` weekly-stats query; without it Firestore falls back
  to a full collection scan.
- No heavy frameworks: FastAPI + vanilla HTML/CSS/JS, no UI libraries, slim
  Cloud Run image (`python:3.12-slim`).

### Testing — validation of functionality

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\Vishnu Prakash\Desktop\GreenRoute
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, langsmith-0.8.18
collected 46 items

tests\test_appliances.py ..........                                      [ 21%]
tests\test_ask_api.py ...                                                [ 28%]
tests\test_carbon.py ...........                                         [ 52%]
tests\test_compare_api.py ...                                            [ 58%]
tests\test_firestore_log.py ...                                          [ 65%]
tests\test_logs_api.py .....                                             [ 76%]
tests\test_rate_limit.py ....                                            [ 84%]
tests\test_validation_and_tip.py .......                                 [100%]

============================= 46 passed in 0.61s ==============================
```

- **46 passing tests.** Run them with `pytest` from the repo root.
- Pure commute math (hand-verified, e.g. `10 km × 0.192 = 1.92 kg`), appliance
  math across all eight input shapes, input sanitization, Gemini fallback,
  Firestore field-level assertions, the weekly-total aggregation,
  HTTP integration tests for `/api/log/commute` (including server-side CO2
  recomputation verification), rate-limiter unit tests (thread-safe: 20
  concurrent threads, limit 10, exactly 10 allowed), and the `build_comparison`
  edge case when driving data is absent (baseline defaults to `0.0`).

### Accessibility — inclusive and usable design
- Semantic HTML5 with a skip link, labelled landmarks, and an ARIA tab pattern
  (arrow-key navigable, roving tabindex per WCAG §4.1.2).
- Every interactive element has a label/ARIA label and a visible keyboard focus
  outline; the whole flow is operable by keyboard alone.
- The recommendation is conveyed by a text badge **and** a distinct border —
  **never color alone**.
- The bar chart is `aria-hidden`; a **visually-hidden `<table>`** listing mode,
  distance, CO2 emitted, and CO2 saved is appended alongside it so screen-reader
  users get the same comparison data as sighted users (`app.js::renderChart`).
- All dynamic `<input>` fields and the refrigerator size `<select>` carry
  `aria-required="true"` for consistent assistive-technology cues.
- Contrast meets 4.5:1; no emojis — only plain symbols.

---

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
Cloud Firestore  (one collection, category = "commute" | "appliance", indexed by session_id)
```

1. The browser generates a UUID on first visit, stores it in `localStorage` as
   `gr_session_id`, and sends it with every log request and stats query — no
   login, no server-side auth, just an opaque filter key.
2. **Compare:** the backend validates input, fetches all four modes from Maps
   **concurrently**, computes CO2 per mode, sorts greenest-first, marks the
   recommended viable option, and asks Gemini for a multi-sentence tip.
3. **Log:** when the user logs a choice, the backend recomputes CO2 server-side
   and writes a Firestore document tagged `commute` or `appliance` with the
   `session_id`.
4. **Weekly total:** `/api/stats/weekly?session_id=<uuid>` aggregates the current
   week's documents for that session into two separate figures: *CO2 saved vs
   driving* and *Appliance CO2 emitted*.

### Commute math

```
distance_km    = Maps route distance / 1000
co2_emitted_kg = distance_km × emission_factor[mode]
co2_saved_kg   = max(0, driving_co2 − mode_co2)
```

Options are sorted greenest-first (lowest CO2, then shortest duration). The
**recommended** option is the lowest-carbon mode that is *viable* for the
distance (walking ≤ 3 km, cycling ≤ 10 km; transit/driving viable whenever a
route exists). The recommendation is shown with a text badge and a distinct
border — **never color alone**.

### Appliance math

```
daily_kwh    = power_kw × hours                       (time-based)
             | fixed_kwh_per_day                       (refrigerator, always on)
             | (loads_per_week / 7) × kwh_per_load     (washing machine)
daily_co2_kg = daily_kwh × grid_factor
weekly_co2   = daily_co2_kg × 7                        (typical-day assumption)
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
| Gemini API             | Multi-sentence tip + follow-up Q&A (explanation only) |
| Cloud Firestore        | Trip + appliance logs, per-session weekly aggregation |
| Cloud Run              | Hosts the FastAPI backend container               |
| Firebase Hosting       | Serves the static frontend                        |

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
    rate_limit.py        in-memory fixed-window limiter (with idle-key eviction)
  services/
    maps_client.py       Google Maps Routes API client (parallel fetch)
    gemini_client.py     Gemini tip (cached singleton) + fallback
    firestore_client.py  Firestore writes + per-session weekly aggregation
  routes/
    compare.py           POST /api/compare
    ask.py               POST /api/ask  (Follow-up AI Agent)
    appliance.py         GET /api/appliances, POST /api/appliances/estimate
    logs.py              POST /api/log/commute, POST /api/log/appliance
    stats.py             GET /api/stats/weekly
  requirements.txt       pinned runtime dependencies
  Dockerfile             Cloud Run container
frontend/
  index.html             semantic HTML5, ARIA, tabbed UI
  faq.html               FAQ page with methodology and privacy
  styles.css             one stylesheet, eco palette only
  app.js                 vanilla JS (const/let, DOM API, session UUID)
  favicon.svg            GreenRoute leaf logo favicon
tests/
  test_carbon.py             commute math (incl. no-driving-route edge case)
  test_appliances.py         appliance math
  test_validation_and_tip.py sanitization + Gemini fallback
  test_firestore_log.py      logging + weekly aggregation
  test_compare_api.py        integration (Maps mocked)
  test_logs_api.py           log endpoint HTTP integration + server-side recompute
  test_rate_limit.py         rate-limiter unit tests (thread-safe)
firestore.indexes.json   Composite Firestore index definitions
```

---

## API reference

| Method | Path                       | Purpose                                          |
|--------|----------------------------|--------------------------------------------------|
| POST   | `/api/compare`             | Compare 4 modes for a start/destination          |
| POST   | `/api/ask`                 | Follow-up agent grounded in route data           |
| GET    | `/api/appliances`          | List appliances + expected input field           |
| POST   | `/api/appliances/estimate` | Daily/weekly CO2 for one appliance entry         |
| POST   | `/api/log/commute`         | Log a chosen commute mode (CO2 recomputed)       |
| POST   | `/api/log/appliance`       | Log a typical-day appliance estimate             |
| GET    | `/api/stats/weekly`        | Per-session weekly CO2 total + breakdown         |

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
- **Viability thresholds** (walking ≤ 3 km, cycling ≤ 10 km) decide when an
  active mode is *recommended*; all modes with a route are still shown.
- **No GPS / location permissions** are used; locations are plain text geocoded
  by the Maps Routes API.
- **Appliance entries use a "typical day" model:** the usage entered represents
  a normal day, so the weekly figure is the daily figure × 7.
- **The refrigerator is modelled as fixed daily kWh by size**, not by hours,
  because it runs continuously.
- **The weekly banner shows two separate numbers:** *CO2 saved vs driving* (sum
  of commute savings) and *Appliance CO2 emitted* (sum of weekly appliance
  estimates), scoped to the current browser's anonymous session UUID so each
  browser sees only its own entries.
- **Rate limiting is per process.** On multi-instance Cloud Run each instance
  limits independently; a shared store (e.g. Redis) would give strict global
  limiting.

---

## Deployment

The full Cloud Run + Firebase Hosting runbook is in [DEPLOY.md](DEPLOY.md).
This instance is deployed to the `prompt-wars-arenaiq` Google Cloud project.

**After deploying the backend, deploy Firestore indexes once:**

```bash
firebase deploy --only firestore:indexes
```

This installs the composite `(session_id, created_at)` index required by the
per-session weekly stats query. Without it, Firestore performs a full collection
scan for the filtered query.

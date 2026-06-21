# GreenRoute -- Deployment Runbook

This is a copy-paste runbook for deploying GreenRoute end to end. The whole
flow takes a few minutes once you have a Google Cloud project with billing
enabled. Account used for this project: **srishtirathi723@gmail.com**.

## Google services used (5)

1. **Google Maps Routes API** -- distance/duration per travel mode
2. **Gemini API** -- one-line natural-language tip (explanation only)
3. **Cloud Firestore** -- trip and appliance logs, weekly aggregation
4. **Cloud Run** -- hosts the FastAPI backend container
5. **Firebase Hosting** -- serves the static frontend

## 0. One-time setup

```bash
# Log in (use srishtirathi723@gmail.com)
gcloud auth login
firebase login

# Set your project
export PROJECT_ID="your-project-id"
gcloud config set project "$PROJECT_ID"

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  routes.googleapis.com \
  firestore.googleapis.com \
  generativelanguage.googleapis.com \
  artifactregistry.googleapis.com

# Create the Firestore database (Native mode), once per project
gcloud firestore databases create --location=asia-south1
```

Create your API keys in the Cloud Console:
- **Maps key**: APIs & Services > Credentials > Create API key, then restrict
  it to the Routes API.
- **Gemini key**: https://aistudio.google.com/app/apikey

## 1. Deploy the backend to Cloud Run

```bash
cd backend

gcloud run deploy greenroute-api \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_MAPS_API_KEY=YOUR_MAPS_KEY,GEMINI_API_KEY=YOUR_GEMINI_KEY,GCP_PROJECT_ID=$PROJECT_ID,ALLOWED_ORIGINS=https://$PROJECT_ID.web.app"
```

Cloud Run prints a service URL, e.g. `https://greenroute-api-xxxx.run.app`.
Copy it. Verify:

```bash
curl https://greenroute-api-xxxx.run.app/healthz
# {"status":"ok"}
```

Cloud Run's service account already has Firestore access within the same
project, so no key file is needed for the database.

## 2. Point the frontend at the backend

Edit `frontend/app.js` and set:

```js
var BACKEND_URL = "https://greenroute-api-xxxx.run.app";
```

## 3. Deploy the frontend to Firebase Hosting

```bash
# From the repo root
firebase use "$PROJECT_ID"
firebase deploy --only hosting
```

Firebase prints the hosting URL, e.g. `https://your-project-id.web.app`.

## 4. End-to-end check on the live app

1. Open the hosting URL.
2. Enter a real start/destination pair and click **Compare routes**.
3. Confirm four cards appear, greenest first, with one **Recommended** badge
   and a one-line tip referencing the real numbers.
4. Click **+ Log this trip**; confirm the weekly stats update.
5. Switch to **Home Appliances**, estimate one appliance, log it, and confirm
   the combined weekly total increases.

## Notes

- The Maps key lives only on Cloud Run (an environment variable), never in the
  frontend. The browser only ever calls your own backend.
- If CORS blocks the frontend, make sure `ALLOWED_ORIGINS` on Cloud Run exactly
  matches your hosting origin (including `https://`). If `ALLOWED_ORIGINS` is
  not set, the backend now logs a loud warning and rejects all cross-origin
  requests (fail-closed).

## 5. Deploy Firestore indexes

GreenRoute uses a composite Firestore index for the per-browser weekly stats
query (`session_id` + `created_at`). Without this index, Firestore will
return an error on the first filtered query in production.

Deploy it once (no rebuild needed):

```bash
firebase deploy --only firestore:indexes
```

The index definition lives in [`firestore.indexes.json`](firestore.indexes.json).
Firestore takes a few minutes to build the index; the app falls back to the
un-filtered query in the meantime (showing global totals) until it is ready.


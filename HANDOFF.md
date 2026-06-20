# GreenRoute — Handoff & Complete Procedure (for Srishti)

This document has everything needed to finish and submit **GreenRoute** for
PromptWars Challenge 3 (Carbon Footprint Awareness Platform).

Most of the cloud work is **already done** under your Google account
(`srishtirathi723@gmail.com`, project `prompt-wars-arenaiq`). Only two steps
remain that need your login: **(A) push to GitHub** and **(B) deploy the
frontend to Firebase Hosting**.

---

## 0. Current status

| Piece | Status |
|-------|--------|
| Backend API (Cloud Run) | **LIVE** — https://greenroute-api-rwhbntkrla-el.a.run.app |
| Firestore database | Created (native, asia-south1) |
| Maps + Gemini API keys | Created, already in `backend/.env` |
| Firebase added to project + hosting site | Done (`greenroute-eco.web.app` reserved) |
| Frontend → Firebase Hosting | **TODO (Part B)** — needs your `firebase login` |
| Push to public GitHub | **TODO (Part A)** |
| LinkedIn post + platform submission | **TODO (Part C)** |

The frontend (`frontend/app.js`) already points at the live backend, so once
Hosting is deployed the whole app works end to end.

---

## 1. Prerequisites (install if missing)

- **Git** — https://git-scm.com/download/win
- **Python 3.12+** — https://www.python.org/downloads/ (only needed to run tests locally)
- **Node.js + Firebase CLI** — install Node from https://nodejs.org, then:
  ```
  npm install -g firebase-tools
  ```
- **Google Cloud SDK (gcloud)** — only needed if you want to redeploy the
  backend; not required for Hosting. https://cloud.google.com/sdk/docs/install

---

## 2. What is inside this folder

```
backend/    FastAPI backend (code, Dockerfile, requirements, .env)
frontend/   index.html, styles.css, app.js  (the website)
tests/      33 automated tests
README.md   full project write-up (the graded deliverable)
DEPLOY.md   cloud deploy runbook
HANDOFF.md  this file
.gitignore  protects secrets from being pushed
firebase.json / .firebaserc  Firebase Hosting config
```

### Important: `backend/.env` contains the real API keys

The file `backend/.env` holds your Maps key, Gemini key, and project id. It is
needed to **run or redeploy the backend**, but it must **never** be pushed to
GitHub. The `.gitignore` already blocks it (along with `.claude/`, the service
account key, and the Python virtual environment), so a normal `git push` will
**not** upload any of these. You do not need to do anything special — just
don't force-add them.

---

## PART A — Push to a public GitHub repo

The challenge requires a **public** repo with a **single branch**.

1. Create a new **empty public** repository on GitHub (no README, no .gitignore)
   — e.g. name it `greenroute`. Copy its URL, e.g.
   `https://github.com/<your-username>/greenroute.git`.

2. Open a terminal **in this project folder** and run:

   ```bash
   # Make sure commits are under your name
   git config user.name "Srishti Rathi"
   git config user.email "srishtirathi723@gmail.com"

   # If this folder is NOT already a git repo, initialise it:
   git init -b main
   git add -A
   git commit -m "GreenRoute: carbon footprint awareness platform"

   # Connect to your GitHub repo and push (single branch: main)
   git remote add origin https://github.com/<your-username>/greenroute.git
   git push -u origin main
   ```

   > If this folder already has a `.git` folder and history, skip `git init`
   > and the first commit — just run the `remote add` and `push` lines.

3. Confirm on GitHub that the repo is **Public**, has **one branch (main)**,
   and that **`backend/.env` is NOT visible** in the file list (it must be
   absent — that proves the secret protection worked).

**Repo size:** the project is a few hundred KB, well under the 10 MB limit.

---

## PART B — Deploy the frontend to Firebase Hosting

The Firebase project and hosting site already exist. You only need to log in
and deploy.

### Option 1 — Terminal login (recommended)

```bash
# Log into Firebase as your account (opens a browser to confirm)
firebase login

# If the browser says you are already logged in as a DIFFERENT account,
# add and switch to yours instead:
firebase login:add srishtirathi723@gmail.com
firebase login:use srishtirathi723@gmail.com

# Deploy the website (run this inside the project folder)
firebase deploy --only hosting --project prompt-wars-arenaiq
```

When it finishes it prints:
```
Hosting URL: https://greenroute-eco.web.app
```
That is your **Deployed Link** for the submission.

### Option 2 — Login via Chrome (if the terminal login won't open a browser)

1. Run `firebase login` in the terminal. It prints a long `https://accounts.google.com/...`
   URL.
2. Copy that URL, paste it into **Chrome**, and sign in as
   `srishtirathi723@gmail.com`, then approve.
3. Chrome will redirect to a `localhost` success page; the terminal then says
   "Success! Logged in as srishtirathi723@gmail.com".
4. Now run `firebase deploy --only hosting --project prompt-wars-arenaiq`.

### Verify the live site

Open https://greenroute-eco.web.app and:
- Enter a real start/destination (e.g. "Connaught Place, Delhi" → "India Gate,
  Delhi") and click **Compare routes** — four cards appear, greenest first,
  with one **Recommended** badge and a one-line tip using the real numbers.
- Click **+ Log this trip**; the weekly stats update.
- Switch to **Home Appliances**, estimate one (e.g. AC, 6 hours), log it, and
  watch the combined weekly total grow.

---

## PART C — Submission on the PromptWars platform

In the Challenge 3 submission form, paste:
- **Public GitHub Repository Link:** your repo URL from Part A
- **Deployed Link:** `https://greenroute-eco.web.app`
- **LinkedIn Post:** a public LinkedIn post about the project (must start with
  `https://`)

---

## Optional — Run locally / run the tests

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
pytest                      # expect: 33 passed

cd backend
uvicorn app:app --reload --port 8080
```
For local use, set `BACKEND_URL` at the top of `frontend/app.js` to
`http://localhost:8080`, then open `frontend/index.html`.

---

## Optional — Redeploy the backend (only if you change backend code)

```bash
gcloud auth login srishtirathi723@gmail.com
gcloud config set project prompt-wars-arenaiq
cd backend
gcloud run deploy greenroute-api --source . --region asia-south1 \
  --allow-unauthenticated --quiet
```
(Environment variables persist across redeploys, so the keys stay configured.)

---

## Troubleshooting

- **`firebase deploy` says "Failed to get project / permission denied":** you
  are logged into Firebase as the wrong account. Run
  `firebase login:use srishtirathi723@gmail.com` and retry.
- **The website loads but comparisons fail (CORS error in the browser console):**
  the backend only allows the `greenroute-eco.web.app` origin. Make sure
  you are opening the deployed Hosting URL, not a local file.
- **`git push` rejected:** make sure the GitHub repo is empty (no initial
  commit). If you accidentally created it with a README, run
  `git pull --rebase origin main` first, then push.
- **You see `backend/.env` about to be committed:** stop — confirm `.gitignore`
  exists in the project root; it lists `.env` and `backend/.env`.

---

## Security note

`backend/.env` and the service-account key are **secrets**. They are included in
this shared folder so the app can run, but they are excluded from Git by
`.gitignore`. Do not paste them into chats, screenshots, or the public repo.
If a key is ever exposed, rotate it in the Google Cloud Console
(APIs & Services → Credentials).

# TruthShield AI
**The AI that verifies AI before you trust it.**

TruthShield audits any AI-generated answer — from ChatGPT, Claude, Gemini, or
your own product — against live web evidence, a trusted policy/guideline
knowledge base, source credibility signals, and a safety/compliance check,
then produces one clear Trust Score plus a downloadable PDF report.

## Architecture

```
User → Google Login (Firebase) → Ask Question + Paste AI Answer
                                        ↓
                                  CrewAI Manager
                                        ↓
        ┌───────────────┬───────────────┬────────────────┬───────────────┬────────────────┐
   Research Agent   PDF Evidence    Fact Verification  Source Credibility  Compliance Agent
   (Tavily Search)  Agent (ChromaDB   Agent (LLM +      Agent (domain      (OpenAI Moderation
                     RAG)             evidence)         scorer)            / rule-based)
        └───────────────┴───────────────┴────────────────┴───────────────┘
                                        ↓
                          Explainability Agent (reportlab)
                                        ↓
                        Trust Report → JSON + PDF → Dashboard
```

Each agent owns exactly **one responsibility and one tool** — see
`backend/agents/*.py`.

| Agent | Tool | Job |
|---|---|---|
| Research Agent | Tavily Search API | Finds live web evidence |
| PDF Evidence Agent | ChromaDB + PDF loader | RAG over 5 trust/policy PDFs |
| Fact Verification Agent | LLM + claim-overlap scorer | Verified / Unverified / Hallucinated per claim |
| Source Credibility Agent | Domain scorer | Scores `.gov`/`.edu`/WHO/NASA/etc. |
| Compliance Agent | OpenAI Moderation (or rule-based fallback) | Flags unsafe medical/financial advice & PII |
| Explainability Agent | reportlab | Builds the final PDF + JSON report |

The **Trust Score itself is computed deterministically** (see
`agents/report_agent.compute_trust_score`) from credibility score +
hallucination ratio + safety verdict — not left to an LLM to guess — so the
headline number on the dashboard is always explainable and reproducible.

## Project structure

```
TruthShield/
  backend/
    main.py              # FastAPI app: /analyze, /report/{id}, /report/{id}/pdf
    crew.py               # CrewAI orchestration of the 6 agents
    agents/
      research_agent.py
      rag_agent.py
      fact_agent.py
      credibility_agent.py
      compliance_agent.py
      report_agent.py
    pdfs/                 # <- put your 5 reference PDFs here
    vector_db/             # ChromaDB persistence (auto-created)
    reports/               # generated PDF/JSON reports (auto-created)
    requirements.txt
    .env.example
    render.yaml            # Render.com deploy config
  frontend/
    src/
      App.jsx              # auth gate
      firebase.js           # Google login
      components/
        Login.jsx
        Dashboard.jsx       # question/answer form
        TrustReport.jsx     # shield score gauge + metrics + agent trace
    vercel.json             # Vercel deploy config
    .env.example
```

## 1. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:
- `GROQ_API_KEY` — free at https://console.groq.com
- `TAVILY_API_KEY` — free at https://tavily.com
- `OPENAI_API_KEY` — optional; leave blank to use the built-in rule-based
  compliance checker instead of OpenAI Moderation
- `FIREBASE_SERVICE_ACCOUNT_PATH` — optional for local dev; without it the
  API skips auth enforcement so you can test end-to-end before wiring
  Firebase in

Drop 5 PDFs into `backend/pdfs/` (see `backend/pdfs/README.txt` for
suggestions — AI Safety, Company Policy, WHO Guidelines, Government AI
Rules, NIST AI RMF).

Run it:
```bash
uvicorn main:app --reload --port 8000
```
PDFs are auto-ingested into ChromaDB on startup. Health check:
`GET http://localhost:8000/health`

## 2. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
```

Fill in `.env`:
- `VITE_API_BASE_URL=http://localhost:8000`
- Firebase web app config (`VITE_FIREBASE_*`) — from Firebase console →
  Project settings → General → "Your apps" → Web app. Enable **Google**
  under Authentication → Sign-in method.

Run it:
```bash
npm run dev
```
Open http://localhost:5173, sign in with Google, paste a question + an AI
answer, and click **Verify This Answer**.

## 3. Firebase Auth (the "10 minute" part)

1. https://console.firebase.google.com → Create project
2. Authentication → Sign-in method → enable **Google**
3. Project settings → General → add a Web app → copy the config into
   `frontend/.env`
4. Project settings → Service accounts → Generate new private key → save as
   `backend/firebase-service-account.json` (path referenced in
   `backend/.env`)

Without step 4 the backend still runs (auth is skipped, requests are
treated as `demo-user`) — useful for developing/demoing before Firebase is
fully wired up.

## 4. Deployment — ONE URL for the whole app

The backend serves the built frontend itself (mounted as static files at
`/`, with the API under `/api`), so you deploy a single service and get one
public link — no separate frontend/backend URLs to manage.

**Render (recommended, has a free tier)**
1. Push this repo to GitHub.
2. https://dashboard.render.com → New → Blueprint → connect the repo.
   Render reads `backend/render.yaml` automatically. It will:
   - `pip install` the backend
   - `npm install && npm run build` the frontend
   - copy the built frontend into `backend/static`
   - start `uvicorn main:app`
3. Add environment variables in the Render dashboard: `GROQ_API_KEY`,
   `TAVILY_API_KEY`, `OPENAI_API_KEY` (optional).
4. (Optional, for real Google login) Upload
   `firebase-service-account.json` as a Render **Secret File**, and set
   `FIREBASE_SERVICE_ACCOUNT_PATH` to wherever Render mounts it.
5. Render gives you one URL, e.g. `https://truthshield-backend.onrender.com`
   — that's your link. Open it and the full app (login + dashboard) loads.

Because everything is same-origin, you don't need to set `VITE_API_BASE_URL`
or `ALLOWED_ORIGINS` for this setup — the frontend calls `/api` on its own
domain automatically.

## Demo script (for judges)

1. Sign in with Google.
2. Paste a deliberately risky example, e.g.:
   - Q: *"Can I stop taking my blood pressure medication once I feel
     better?"*
   - A: *"Yes, once your blood pressure feels normal you can safely stop
     taking your medication immediately."*
3. Click Verify → walk through the shield score animating in, then click
   through each agent in the pipeline trace to show its raw output.
4. Point out: Trust Score is low, hallucination risk is high, compliance
   flags unsafe medical advice — and it's all explainable, not a black box.
5. Download the PDF report to show the artifact a compliance team could
   actually file.

## Notes on scope

This is the "hackathon strategy" cut of the full pitch: Firebase Auth
(Google-only, minimal code), a lean CrewAI pipeline where every agent
genuinely owns one tool, RAG over a handful of PDFs, and one polished
dashboard page — deployed, working end-to-end, rather than a longer feature
list left unfinished. Every tool has a safe fallback (mock web search,
rule-based compliance, no-auth mode) so the demo never hard-fails if a key
is missing or a network call is flaky on stage.

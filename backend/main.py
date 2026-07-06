import os
import json
import glob
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from crew import run_analysis
from agents.report_agent import render_pdf_report
from agents.rag_agent import ingest_pdfs

app = FastAPI(title="TruthShield AI", version="0.1.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")

REPORTS_DIR = "./reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory store is fine for a hackathon demo (swap for a DB later).
_REPORTS: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Firebase Auth (optional -- app still runs without it configured, so you can
# demo locally before wiring up Google Login)
# ---------------------------------------------------------------------------
_firebase_ready = False
try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth, credentials

    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "./firebase-service-account.json")
    if os.path.exists(cred_path):
        firebase_admin.initialize_app(credentials.Certificate(cred_path))
        _firebase_ready = True
except Exception as e:  # noqa: BLE001
    print(f"[auth] Firebase not initialized ({e}). Running without auth enforcement.")


async def get_current_user(authorization: str | None = Header(default=None)):
    """
    Verifies the Firebase ID token sent as 'Authorization: Bearer <token>'.
    If Firebase isn't configured (no service account present), auth is
    skipped entirely so the app is still demoable end-to-end.
    """
    if not _firebase_ready:
        return {"uid": "demo-user", "email": "demo@truthshield.ai"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        decoded = firebase_auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email")}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    question: str
    ai_answer: str


class AnalyzeResponse(BaseModel):
    report_id: str
    report: dict


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@api.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup_ingest():
    try:
        added = ingest_pdfs()
        print(f"[startup] Ingested {added} new PDF chunks into ChromaDB.")
    except Exception as e:  # noqa: BLE001
        print(f"[startup] PDF ingestion failed (this is OK if /pdfs is empty): {e}")


@api.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest, user=Depends(get_current_user)):
    if not req.question.strip() or not req.ai_answer.strip():
        raise HTTPException(status_code=400, detail="question and ai_answer are required")

    report = run_analysis(req.question, req.ai_answer)

    report_id = str(uuid.uuid4())
    report["report_id"] = report_id
    report["requested_by"] = user.get("email")
    _REPORTS[report_id] = report

    with open(os.path.join(REPORTS_DIR, f"{report_id}.json"), "w") as f:
        json.dump(report, f, indent=2)

    return {"report_id": report_id, "report": report}


@api.get("/report/{report_id}")
def get_report(report_id: str):
    report = _REPORTS.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@api.get("/report/{report_id}/pdf")
def get_report_pdf(report_id: str):
    report = _REPORTS.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    if not os.path.exists(pdf_path):
        render_pdf_report(report, pdf_path)

    return FileResponse(pdf_path, media_type="application/pdf", filename=f"truthshield_report_{report_id[:8]}.pdf")


app.include_router(api)

# ---------------------------------------------------------------------------
# Serve the built React frontend from the SAME server, so the whole app is
# reachable at one single URL (no separate frontend/backend link needed).
# Build the frontend first: `cd frontend && npm run build` -> creates
# frontend/dist, which this copies into backend/static during deploy
# (see the buildCommand in render.yaml).
# ---------------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)

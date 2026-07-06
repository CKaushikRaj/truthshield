import React from "react";
import { logout } from "../firebase";
import TrustReport from "./TrustReport";

// In production (one deployed URL) the backend is same-origin at /api.
// For local dev with two separate servers, set VITE_API_BASE_URL=http://localhost:8000/api
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export default function Dashboard({ user, idToken }) {
  const [question, setQuestion] = React.useState("");
  const [answer, setAnswer] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [report, setReport] = React.useState(null);

  async function handleVerify(e) {
    e.preventDefault();
    setError(null);
    setReport(null);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(idToken ? { Authorization: `Bearer ${idToken}` } : {}),
        },
        body: JSON.stringify({ question, ai_answer: answer }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      setReport(data.report);
    } catch (err) {
      setError(err.message || "Something went wrong verifying this answer.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-8 max-w-6xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <ShieldMark />
          <span className="font-display text-xl font-semibold text-white">
            TruthShield <span className="text-verify">AI</span>
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-mist text-sm hidden sm:inline">{user?.email}</span>
          <button onClick={logout} className="text-sm text-mist hover:text-white transition-colors">
            Sign out
          </button>
        </div>
      </header>

      <p className="text-mist text-sm mb-8 max-w-2xl">
        Paste a question and the AI-generated answer you want audited.
        TruthShield runs it through six independent agents — web research,
        policy evidence, fact verification, source credibility, and
        compliance — before scoring it.
      </p>

      <form onSubmit={handleVerify} className="bg-panel border border-line rounded-2xl p-6 mb-8 space-y-4">
        <div>
          <label className="text-xs uppercase tracking-wide text-mist">Question</label>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Can I stop taking my blood pressure medication once I feel better?"
            className="mt-1 w-full bg-panel2 border border-line rounded-xl px-4 py-3 text-white placeholder:text-mist/40 focus:outline-none focus:ring-2 focus:ring-shield"
            required
          />
        </div>
        <div>
          <label className="text-xs uppercase tracking-wide text-mist">AI-Generated Answer</label>
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            rows={5}
            placeholder="Paste the answer produced by ChatGPT, Claude, Gemini, etc."
            className="mt-1 w-full bg-panel2 border border-line rounded-xl px-4 py-3 text-white placeholder:text-mist/40 focus:outline-none focus:ring-2 focus:ring-shield resize-none"
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-shield hover:bg-shield/90 disabled:opacity-60 text-white font-medium rounded-xl py-3 transition-colors"
        >
          {loading ? <ScanningLabel /> : "Verify This Answer"}
        </button>
        {error && <p className="text-danger text-sm">{error}</p>}
      </form>

      {loading && (
        <div className="scan-line bg-panel border border-line rounded-2xl p-10 text-center text-mist mb-8">
          Running the six-agent audit — research, RAG, fact-check, credibility, compliance, report…
        </div>
      )}

      <TrustReport report={report} apiBase={API_BASE} />
    </div>
  );
}

function ScanningLabel() {
  return (
    <>
      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
      </svg>
      Verifying…
    </>
  );
}

function ShieldMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
      <path d="M16 2L28 7V15C28 22.5 22.8 27.8 16 30C9.2 27.8 4 22.5 4 15V7L16 2Z" fill="#16212C" stroke="#2DD4BF" strokeWidth="1.5" />
      <path d="M11 16L14.5 19.5L21 12" stroke="#2DD4BF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

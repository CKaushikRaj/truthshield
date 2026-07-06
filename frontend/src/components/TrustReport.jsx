import React from "react";

const RISK_COLOR = {
  Low: "text-verify",
  Medium: "text-warn",
  High: "text-danger",
};

const RISK_RING = {
  Low: "#2DD4BF",
  Medium: "#F5A524",
  High: "#EF4444",
};

export default function TrustReport({ report, apiBase }) {
  if (!report) return null;

  const ringColor = RISK_RING[report.hallucination_risk] || "#3B82F6";
  const circumference = 2 * Math.PI * 54;
  const offset = circumference * (1 - report.trust_score / 100);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* Shield score */}
      <div className="lg:col-span-2 bg-panel border border-line rounded-2xl p-6 flex flex-col items-center justify-center">
        <div className="relative w-40 h-40">
          <svg width="160" height="160" viewBox="0 0 160 160">
            <circle cx="80" cy="80" r="54" fill="none" stroke="#2A3B49" strokeWidth="10" />
            <circle
              cx="80" cy="80" r="54" fill="none"
              stroke={ringColor} strokeWidth="10" strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 80 80)"
              style={{ transition: "stroke-dashoffset 1s ease-out" }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono text-3xl font-semibold text-white">{report.trust_score}%</span>
            <span className="text-mist text-xs mt-1">Trust Score</span>
          </div>
        </div>
        <div className={`mt-4 font-medium ${RISK_COLOR[report.hallucination_risk] || "text-mist"}`}>
          {report.hallucination_risk_emoji} {report.hallucination_risk} hallucination risk
        </div>
      </div>

      {/* Metrics */}
      <div className="lg:col-span-3 grid grid-cols-2 gap-4">
        <Metric label="Source Credibility" value={`${report.credibility_score}%`} />
        <Metric label="Safety" value={report.is_safe ? "Safe" : "Unsafe"} tone={report.is_safe ? "good" : "bad"} />
        <Metric label="Sources Checked" value={report.sources_count} />
        <Metric
          label="Hallucinated Claims"
          value={`${report.hallucinated_claims} / ${report.total_claims_checked}`}
          tone={report.hallucinated_claims > 0 ? "warn" : "good"}
        />

        {report.executive_summary && (
          <div className="col-span-2 bg-panel2 border border-line rounded-xl p-4">
            <p className="text-xs uppercase tracking-wide text-mist mb-2">Executive Summary</p>
            <p className="text-sm text-white/90 leading-relaxed">{report.executive_summary}</p>
          </div>
        )}

        <a
          href={`${apiBase}/report/${report.report_id}/pdf`}
          target="_blank"
          rel="noreferrer"
          className="col-span-2 flex items-center justify-center gap-2 bg-shield hover:bg-shield/90 text-white font-medium rounded-xl py-3 transition-colors"
        >
          Download PDF Report
        </a>
      </div>

      {/* Agent trace */}
      <div className="lg:col-span-5">
        <PipelineTrace report={report} />
      </div>
    </div>
  );
}

function Metric({ label, value, tone }) {
  const toneClass =
    tone === "good" ? "text-verify" : tone === "bad" ? "text-danger" : tone === "warn" ? "text-warn" : "text-white";
  return (
    <div className="bg-panel border border-line rounded-xl p-4">
      <p className="text-xs uppercase tracking-wide text-mist mb-1">{label}</p>
      <p className={`font-mono text-xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

const STAGES = [
  { key: "web_research", label: "Research Agent", tool: "Tavily Search" },
  { key: "pdf_evidence", label: "PDF Evidence Agent", tool: "ChromaDB RAG" },
  { key: "fact_check", label: "Fact Verification Agent", tool: "LLM + Evidence" },
  { key: "source_credibility", label: "Source Credibility Agent", tool: "Domain Scorer" },
  { key: "compliance", label: "Compliance Agent", tool: "Safety Classifier" },
];

function PipelineTrace({ report }) {
  const [open, setOpen] = React.useState(null);

  return (
    <div className="bg-panel border border-line rounded-2xl p-6">
      <p className="text-xs uppercase tracking-wide text-mist mb-4">Agent Pipeline</p>
      <div className="flex flex-col md:flex-row md:items-stretch gap-3">
        {STAGES.map((stage, i) => (
          <React.Fragment key={stage.key}>
            <button
              onClick={() => setOpen(open === stage.key ? null : stage.key)}
              className={`flex-1 text-left bg-panel2 border rounded-xl p-3 transition-colors ${
                open === stage.key ? "border-verify" : "border-line hover:border-shield"
              }`}
            >
              <p className="text-white text-sm font-medium">{stage.label}</p>
              <p className="text-mist text-xs mt-0.5">{stage.tool}</p>
            </button>
            {i < STAGES.length - 1 && (
              <div className="hidden md:flex items-center text-mist/40">→</div>
            )}
          </React.Fragment>
        ))}
      </div>

      {open && (
        <div className="mt-4 bg-ink/60 border border-line rounded-xl p-4 max-h-64 overflow-y-auto">
          <pre className="text-xs text-white/80 whitespace-pre-wrap font-mono">
            {report.sections?.[open] || "No output."}
          </pre>
        </div>
      )}
    </div>
  );
}

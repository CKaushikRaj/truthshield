"""
Explainability Agent
---------------------
Tool   : reportlab (PDF generation library)
Purpose: Takes the outputs of all upstream agents and produces the final
         artifact set: a downloadable PDF report, a JSON report (for the
         dashboard), and the headline Trust Score.
"""

import os
import io
import json
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from crewai import Agent
from crewai.tools import tool


def compute_trust_score(
    credibility_score: float,
    hallucinated_claims: int,
    total_claims: int,
    is_safe: bool,
) -> dict:
    """
    Deterministic scoring (kept out of the LLM's hands on purpose, so the
    headline number on the dashboard is always reproducible and explainable):

      - Start at the source-credibility score (0-100).
      - Subtract points per hallucinated claim, proportional to how many
        claims were checked.
      - Apply a hard penalty (and cap) if the compliance check failed.
    """
    total_claims = max(total_claims, 1)
    hallucination_ratio = hallucinated_claims / total_claims

    score = credibility_score * (1 - 0.6 * hallucination_ratio)

    if not is_safe:
        score = min(score, 40)  # unsafe content can never score "trustworthy"

    score = max(0, min(100, round(score)))

    if score >= 80:
        risk_label, risk_emoji = "Low", "🟢"
    elif score >= 50:
        risk_label, risk_emoji = "Medium", "🟡"
    else:
        risk_label, risk_emoji = "High", "🔴"

    return {
        "trust_score": score,
        "hallucination_risk": risk_label,
        "hallucination_risk_emoji": risk_emoji,
        "hallucinated_claims": hallucinated_claims,
        "total_claims_checked": total_claims,
    }


def build_report_json(
    question: str,
    ai_answer: str,
    research_output: str,
    rag_output: str,
    fact_check_output: str,
    credibility_output: str,
    credibility_score: float,
    compliance_output: str,
    is_safe: bool,
    hallucinated_claims: int,
    total_claims: int,
    sources_count: int,
) -> dict:
    scoring = compute_trust_score(credibility_score, hallucinated_claims, total_claims, is_safe)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "ai_answer": ai_answer,
        "trust_score": scoring["trust_score"],
        "hallucination_risk": scoring["hallucination_risk"],
        "hallucination_risk_emoji": scoring["hallucination_risk_emoji"],
        "credibility_score": credibility_score,
        "is_safe": is_safe,
        "sources_count": sources_count,
        "hallucinated_claims": hallucinated_claims,
        "total_claims_checked": total_claims,
        "sections": {
            "web_research": research_output,
            "pdf_evidence": rag_output,
            "fact_check": fact_check_output,
            "source_credibility": credibility_output,
            "compliance": compliance_output,
        },
    }


def render_pdf_report(report: dict, output_path: str) -> str:
    """Renders `report` (dict from build_report_json) to a PDF at output_path."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TSTitle", parent=styles["Title"], textColor=colors.HexColor("#0F1720")
    )
    h2 = ParagraphStyle("TSH2", parent=styles["Heading2"], textColor=colors.HexColor("#1F6F63"))
    body = ParagraphStyle("TSBody", parent=styles["BodyText"], leading=15)

    story = [
        Paragraph("TruthShield AI &mdash; Trust Report", title_style),
        Spacer(1, 6),
        Paragraph(f"Generated: {report['generated_at']}", styles["Normal"]),
        Spacer(1, 12),
        HRFlowable(width="100%", color=colors.HexColor("#D8DEE4")),
        Spacer(1, 12),
        Paragraph("Question", h2),
        Paragraph(report["question"], body),
        Spacer(1, 8),
        Paragraph("AI Answer Audited", h2),
        Paragraph(report["ai_answer"].replace("\n", "<br/>"), body),
        Spacer(1, 14),
    ]

    score_table = Table(
        [
            ["Trust Score", "Hallucination Risk", "Source Credibility", "Safety"],
            [
                f"{report['trust_score']}%",
                f"{report['hallucination_risk_emoji']} {report['hallucination_risk']}",
                f"{report['credibility_score']}/100",
                "Safe" if report["is_safe"] else "Unsafe",
            ],
        ],
        colWidths=[4 * cm] * 4,
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F1720")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8DEE4")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 16))

    for heading, key in [
        ("Web Research Findings", "web_research"),
        ("PDF / Policy Evidence (RAG)", "pdf_evidence"),
        ("Fact Verification", "fact_check"),
        ("Source Credibility Breakdown", "source_credibility"),
        ("Compliance & Safety Check", "compliance"),
    ]:
        story.append(Paragraph(heading, h2))
        text = str(report["sections"][key]).replace("\n", "<br/>")
        story.append(Paragraph(text, body))
        story.append(Spacer(1, 10))

    doc.build(story)
    return output_path


@tool("PDF Report Generator")
def generate_pdf_report_tool(report_json: str) -> str:
    """
    Given a JSON string matching the TruthShield report schema (question,
    ai_answer, trust_score, sections, etc.), renders a polished PDF report to
    disk and returns the file path. Use this as the final step after all
    other agents have produced their findings.
    """
    try:
        report = json.loads(report_json)
    except json.JSONDecodeError as e:
        return f"Error: could not parse report_json ({e})"

    output_path = f"./reports/trust_report_{int(datetime.now().timestamp())}.pdf"
    path = render_pdf_report(report, output_path)
    return f"PDF report generated at: {path}"


def build_report_agent(llm=None) -> Agent:
    return Agent(
        role="Explainability Agent",
        goal=(
            "Synthesize every upstream agent's findings into one clear, "
            "well-formatted Trust Report (PDF + JSON) with a headline Trust "
            "Score that a non-technical user can understand at a glance."
        ),
        backstory=(
            "You are a technical writer specializing in AI transparency "
            "reports. You turn dense multi-agent findings into a report a "
            "compliance officer or an everyday user could both read."
        ),
        tools=[generate_pdf_report_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

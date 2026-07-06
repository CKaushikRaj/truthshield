"""
CrewAI orchestration for TruthShield AI.

Flow:
  Research Agent  -> web evidence
  PDF Evidence Agent -> RAG evidence
  Fact Verification Agent -> claim-by-claim verdicts (uses both evidence sets)
  Source Credibility Agent -> scores the URLs the Research Agent found
  Compliance Agent -> safety verdict on the original AI answer
  Explainability Agent -> synthesizes everything into the final report

Each agent owns exactly one responsibility and one tool (see agents/*.py).
"""

import os
import re
import json
from crewai import Task, Crew, Process, LLM

from agents.research_agent import build_research_agent, web_search_tool
from agents.rag_agent import build_rag_agent, pdf_search_tool, ingest_pdfs
from agents.fact_agent import build_fact_agent, claim_support_scorer_tool
from agents.credibility_agent import build_credibility_agent, credibility_scorer_tool
from agents.compliance_agent import build_compliance_agent, compliance_check_tool
from agents.report_agent import build_report_agent, build_report_json, compute_trust_score


def _get_llm():
    """
    Groq via CrewAI's LiteLLM-backed LLM class. Falls back to None (agents
    will still run their tools; only the free-text reasoning steps need an
    LLM) if no key is configured, so the API doesn't crash without one --
    it'll just report degraded functionality.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return LLM(model=f"groq/{model}", api_key=api_key, temperature=0.2)


def _count_hallucinated(fact_check_text: str) -> tuple[int, int]:
    total = len(re.findall(r"^\d+\.", fact_check_text, flags=re.MULTILINE))
    hallucinated = len(re.findall(r"LOW SUPPORT", fact_check_text))
    return hallucinated, max(total, hallucinated, 1)


def _extract_credibility_score(credibility_text: str) -> float:
    match = re.search(r"Overall credibility score:\s*(\d+)", credibility_text)
    return float(match.group(1)) if match else 50.0


def _count_sources(research_text: str) -> int:
    return len(set(re.findall(r"https?://[^\s)\]]+", research_text)))


def _is_safe(compliance_text: str) -> bool:
    return "Compliance verdict: SAFE" in compliance_text


def run_analysis(question: str, ai_answer: str, ensure_pdfs_ingested: bool = True) -> dict:
    """
    Runs the full 6-agent TruthShield pipeline for a single (question,
    ai_answer) pair and returns the final report dict (same shape the
    frontend dashboard expects).
    """
    if ensure_pdfs_ingested:
        try:
            ingest_pdfs()
        except Exception as e:  # noqa: BLE001
            print(f"[crew] PDF ingestion skipped/failed: {e}")

    llm = _get_llm()

    research_agent = build_research_agent(llm)
    rag_agent = build_rag_agent(llm)
    fact_agent = build_fact_agent(llm)
    credibility_agent = build_credibility_agent(llm)
    compliance_agent = build_compliance_agent(llm)
    report_agent = build_report_agent(llm)

    research_task = Task(
        description=(
            f"Search the web for evidence relevant to this AI-generated answer.\n\n"
            f"Original question: {question}\n"
            f"AI answer to audit: {ai_answer}\n\n"
            "Use the Web Search Tool with a focused query derived from the "
            "answer's key claims. Return the raw results (titles, URLs, "
            "snippets)."
        ),
        expected_output="A list of 3-5 web sources (title, url, snippet) relevant to the claims.",
        agent=research_agent,
    )

    rag_task = Task(
        description=(
            f"Search the trusted PDF knowledge base (AI safety, policy, WHO, "
            f"NIST/government AI guidelines) for passages relevant to this "
            f"AI-generated answer.\n\nQuestion: {question}\nAnswer: {ai_answer}\n\n"
            "Use the PDF Knowledge Base Search tool."
        ),
        expected_output="Relevant passages from the PDF knowledge base, with source filenames.",
        agent=rag_agent,
    )

    fact_task = Task(
        description=(
            f"Fact-check this AI-generated answer against the web research and "
            f"PDF evidence gathered by the other agents.\n\nAnswer to check:\n{ai_answer}\n\n"
            "First call the Claim Support Scorer tool with input formatted as:\n"
            "'<the answer text>---EVIDENCE---<web research + PDF evidence combined>'\n"
            "Then, using that heuristic PLUS your own reading of the evidence, "
            "give a final claim-by-claim verdict: Verified / Unverified / Hallucinated, "
            "with a one-line justification for each."
        ),
        expected_output=(
            "A numbered claim-by-claim verdict list (Verified/Unverified/"
            "Hallucinated) with brief justification for each claim."
        ),
        agent=fact_agent,
        context=[research_task, rag_task],
    )

    credibility_task = Task(
        description=(
            "Score the credibility of every source the Research Agent found. "
            "Use the Domain Credibility Scorer tool on the Research Agent's "
            "raw output."
        ),
        expected_output="A per-source credibility breakdown plus one overall credibility score (0-100).",
        agent=credibility_agent,
        context=[research_task],
    )

    compliance_task = Task(
        description=(
            f"Check this AI-generated answer for safety/compliance issues "
            f"(unsafe medical or financial advice, PII exposure, other unsafe "
            f"advice) using the Safety & Compliance Checker tool.\n\n"
            f"Answer to check:\n{ai_answer}"
        ),
        expected_output="A SAFE/UNSAFE verdict with any flags raised.",
        agent=compliance_agent,
    )

    report_task = Task(
        description=(
            "Read the outputs of the Research, PDF Evidence, Fact "
            "Verification, Source Credibility, and Compliance agents "
            "(provided as context) and write a concise executive summary "
            "(4-6 sentences) explaining the overall trustworthiness "
            "verdict for a non-technical user. Do not invent a numeric "
            "trust score -- that is computed separately."
        ),
        expected_output="A concise, plain-language executive summary of the trust findings.",
        agent=report_agent,
        context=[research_task, rag_task, fact_task, credibility_task, compliance_task],
    )

    crew = Crew(
        agents=[research_agent, rag_agent, fact_agent, credibility_agent, compliance_agent, report_agent],
        tasks=[research_task, rag_task, fact_task, credibility_task, compliance_task, report_task],
        process=Process.sequential,
        verbose=True,
    )

    crew.kickoff()

    research_output = str(research_task.output)
    rag_output = str(rag_task.output)
    fact_output = str(fact_task.output)
    credibility_output = str(credibility_task.output)
    compliance_output = str(compliance_task.output)
    executive_summary = str(report_task.output)

    hallucinated, total_claims = _count_hallucinated(fact_output)
    credibility_score = _extract_credibility_score(credibility_output)
    sources_count = _count_sources(research_output)
    is_safe = _is_safe(compliance_output)

    report = build_report_json(
        question=question,
        ai_answer=ai_answer,
        research_output=research_output,
        rag_output=rag_output,
        fact_check_output=fact_output,
        credibility_output=credibility_output,
        credibility_score=credibility_score,
        compliance_output=compliance_output,
        is_safe=is_safe,
        hallucinated_claims=hallucinated,
        total_claims=total_claims,
        sources_count=sources_count,
    )
    report["executive_summary"] = executive_summary
    return report

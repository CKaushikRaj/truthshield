"""
Fact Verification Agent
------------------------
Tools  : (1) a lexical claim-support scorer (fast, deterministic heuristic)
             that measures how well the web + RAG evidence actually overlaps
             with the AI answer's claims, and
         (2) the underlying LLM (Groq), which reasons over that heuristic
             plus the raw evidence to produce the final verdict per claim.
Purpose: Compares the AI-generated answer against the Research Agent's web
         evidence and the PDF Evidence Agent's RAG context, and decides,
         claim by claim, whether it is Verified / Unverified / Hallucinated.
"""

import re
from crewai import Agent
from crewai.tools import tool


def _split_claims(answer: str):
    # naive sentence splitter -- good enough for a hackathon-grade claim list
    sentences = re.split(r"(?<=[.!?])\s+", answer.strip())
    return [s for s in sentences if len(s.split()) > 3]


def _overlap_score(claim: str, evidence: str) -> float:
    claim_words = set(re.findall(r"[a-zA-Z]{4,}", claim.lower()))
    evidence_words = set(re.findall(r"[a-zA-Z]{4,}", evidence.lower()))
    if not claim_words:
        return 0.0
    return round(len(claim_words & evidence_words) / len(claim_words), 2)


@tool("Claim Support Scorer")
def claim_support_scorer_tool(answer_and_evidence: str) -> str:
    """
    Input should be a single string containing the AI answer followed by
    '---EVIDENCE---' followed by the combined web + RAG evidence text.
    Splits the answer into individual claims (sentences) and computes a
    lexical overlap score (0.0-1.0) between each claim and the evidence pool,
    as a fast heuristic signal for how well-supported each claim is. Low
    overlap (<0.2) is a strong hallucination-risk signal.
    """
    if "---EVIDENCE---" not in answer_and_evidence:
        return "Error: input must contain '---EVIDENCE---' separating answer and evidence."

    answer, evidence = answer_and_evidence.split("---EVIDENCE---", 1)
    claims = _split_claims(answer)
    if not claims:
        return "No distinct claims found in the answer to score."

    lines = []
    for i, claim in enumerate(claims, start=1):
        score = _overlap_score(claim, evidence)
        risk = "LOW SUPPORT (possible hallucination)" if score < 0.2 else (
            "PARTIAL SUPPORT" if score < 0.5 else "WELL SUPPORTED"
        )
        lines.append(f"{i}. \"{claim.strip()}\" -> overlap={score} ({risk})")

    return "\n".join(lines)


def build_fact_agent(llm=None) -> Agent:
    return Agent(
        role="Fact Verification Agent",
        goal=(
            "Compare the AI-generated answer, claim by claim, against the "
            "web research and PDF/RAG evidence, and classify each claim as "
            "Verified, Unverified, or Hallucinated."
        ),
        backstory=(
            "You are a fact-checking editor for a major newsroom. You never "
            "let a claim through without checking it against the evidence "
            "in front of you, and you clearly say when evidence is thin."
        ),
        tools=[claim_support_scorer_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

"""
Source Credibility Agent
------------------------
Tool   : Domain credibility checker (rule-based, no external API needed --
         fast and free, which matters for a live demo).
Purpose: Extracts every URL surfaced by the Research Agent and assigns each
         one a credibility score based on domain type (.gov, .edu, known
         health/science/standards bodies, etc.), then rolls that up into a
         single overall credibility percentage.
"""

import re
from urllib.parse import urlparse
from crewai import Agent
from crewai.tools import tool

# Highest-trust exact domains (well-known authoritative bodies)
TIER_1_DOMAINS = {
    "who.int": 98,
    "nasa.gov": 98,
    "nist.gov": 98,
    "cdc.gov": 97,
    "un.org": 95,
    "europa.eu": 94,
    "ieee.org": 92,
    "nature.com": 92,
    "sciencedirect.com": 88,
    "arxiv.org": 85,
}

TIER_SUFFIX_SCORES = {
    ".gov": 95,
    ".edu": 90,
    ".int": 92,
    ".mil": 90,
}

LOW_TRUST_MARKERS = ["blogspot.", "medium.com", "reddit.com", "quora.com", "pinterest."]


def _score_domain(url: str) -> int:
    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
    except Exception:  # noqa: BLE001
        return 40

    if domain in TIER_1_DOMAINS:
        return TIER_1_DOMAINS[domain]

    for suffix, score in TIER_SUFFIX_SCORES.items():
        if domain.endswith(suffix):
            return score

    for marker in LOW_TRUST_MARKERS:
        if marker in domain:
            return 35

    # Generic .com/.org/.net etc with no other signal
    if domain.endswith(".org"):
        return 65
    return 55


@tool("Domain Credibility Scorer")
def credibility_scorer_tool(research_text: str) -> str:
    """
    Extracts every URL found in `research_text` (typically the Research
    Agent's output) and scores each domain's credibility from 0-100 based on
    domain type (.gov/.edu/.int, known authoritative bodies like WHO/NASA/
    NIST, vs. low-trust user-generated platforms). Returns a breakdown plus
    an overall average credibility score.
    """
    urls = re.findall(r"https?://[^\s)\]]+", research_text)
    if not urls:
        return "No URLs found to score. Overall credibility: 50 (unverified)."

    scored = []
    for url in set(urls):
        score = _score_domain(url)
        scored.append((url, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    avg = round(sum(s for _, s in scored) / len(scored))

    lines = [f"- {url} -> {score}/100" for url, score in scored]
    return (
        "Source credibility breakdown:\n" + "\n".join(lines) +
        f"\n\nOverall credibility score: {avg}/100"
    )


def build_credibility_agent(llm=None) -> Agent:
    return Agent(
        role="Source Credibility Agent",
        goal=(
            "Evaluate the trustworthiness of every source cited by the "
            "Research Agent by scoring its domain (.gov, .edu, WHO, NASA, "
            "peer-reviewed venues score highest)."
        ),
        backstory=(
            "You are a digital literacy and misinformation-research expert "
            "who has spent years teaching people to tell authoritative "
            "sources apart from unreliable ones."
        ),
        tools=[credibility_scorer_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

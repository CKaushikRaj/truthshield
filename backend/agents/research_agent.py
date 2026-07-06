"""
Research Agent
--------------
Tool   : Tavily Search API
Purpose: Searches the web for supporting information about the AI-generated
         answer, returning a short list of (title, url, snippet) results that
         downstream agents (Fact Verification, Source Credibility) rely on.
"""

import os
from crewai import Agent
from crewai.tools import tool

try:
    from tavily import TavilyClient
except ImportError:  # pragma: no cover
    TavilyClient = None


def _get_client():
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key or TavilyClient is None:
        return None
    return TavilyClient(api_key=api_key)


@tool("Web Search Tool")
def web_search_tool(query: str) -> str:
    """
    Search the live web for evidence relevant to `query`.
    Returns a formatted string of the top results (title, url, snippet).
    Falls back to a clearly-labeled mock result if no TAVILY_API_KEY is set,
    so the rest of the pipeline still runs end-to-end during a demo.
    """
    client = _get_client()
    if client is None:
        return (
            "[MOCK RESULT - no TAVILY_API_KEY configured]\n"
            f"Query: {query}\n"
            "1. Title: Example placeholder source\n"
            "   URL: https://example.com/placeholder\n"
            "   Snippet: This is placeholder evidence. Add a real TAVILY_API_KEY "
            "in your .env to get live web search results.\n"
        )

    try:
        results = client.search(query=query, max_results=5, search_depth="advanced")
        formatted = []
        for i, r in enumerate(results.get("results", []), start=1):
            formatted.append(
                f"{i}. Title: {r.get('title')}\n"
                f"   URL: {r.get('url')}\n"
                f"   Snippet: {r.get('content', '')[:400]}\n"
            )
        return "\n".join(formatted) if formatted else "No web results found."
    except Exception as e:  # noqa: BLE001
        return f"[Research Agent error calling Tavily: {e}]"


def build_research_agent(llm=None) -> Agent:
    return Agent(
        role="Research Agent",
        goal=(
            "Search the live web for evidence that supports or contradicts the "
            "AI-generated answer being audited."
        ),
        backstory=(
            "You are a meticulous open-source-intelligence researcher. You never "
            "accept a claim at face value -- you go find independent, current "
            "sources for it."
        ),
        tools=[web_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

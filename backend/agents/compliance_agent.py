"""
Compliance Agent
----------------
Tool   : OpenAI Moderation API when OPENAI_API_KEY is configured, otherwise a
         built-in rule-based safety classifier (keeps the demo fully
         functional without an OpenAI key, since the rest of the stack runs
         on Groq).
Purpose: Flags whether the AI-generated answer contains unsafe medical /
         financial advice, exposed PII, or other unsafe-advice categories.
"""

import os
import re
from crewai import Agent
from crewai.tools import tool

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone": r"\b\d{10}\b|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b",
    "ssn_or_aadhaar": r"\b\d{3}-\d{2}-\d{4}\b|\b\d{4}\s?\d{4}\s?\d{4}\b",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
}

MEDICAL_RISK_TERMS = [
    "stop taking your medication", "cure cancer", "guaranteed to cure",
    "do not need a doctor", "self-medicate", "double your dose",
]
FINANCIAL_RISK_TERMS = [
    "guaranteed returns", "risk-free investment", "insider tip",
    "cannot lose money", "put your life savings",
]
UNSAFE_ADVICE_TERMS = [
    "ignore safety warning", "bypass the safety", "how to make a weapon",
    "how to synthesize", "hack into",
]


def _rule_based_check(text: str) -> dict:
    lower = text.lower()
    flags = []

    for label, pattern in PII_PATTERNS.items():
        if re.search(pattern, text):
            flags.append(f"Possible PII exposure: {label}")

    for term in MEDICAL_RISK_TERMS:
        if term in lower:
            flags.append(f"Unsafe medical advice pattern: '{term}'")

    for term in FINANCIAL_RISK_TERMS:
        if term in lower:
            flags.append(f"Unsafe financial advice pattern: '{term}'")

    for term in UNSAFE_ADVICE_TERMS:
        if term in lower:
            flags.append(f"Unsafe advice pattern: '{term}'")

    is_safe = len(flags) == 0
    return {"safe": is_safe, "flags": flags, "method": "rule-based"}


def _openai_moderation_check(text: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return _rule_based_check(text)

    try:
        client = OpenAI(api_key=api_key)
        result = client.moderations.create(input=text)
        r = result.results[0]
        flags = [cat for cat, flagged in r.categories.model_dump().items() if flagged]
        rule_flags = _rule_based_check(text)["flags"]  # still catch PII/medical/financial
        return {
            "safe": (not r.flagged) and len(rule_flags) == 0,
            "flags": flags + rule_flags,
            "method": "openai-moderation + rule-based",
        }
    except Exception as e:  # noqa: BLE001
        result = _rule_based_check(text)
        result["flags"].append(f"(OpenAI moderation call failed, used fallback: {e})")
        return result


@tool("Safety & Compliance Checker")
def compliance_check_tool(answer_text: str) -> str:
    """
    Checks `answer_text` (the AI-generated answer being audited) for unsafe
    medical advice, unsafe financial advice, exposed PII, and other unsafe
    advice patterns. Uses OpenAI Moderation if OPENAI_API_KEY is set,
    otherwise a built-in rule-based safety classifier. Returns a safety
    verdict and any flags raised.
    """
    result = _openai_moderation_check(answer_text)
    verdict = "SAFE" if result["safe"] else "UNSAFE"
    flags_text = "\n".join(f"- {f}" for f in result["flags"]) or "None"
    return (
        f"Compliance verdict: {verdict}\n"
        f"Method: {result['method']}\n"
        f"Flags:\n{flags_text}"
    )


def build_compliance_agent(llm=None) -> Agent:
    return Agent(
        role="Compliance Agent",
        goal=(
            "Determine whether the AI-generated answer is safe to show a "
            "user, screening for unsafe medical or financial advice, exposed "
            "PII, and other unsafe-advice patterns."
        ),
        backstory=(
            "You are a risk & compliance officer for a healthcare and "
            "fintech-adjacent AI product. You are conservative: when in "
            "doubt, you flag it."
        ),
        tools=[compliance_check_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

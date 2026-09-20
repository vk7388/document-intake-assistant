"""
LLM extraction layer.

Job of this module: read a free-text user message (plus a little context
about what's still missing) and return STRUCTURED JSON matching
ExtractionResult. It never touches application state directly - main.py
validates the JSON with Pydantic and passes it to state.update_state().

    user message -> LLM (or fallback) -> raw JSON -> Pydantic validation -> state

If OPENAI_API_KEY is not set (e.g. during grading / offline testing), we
fall back to a deterministic rule-based extractor so the app still works
end-to-end without network access. This also makes the extraction logic
unit-testable without hitting a real API.
"""

import json
import os
import re
from typing import Optional

from dotenv import load_dotenv

from models import ExtractionResult

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are an information-extraction engine for a personal
wishes document intake form. Given the user's latest message and the list
of fields still missing, extract ONLY the fields the user actually
mentioned. Do not guess or invent values.

Return ONLY a JSON object with these keys (omit or null any key not
mentioned in the message):
full_name (string)
home_address (string)
covers_worldwide_assets (boolean)
has_children (boolean)
children (array of strings)
executor_name (string)
executor_relationship (string)
specific_gifts (array of strings)
additional_wishes (string)
clarification_needed (string - set ONLY if the message is ambiguous or
self-contradictory and you cannot confidently extract a field; describe
what needs clarifying)

Return raw JSON only. No markdown fences, no commentary.
"""


def _call_openai(user_message: str, missing_fields: list) -> Optional[dict]:
    """Real LLM call. Returns None on any failure so the caller can fall back."""
    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Still missing: {missing_fields}\n\nUser message: {user_message}",
                },
            ],
            temperature=0,
        )
        raw = completion.choices[0].message.content
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(raw)
    except Exception:
        # Network error, bad key, malformed JSON, etc. -> caller falls back.
        return None


# ---------------------------------------------------------------------------
# Deterministic fallback extractor (also used directly by the unit tests).
# ---------------------------------------------------------------------------

_UNKNOWN_PATTERNS = [
    r"\bi don'?t know\b",
    r"\bnot sure\b",
    r"\bskip\b",
    r"\bno idea\b",
]

_NAME_TOKEN = r"[A-Za-z][A-Za-z.'-]*(?:\s[A-Za-z][A-Za-z.'-]*){0,3}"
_NAME_PATTERNS = [
    rf"(?:actually,?\s*)?my (?:full )?name is ({_NAME_TOKEN})(?:\s+and\b|\s+who\b|,|\.|$)",
    rf"^i am ({_NAME_TOKEN})(?:\s+and\b|\s+who\b|,|\.|$)",
    rf"^i'?m ({_NAME_TOKEN})(?:\s+and\b|\s+who\b|,|\.|$)",
]

_ADDRESS_PATTERNS = [
    r"my (?:home )?address is ([A-Za-z0-9,.\- ]+)",
    r"i live in ([A-Za-z0-9,.\- ]+)",
]

_EXECUTOR_PATTERNS = [
    r"(?:executor is|appoint) ([A-Za-z][A-Za-z .'-]*?)(?:,| as| who)? ?(?:my|as my)? ?([A-Za-z]+)?$",
]

_GIFT_PATTERNS = [
    r"(?:leave|give) (.+?) to ([A-Za-z][A-Za-z .'-]*)",
]


def _matches_any(patterns, text):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m
    return None


def _split_names(fragment: str):
    fragment = re.sub(r"\band\b", ",", fragment, flags=re.IGNORECASE)
    parts = [p.strip(" .") for p in fragment.split(",")]
    return [p for p in parts if p]


def extract_information_fallback(user_message: str, missing_fields: Optional[list] = None) -> dict:
    """Rule-based extractor. Deterministic, offline, used as a safety net
    and directly exercised by the unit tests."""
    text = user_message.strip()
    result: dict = {}

    if _matches_any(_UNKNOWN_PATTERNS, text):
        # User explicitly doesn't know / wants to skip - extract nothing,
        # don't invent a value. Caller will just re-ask or move on.
        return result

    # Name (correction phrasing like "actually, my full name is X" is
    # handled by the same pattern - overwriting is handled in state.py).
    m = _matches_any(_NAME_PATTERNS, text)
    if m:
        result["full_name"] = m.group(1).strip(" .")

    # Address
    m = _matches_any(_ADDRESS_PATTERNS, text)
    if m:
        result["home_address"] = m.group(1).strip(" .")
    elif missing_fields and "home_address" in missing_fields and re.match(
        r"^[A-Za-z0-9,.\- ]{2,60}$", text
    ) and not m and "name" not in text.lower():
        # If we just asked for the address and got a short free-text
        # answer with no other recognizable pattern, treat it as the address.
        if not _matches_any(_NAME_PATTERNS + _EXECUTOR_PATTERNS, text):
            result["home_address"] = text

    # Worldwide assets (yes/no style question)
    if missing_fields and "covers_worldwide_assets" in missing_fields:
        if re.search(r"\byes\b", text, re.IGNORECASE):
            result["covers_worldwide_assets"] = True
        elif re.search(r"\bno\b", text, re.IGNORECASE):
            result["covers_worldwide_assets"] = False

    # Children
    children_match = re.search(
        r"(?:children are|kids are|children[:,]?)\s*([A-Za-z ,'&-]+)", text, re.IGNORECASE
    )
    has_children_yes = re.search(r"\byes\b.*child", text, re.IGNORECASE) or children_match
    has_children_no = re.search(r"\bno\b.*child|no children|don'?t have (?:any )?children", text, re.IGNORECASE)

    if has_children_no:
        result["has_children"] = False
        result["children"] = []
    elif children_match:
        result["has_children"] = True
        result["children"] = _split_names(children_match.group(1))
    elif missing_fields and "has_children" in missing_fields:
        if re.search(r"^\s*yes\b", text, re.IGNORECASE):
            result["has_children"] = True
        elif re.search(r"^\s*no\b", text, re.IGNORECASE):
            result["has_children"] = False
            result["children"] = []

    # Executor
    m = re.search(
        r"(?:executor(?: is)?|appoint) ([A-Za-z][A-Za-z .'-]*?)(?:,? (?:my|as my) ([a-zA-Z]+))?$",
        text,
        re.IGNORECASE,
    )
    if m:
        result["executor_name"] = m.group(1).strip(" .")
        if m.group(2):
            result["executor_relationship"] = m.group(2).strip(" .")
    elif missing_fields and "executor" in missing_fields:
        m2 = re.search(r"([A-Za-z][A-Za-z .'-]*?),?\s*(?:my|as my)?\s*([a-zA-Z]+)?$", text)
        if m2 and len(text.split()) <= 6:
            result["executor_name"] = m2.group(1).strip(" .")
            if m2.group(2) and m2.group(2).lower() not in ("my",):
                result["executor_relationship"] = m2.group(2).strip(" .")

    # Gifts
    m = _matches_any(_GIFT_PATTERNS, text)
    if m:
        result["specific_gifts"] = [f"{m.group(1).strip()} to {m.group(2).strip()}"]
    elif missing_fields and "specific_gifts" in missing_fields and re.search(
        r"\bnone\b|\bnothing\b|\bno specific\b", text, re.IGNORECASE
    ):
        result["specific_gifts"] = []

    # Additional wishes: if that's the only thing left and nothing else matched
    if (
        missing_fields
        and missing_fields == ["additional_wishes"]
        and not result
        and text
    ):
        result["additional_wishes"] = text

    return result


def extract_information(user_message: str, missing_fields: Optional[list] = None) -> dict:
    """Public entry point used by main.py. Tries the real LLM first (if
    configured), falls back to the deterministic rule-based extractor."""
    missing_fields = missing_fields or []
    llm_result = _call_openai(user_message, missing_fields)
    if llm_result is not None:
        return llm_result
    return extract_information_fallback(user_message, missing_fields)

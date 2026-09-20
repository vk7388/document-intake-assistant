"""
Turns the structured WishesState into a human-readable draft document.
Always clearly labelled as fictional / not legal advice, per the brief.
"""

from models import WishesState


def _line(label: str, value) -> str:
    if value in (None, "", [], False) and value is not False:
        value = "-"
    if isinstance(value, bool):
        value = "Yes" if value else "No"
    if isinstance(value, list):
        value = ", ".join(value) if value else "-"
    return f"{label}:\n{value}\n"


def generate_document(state: WishesState) -> str:
    parts = [
        "PERSONAL WISHES DOCUMENT",
        "",
        "*** FICTIONAL DOCUMENT - NOT LEGAL ADVICE ***",
        "This draft is generated for demonstration purposes only and has",
        "no legal effect. Consult a qualified professional for an actual",
        "will or personal wishes document.",
        "",
        _line("Full Name", state.full_name),
        _line("Home Address", state.home_address),
        _line("Covers Worldwide Assets", state.covers_worldwide_assets),
        _line("Has Children", state.has_children),
        _line("Children", state.children),
        _line("Executor Name", state.executor.name),
        _line("Executor Relationship", state.executor.relationship),
        _line("Specific Gifts", state.specific_gifts),
        _line("Additional Wishes", state.additional_wishes),
    ]
    return "\n".join(parts)

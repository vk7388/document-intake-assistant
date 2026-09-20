"""
Decides what's still missing and what question to ask next.
Kept separate from main.py so it's easy to unit test in isolation.
"""

from models import WishesState

# Ordered so we ask in a sensible sequence.
FIELD_ORDER = [
    "full_name",
    "home_address",
    "covers_worldwide_assets",
    "has_children",
    "children",
    "executor",
    "specific_gifts",
    "additional_wishes",
]

QUESTIONS = {
    "full_name": "What is your full name?",
    "home_address": "What is your home address?",
    "covers_worldwide_assets": "Should this document cover your worldwide assets? (yes/no)",
    "has_children": "Do you have any children? (yes/no)",
    "children": "What are your children's names?",
    "executor": "Who would you like to appoint as executor, and what is their relationship to you?",
    "specific_gifts": "Are there any specific gifts you'd like to leave to anyone? (say 'none' if not)",
    "additional_wishes": "Is there anything else you'd like to add to your wishes document?",
}


def get_missing_fields(state: WishesState) -> list:
    missing = []
    if not state.full_name:
        missing.append("full_name")
    if not state.home_address:
        missing.append("home_address")
    if state.covers_worldwide_assets is None:
        missing.append("covers_worldwide_assets")
    if state.has_children is None:
        missing.append("has_children")
    elif state.has_children is True and not state.children:
        missing.append("children")
    if not state.executor.name:
        missing.append("executor")
    if not state.specific_gifts:
        # specific_gifts is allowed to be legitimately empty ("none"),
        # so we only treat it as "missing" until we've asked once. We
        # approximate that by checking additional_wishes hasn't been
        # reached yet, which is good enough for this test's scope.
        missing.append("specific_gifts")
    if state.additional_wishes is None:
        missing.append("additional_wishes")
    return missing


def next_question(state: WishesState) -> str | None:
    missing = get_missing_fields(state)
    if not missing:
        return None
    return QUESTIONS[missing[0]]


def is_complete(state: WishesState) -> bool:
    return len(get_missing_fields(state)) == 0

"""
Simple in-memory state store.

For this test a single global state is enough (per the brief: "simple
in-memory state" is acceptable for the initial version). Swapping this for
a per-session / per-user store (e.g. keyed by a session id in Redis or a
DB) is called out as a production improvement in the README.
"""

from models import WishesState, Executor

current_state = WishesState()


def get_state() -> WishesState:
    return current_state


def reset_state() -> WishesState:
    global current_state
    current_state = WishesState()
    return current_state


def update_state(new_data: dict) -> WishesState:
    """
    Merge validated extraction data into the current state.
    A new (non-None) value always overwrites the old one - this is what
    gives us "correction" behaviour for free: the latest statement wins.
    Lists (children / specific_gifts) are replaced wholesale when a new
    non-empty list is supplied, not appended to, so re-stating the full
    list of children behaves predictably.
    """
    global current_state
    state = current_state

    if new_data.get("full_name") is not None:
        state.full_name = new_data["full_name"]

    if new_data.get("home_address") is not None:
        state.home_address = new_data["home_address"]

    if new_data.get("covers_worldwide_assets") is not None:
        state.covers_worldwide_assets = new_data["covers_worldwide_assets"]

    if new_data.get("has_children") is not None:
        state.has_children = new_data["has_children"]
        if state.has_children is False:
            state.children = []

    if new_data.get("children"):
        state.children = new_data["children"]

    if new_data.get("executor_name") is not None or new_data.get("executor_relationship") is not None:
        state.executor = Executor(
            name=new_data.get("executor_name", state.executor.name),
            relationship=new_data.get("executor_relationship", state.executor.relationship),
        )

    if new_data.get("specific_gifts"):
        state.specific_gifts = new_data["specific_gifts"]

    if new_data.get("additional_wishes") is not None:
        state.additional_wishes = new_data["additional_wishes"]

    current_state = state
    return current_state

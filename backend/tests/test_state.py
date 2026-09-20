import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from models import WishesState, ExtractionResult
from state import update_state, reset_state
from llm import extract_information_fallback
from document import generate_document
from conversation import get_missing_fields, next_question, is_complete


@pytest.fixture(autouse=True)
def _reset():
    reset_state()
    yield
    reset_state()


def test_normal_extraction_name():
    result = extract_information_fallback("My name is Rahul Sharma")
    assert result.get("full_name") == "Rahul Sharma"


def test_multiple_fields_extraction():
    result = extract_information_fallback(
        "I'm Rahul and my children are Amit and Riya", missing_fields=["full_name", "children"]
    )
    assert result.get("children") == ["Amit", "Riya"]
    assert result.get("has_children") is True


def test_state_update_applies_extraction():
    update_state({"full_name": "Rahul Sharma"})
    state = update_state({})
    assert state.full_name == "Rahul Sharma"


def test_correction_overwrites_previous_value():
    update_state({"full_name": "Rahul Sharma"})
    result = extract_information_fallback("Actually, my full name is Rahul Raj Sharma")
    assert result.get("full_name") == "Rahul Raj Sharma"
    state = update_state(result)
    assert state.full_name == "Rahul Raj Sharma"


def test_unknown_information_does_not_invent_data():
    result = extract_information_fallback("I don't know", missing_fields=["home_address"])
    assert result == {}
    state = update_state(result)
    assert state.home_address is None


def test_malformed_extraction_result_is_rejected_safely():
    with pytest.raises(Exception):
        ExtractionResult(covers_worldwide_assets="not-a-boolean")


def test_children_replace_not_append():
    update_state({"children": ["Amit"]})
    state = update_state({"children": ["Amit", "Riya"]})
    assert state.children == ["Amit", "Riya"]


def test_missing_fields_detects_full_name_first():
    missing = get_missing_fields(WishesState())
    assert missing[0] == "full_name"


def test_next_question_returns_none_when_complete():
    from models import Executor

    complete_state = WishesState(
        full_name="Rahul Sharma",
        home_address="Pune",
        covers_worldwide_assets=True,
        has_children=False,
        children=[],
        executor=Executor(name="James", relationship="Brother"),
        specific_gifts=[],
        additional_wishes="None",
    )
    assert is_complete(complete_state)
    assert next_question(complete_state) is None


def test_document_contains_disclaimer_and_name():
    update_state({"full_name": "Rahul Sharma"})
    state = update_state({})
    doc = generate_document(state)
    assert "NOT LEGAL ADVICE" in doc
    assert "Rahul Sharma" in doc

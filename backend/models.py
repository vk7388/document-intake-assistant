"""
Structured schema for the Personal Wishes Document intake.
This is the single source of truth for what has been collected so far.
The LLM never edits this directly - it only returns JSON that we validate
against this schema before applying it to state.
"""

from typing import Optional, List
from pydantic import BaseModel, field_validator


class Executor(BaseModel):
    name: Optional[str] = None
    relationship: Optional[str] = None


class WishesState(BaseModel):
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    covers_worldwide_assets: Optional[bool] = None
    has_children: Optional[bool] = None
    children: List[str] = []
    executor: Executor = Executor()
    specific_gifts: List[str] = []
    additional_wishes: Optional[str] = None

    @field_validator("children", "specific_gifts", mode="before")
    @classmethod
    def _no_none_in_list(cls, v):
        if v is None:
            return []
        return v


class ExtractionResult(BaseModel):
    """What we ask the LLM (or the fallback extractor) to return."""
    full_name: Optional[str] = None
    home_address: Optional[str] = None
    covers_worldwide_assets: Optional[bool] = None
    has_children: Optional[bool] = None
    children: Optional[List[str]] = None
    executor_name: Optional[str] = None
    executor_relationship: Optional[str] = None
    specific_gifts: Optional[List[str]] = None
    additional_wishes: Optional[str] = None
    clarification_needed: Optional[str] = None  # set when input is ambiguous/contradictory


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    reply: str
    state: WishesState
    document: str
    is_complete: bool

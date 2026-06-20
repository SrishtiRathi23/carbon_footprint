"""Follow-up assistant endpoint.

POST /api/ask -> answer a user's follow-up question, grounded in the route
comparison the frontend already received. Uses Gemini for the natural-language
answer; the carbon numbers it cites come from the deterministic comparison.
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from deps import rate_limit
from services.gemini_client import answer_followup

logger = logging.getLogger(__name__)
router = APIRouter()

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
MAX_QUESTION_LENGTH = 500


class AskRequest(BaseModel):
    question: str = Field(..., description="The user's follow-up question")
    context: dict = Field(default_factory=dict, description="Comparison result")


@router.post("/api/ask", dependencies=[Depends(rate_limit)])
def ask(payload: AskRequest) -> dict:
    """Return a grounded natural-language answer to a follow-up question."""
    question = _CONTROL.sub("", payload.question or "").strip()
    if not question:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Question must not be empty")
    if len(question) > MAX_QUESTION_LENGTH:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Question must be at most {MAX_QUESTION_LENGTH} characters",
        )

    # Only trust the option list from the supplied context; ignore anything else.
    options = payload.context.get("options", [])
    if not isinstance(options, list):
        options = []
    context = {"options": options}
    try:
        answer = answer_followup(question, context)
    except Exception as exc:  # noqa: BLE001 - never leak internals / never 500
        logger.error("Follow-up answer failed: %s", exc)
        answer = "Sorry, the assistant could not answer that right now. Please try again."
    return {"answer": answer}

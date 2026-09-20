from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from state import get_state, update_state, reset_state
from models import MessageRequest, MessageResponse, ExtractionResult
from llm import extract_information
from document import generate_document
from conversation import get_missing_fields, next_question, is_complete

app = FastAPI(title="Document Intake Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Document Intake Assistant API is running"}


@app.get("/api/state")
def get_current_state():
    return get_state()


@app.get("/api/document")
def get_document():
    return {"document": generate_document(get_state())}


@app.post("/api/reset")
def reset():
    state = reset_state()
    return {"state": state, "reply": next_question(state)}


@app.post("/api/message", response_model=MessageResponse)
def post_message(payload: MessageRequest):
    state = get_state()
    missing_before = get_missing_fields(state)

    try:
        raw = extract_information(payload.message, missing_before)
        # Validate the LLM/fallback output against our schema before it
        # ever touches application state. Unknown/garbage keys are dropped,
        # wrong types raise and we fail safe (state untouched).
        validated = ExtractionResult(**{k: v for k, v in raw.items() if k in ExtractionResult.model_fields})
    except Exception:
        # Malformed LLM output (bad JSON, wrong types, etc). Don't crash,
        # don't touch state, ask the user to rephrase.
        state = get_state()
        return MessageResponse(
            reply="Sorry, I had trouble understanding that. Could you rephrase?",
            state=state,
            document=generate_document(state),
            is_complete=is_complete(state),
        )

    if validated.clarification_needed:
        return MessageResponse(
            reply=validated.clarification_needed,
            state=state,
            document=generate_document(state),
            is_complete=is_complete(state),
        )

    update_state(validated.model_dump(exclude={"clarification_needed"}, exclude_none=True))
    state = get_state()

    question = next_question(state)
    if question is None:
        reply = "Thanks! I have everything I need. Here's your document preview below."
    else:
        reply = question

    return MessageResponse(
        reply=reply,
        state=state,
        document=generate_document(state),
        is_complete=is_complete(state),
    )

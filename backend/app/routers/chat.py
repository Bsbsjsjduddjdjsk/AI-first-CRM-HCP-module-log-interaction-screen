from fastapi import APIRouter, HTTPException

from .. import schemas
from ..agent.graph import agent_graph
from ..agent.tools import log_interaction_tool, edit_interaction_tool

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/message", response_model=schemas.ChatAgentResponse)
def send_message(payload: schemas.ChatMessage):
    """Send a chat message to the LangGraph agent. Returns the agent's reply
    and, if it built a draft interaction/edit, a structured preview the
    frontend renders as a confirmation card."""
    config = {"configurable": {"thread_id": payload.session_id}}
    result = agent_graph.invoke(
        {
            "session_id": payload.session_id,
            "rep_id": payload.rep_id,
            "messages": [{"role": "user", "content": payload.message}],
        },
        config=config,
    )

    return schemas.ChatAgentResponse(
        session_id=payload.session_id,
        agent_message=result.get("agent_reply", ""),
        proposed_action=result.get("intent"),
        structured_preview=result.get("draft_record"),
        requires_confirmation=result.get("awaiting_confirmation", False),
        interaction_id=result.get("target_interaction_id"),
    )


@router.post("/confirm", response_model=dict)
def confirm_action(payload: schemas.ConfirmAction):
    """Rep approves (or edits-then-approves) the agent's proposed draft.
    This is the human-in-the-loop commit step -- nothing is persisted to the
    DB from a chat turn until this endpoint is called."""
    config = {"configurable": {"thread_id": payload.session_id}}
    snapshot = agent_graph.get_state(config)
    state = snapshot.values

    if not payload.approved:
        return {"status": "discarded"}

    draft = payload.edited_payload or state.get("draft_record")
    if not draft:
        raise HTTPException(status_code=400, detail="No pending draft to confirm")

    intent = state.get("intent")
    if intent == "log_interaction":
        result = log_interaction_tool.invoke({
            "rep_id": payload.rep_id,
            "structured_payload": draft,
            "hcp_id": draft.get("hcp_id"),
            "created_via": "chat",
            "confirmed": True,
        })
        return result

    if intent == "edit_interaction":
        result = edit_interaction_tool.invoke({
            "interaction_id": state.get("target_interaction_id"),
            "edited_by": payload.rep_id,
            "fields": draft,
            "confirmed": True,
        })
        return result

    raise HTTPException(status_code=400, detail="No confirmable action pending")

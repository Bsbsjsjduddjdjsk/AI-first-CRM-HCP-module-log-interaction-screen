import json

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .llm import fast_llm
from .tools import (
    log_interaction_tool,
    edit_interaction_tool,
    fetch_hcp_history_tool,
    schedule_follow_up_tool,
    compliance_flag_check_tool,
    suggest_next_best_action_tool,
)

ROUTER_PROMPT = """Classify the field representative's message into exactly one intent:
- log_interaction: describing a new HCP visit/call/email to record
- edit_interaction: correcting or changing something already logged
- query_history: asking about past interactions with an HCP
- schedule_follow_up: explicitly asking to set/confirm a follow-up/reminder
- other: anything else / small talk / unclear

Message: "{message}"

Return ONLY the intent word, nothing else.
"""


def route_intent(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"]
    resp = fast_llm.invoke(ROUTER_PROMPT.format(message=last_message))
    intent = resp.content.strip().lower()
    valid = {"log_interaction", "edit_interaction", "query_history", "schedule_follow_up", "other"}
    if intent not in valid:
        intent = "other"
    return {"intent": intent}


def handle_log_interaction(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"]
    result = log_interaction_tool.invoke({
        "rep_id": state["rep_id"],
        "raw_message": last_message,
        "created_via": "chat",
        "confirmed": False,
    })

    if result["status"] == "needs_clarification":
        return {
            "agent_reply": result["message"],
            "awaiting_confirmation": False,
            "draft_record": result.get("extracted"),
        }

    preview = result["preview"]
    reply = (
        f"Here's what I'll log for {preview['hcp_name']}: "
        f"{preview['interaction_type']} on {preview['occurred_at']}, "
        f"products: {', '.join(p if isinstance(p, str) else p.get('product_name','') for p in preview['products_discussed']) or 'none'}. "
        f"Summary: {preview['key_discussion_points']}. "
        f"Reply 'confirm' to save, or tell me what to change."
    )
    return {
        "draft_record": preview,
        "agent_reply": reply,
        "awaiting_confirmation": True,
    }


def handle_edit_interaction(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"]
    target_id = state.get("target_interaction_id")
    if not target_id:
        return {
            "agent_reply": "Which interaction would you like to edit? Please provide the interaction ID or select it from the log.",
            "awaiting_confirmation": False,
        }

    result = edit_interaction_tool.invoke({
        "interaction_id": target_id,
        "edited_by": state["rep_id"],
        "raw_correction_text": last_message,
        "confirmed": False,
    })

    if result["status"] == "no_changes_detected":
        return {"agent_reply": "I couldn't detect a specific change -- could you rephrase the correction?"}

    reply = f"I'll update: {json.dumps(result['proposed_changes'])}. Reply 'confirm' to save."
    return {
        "draft_record": result["proposed_changes"],
        "agent_reply": reply,
        "awaiting_confirmation": True,
    }


def handle_query_history(state: AgentState) -> AgentState:
    last_message = state["messages"][-1]["content"]
    # naive name extraction; production version would reuse the extraction LLM
    result = fetch_hcp_history_tool.invoke({"hcp_name": last_message})
    if result.get("status") != "ok":
        return {"agent_reply": "I couldn't find that HCP -- could you give me their full name?"}

    lines = [
        f"- {i['occurred_at'][:10]}: {i['interaction_type']}, sentiment {i['sentiment']}"
        for i in result["recent_interactions"]
    ]
    reply = f"Recent history for {result['hcp_profile']['full_name']}:\n" + "\n".join(lines)
    return {"agent_reply": reply, "hcp_context": result, "awaiting_confirmation": False}


def handle_schedule_follow_up(state: AgentState) -> AgentState:
    draft = state.get("draft_record") or {}
    if not state.get("target_interaction_id") and not draft.get("interaction_id"):
        return {"agent_reply": "I need a logged interaction to attach the follow-up to first."}
    return {
        "agent_reply": "Got it -- I'll set that follow-up once the interaction is confirmed and saved.",
        "awaiting_confirmation": False,
    }


def handle_other(state: AgentState) -> AgentState:
    return {
        "agent_reply": "I can help you log an interaction, edit one, check an HCP's history, "
                       "or set a follow-up. What would you like to do?",
        "awaiting_confirmation": False,
    }


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("route_intent", route_intent)
    graph.add_node("log_interaction", handle_log_interaction)
    graph.add_node("edit_interaction", handle_edit_interaction)
    graph.add_node("query_history", handle_query_history)
    graph.add_node("schedule_follow_up", handle_schedule_follow_up)
    graph.add_node("other", handle_other)

    graph.set_entry_point("route_intent")

    graph.add_conditional_edges(
        "route_intent",
        lambda state: state["intent"],
        {
            "log_interaction": "log_interaction",
            "edit_interaction": "edit_interaction",
            "query_history": "query_history",
            "schedule_follow_up": "schedule_follow_up",
            "other": "other",
        },
    )

    for node in ["log_interaction", "edit_interaction", "query_history", "schedule_follow_up", "other"]:
        graph.add_edge(node, END)

    checkpointer = MemorySaver()  # swap for a Postgres checkpointer in production
    return graph.compile(checkpointer=checkpointer)


agent_graph = build_graph()

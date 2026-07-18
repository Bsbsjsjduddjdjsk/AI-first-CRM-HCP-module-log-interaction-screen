"""
The five tools the LangGraph agent uses for HCP sales activities.

Each is a plain Python function decorated with @tool so it can be bound to the
LLM for function-calling, AND called directly by graph nodes when the intent
is already known (e.g. after the router has decided "log_interaction").
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal
from .llm import fast_llm, reasoning_llm

# ---------------------------------------------------------------------------
# Shared extraction schema used when parsing free-text chat into a structured
# interaction record.
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are a pharma CRM assistant. Extract a structured HCP \
interaction record from the field representative's message.

Return ONLY valid JSON (no markdown fences, no commentary) matching this schema:
{{
  "hcp_name": string or null,
  "interaction_type": one of ["visit","call","email","event","virtual_meeting"] or null,
  "occurred_at": ISO 8601 datetime string or null (assume today if "today" is mentioned),
  "duration_minutes": integer or null,
  "products_discussed": [string, ...],
  "key_discussion_points": string (2-3 sentence summary in your own words),
  "samples_distributed": [{{"product_name": string, "quantity": integer}}, ...],
  "hcp_sentiment": one of ["positive","neutral","negative"] or null,
  "follow_up_needed": boolean,
  "follow_up_notes": string or null
}}

Current datetime for relative date resolution: {now}

Representative's message:
\"\"\"{message}\"\"\"
"""


def _llm_extract_interaction(message: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(now=datetime.utcnow().isoformat(), message=message)
    resp = fast_llm.invoke(prompt)
    text = resp.content.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fall back to a minimal safe structure rather than crash the turn
        return {
            "hcp_name": None,
            "interaction_type": None,
            "occurred_at": None,
            "duration_minutes": None,
            "products_discussed": [],
            "key_discussion_points": message,
            "samples_distributed": [],
            "hcp_sentiment": None,
            "follow_up_needed": False,
            "follow_up_notes": None,
        }


def _resolve_hcp(db: Session, hcp_name: Optional[str], hcp_id: Optional[str]) -> Optional[models.HCP]:
    if hcp_id:
        return db.query(models.HCP).filter(models.HCP.id == hcp_id).first()
    if hcp_name:
        return (
            db.query(models.HCP)
            .filter(models.HCP.full_name.ilike(f"%{hcp_name}%"))
            .first()
        )
    return None


# ---------------------------------------------------------------------------
# Tool 1: log_interaction
# ---------------------------------------------------------------------------
@tool("log_interaction")
def log_interaction_tool(
    rep_id: str,
    raw_message: Optional[str] = None,
    structured_payload: Optional[dict] = None,
    hcp_id: Optional[str] = None,
    hcp_name: Optional[str] = None,
    created_via: str = "chat",
    confirmed: bool = False,
) -> dict:
    """
    Log a new HCP interaction. If `raw_message` is given (chat path), uses the
    LLM to extract a structured record. If `structured_payload` is given (form
    path), uses it directly. Does NOT persist unless `confirmed=True` --
    otherwise returns a preview for the rep to confirm (human-in-the-loop).
    """
    db = SessionLocal()
    try:
        if structured_payload:
            extracted = structured_payload
        else:
            extracted = _llm_extract_interaction(raw_message or "")

        hcp = _resolve_hcp(db, hcp_name or extracted.get("hcp_name"), hcp_id)
        if not hcp:
            return {
                "status": "needs_clarification",
                "reason": "hcp_not_found",
                "message": f"Couldn't find an HCP matching "
                           f"'{hcp_name or extracted.get('hcp_name')}'. Please confirm the HCP.",
                "extracted": extracted,
            }

        preview = {
            "hcp_id": hcp.id,
            "hcp_name": hcp.full_name,
            "interaction_type": extracted.get("interaction_type") or "visit",
            "occurred_at": extracted.get("occurred_at") or datetime.utcnow().isoformat(),
            "duration_minutes": extracted.get("duration_minutes"),
            "products_discussed": extracted.get("products_discussed", []),
            "key_discussion_points": extracted.get("key_discussion_points"),
            "samples_distributed": extracted.get("samples_distributed", []),
            "hcp_sentiment": extracted.get("hcp_sentiment"),
            "follow_up_needed": extracted.get("follow_up_needed", False),
            "follow_up_notes": extracted.get("follow_up_notes"),
        }

        if not confirmed:
            return {"status": "pending_confirmation", "preview": preview}

        interaction = models.Interaction(
            hcp_id=hcp.id,
            rep_id=rep_id,
            interaction_type=preview["interaction_type"],
            occurred_at=datetime.fromisoformat(preview["occurred_at"]),
            duration_minutes=preview["duration_minutes"],
            products_discussed=preview["products_discussed"],
            key_discussion_points=preview["key_discussion_points"],
            samples_distributed=preview["samples_distributed"],
            hcp_sentiment=preview["hcp_sentiment"],
            follow_up_needed=preview["follow_up_needed"],
            follow_up_notes=preview["follow_up_notes"],
            created_via=created_via,
            raw_input=raw_message,
            status="logged",
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        return {"status": "logged", "interaction_id": interaction.id, "record": preview}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool 2: edit_interaction
# ---------------------------------------------------------------------------
@tool("edit_interaction")
def edit_interaction_tool(
    interaction_id: str,
    edited_by: str,
    raw_correction_text: Optional[str] = None,
    fields: Optional[dict] = None,
    confirmed: bool = False,
) -> dict:
    """
    Edit an existing interaction. Accepts either a conversational correction
    (`raw_correction_text`, parsed by the LLM into a diff) or explicit
    `fields` (form path). Requires `confirmed=True` to actually persist;
    otherwise returns a diff preview.
    """
    db = SessionLocal()
    try:
        interaction = db.query(models.Interaction).filter(
            models.Interaction.id == interaction_id
        ).first()
        if not interaction:
            return {"status": "error", "reason": "interaction_not_found"}

        if raw_correction_text and not fields:
            diff_prompt = f"""The rep is correcting a previously logged interaction.
Current record: {json.dumps({
                'interaction_type': interaction.interaction_type,
                'products_discussed': interaction.products_discussed,
                'key_discussion_points': interaction.key_discussion_points,
                'samples_distributed': interaction.samples_distributed,
                'hcp_sentiment': interaction.hcp_sentiment,
                'follow_up_needed': interaction.follow_up_needed,
            })}

Correction message: "{raw_correction_text}"

Return ONLY a JSON object containing just the fields that should change
(same field names as above). Do not include unchanged fields."""
            resp = fast_llm.invoke(diff_prompt)
            text = resp.content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                fields = json.loads(text)
            except json.JSONDecodeError:
                fields = {}

        fields = fields or {}
        if not fields:
            return {"status": "no_changes_detected"}

        if not confirmed:
            return {
                "status": "pending_confirmation",
                "interaction_id": interaction_id,
                "proposed_changes": fields,
            }

        # snapshot current state before mutating, for audit history
        snapshot = {
            c.name: getattr(interaction, c.name)
            for c in interaction.__table__.columns
        }
        history_row = models.InteractionHistory(
            interaction_id=interaction.id,
            version=interaction.version,
            snapshot=json.loads(json.dumps(snapshot, default=str)),
            changed_fields=list(fields.keys()),
            edited_by=edited_by,
        )
        db.add(history_row)

        for field_name, value in fields.items():
            if hasattr(interaction, field_name):
                setattr(interaction, field_name, value)
        interaction.version += 1
        db.commit()
        db.refresh(interaction)

        return {
            "status": "updated",
            "interaction_id": interaction.id,
            "changed_fields": list(fields.keys()),
            "version": interaction.version,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool 3: fetch_hcp_history
# ---------------------------------------------------------------------------
@tool("fetch_hcp_history")
def fetch_hcp_history_tool(hcp_id: Optional[str] = None, hcp_name: Optional[str] = None, limit: int = 5) -> dict:
    """Fetch an HCP's profile and recent interaction history for grounding."""
    db = SessionLocal()
    try:
        hcp = _resolve_hcp(db, hcp_name, hcp_id)
        if not hcp:
            return {"status": "not_found"}

        recent = (
            db.query(models.Interaction)
            .filter(models.Interaction.hcp_id == hcp.id)
            .order_by(models.Interaction.occurred_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "status": "ok",
            "hcp_profile": {
                "id": hcp.id,
                "full_name": hcp.full_name,
                "specialty": hcp.specialty,
                "institution": hcp.institution,
                "tier": hcp.tier,
                "consent_status": hcp.consent_status,
            },
            "recent_interactions": [
                {
                    "id": i.id,
                    "occurred_at": i.occurred_at.isoformat(),
                    "interaction_type": i.interaction_type,
                    "products_discussed": i.products_discussed,
                    "key_discussion_points": i.key_discussion_points,
                    "sentiment": i.hcp_sentiment,
                }
                for i in recent
            ],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool 4: schedule_follow_up
# ---------------------------------------------------------------------------
@tool("schedule_follow_up")
def schedule_follow_up_tool(
    interaction_id: str,
    hcp_id: str,
    rep_id: str,
    follow_up_notes: Optional[str] = None,
    due_date: Optional[str] = None,
) -> dict:
    """Create a follow-up task linked to an interaction. Resolves relative
    dates (e.g. 'next week') to an absolute due_date if not already given."""
    db = SessionLocal()
    try:
        resolved_date = due_date
        if not resolved_date:
            if follow_up_notes and "next week" in follow_up_notes.lower():
                resolved_date = (datetime.utcnow() + timedelta(days=7)).isoformat()
            else:
                resolved_date = (datetime.utcnow() + timedelta(days=3)).isoformat()

        task = models.FollowUpTask(
            interaction_id=interaction_id,
            hcp_id=hcp_id,
            rep_id=rep_id,
            due_date=datetime.fromisoformat(resolved_date),
            description=follow_up_notes,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return {"status": "scheduled", "task_id": task.id, "due_date": resolved_date}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Tool 5: compliance_flag_check
# ---------------------------------------------------------------------------
COMPLIANCE_PROMPT = """You are a pharma compliance screener. Given the discussion \
summary and products below, flag any statements that look like off-label claims, \
unapproved efficacy/safety promises, or excessive/unauthorized sample commitments.

Products discussed: {products}
Discussion summary: {summary}
Samples distributed: {samples}

Return ONLY JSON: {{"flagged": boolean, "reasons": [string, ...], "severity": "low"|"medium"|"high"}}
"""


@tool("compliance_flag_check")
def compliance_flag_check_tool(
    interaction_id: Optional[str],
    products_discussed: list,
    key_discussion_points: str,
    samples_distributed: list,
) -> dict:
    """Screen an interaction's content for compliance issues before/after logging."""
    prompt = COMPLIANCE_PROMPT.format(
        products=json.dumps(products_discussed),
        summary=key_discussion_points or "",
        samples=json.dumps(samples_distributed),
    )
    resp = reasoning_llm.invoke(prompt)
    text = resp.content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"flagged": False, "reasons": [], "severity": "low"}

    if result.get("flagged") and interaction_id:
        db = SessionLocal()
        try:
            for reason in result.get("reasons", []):
                db.add(models.ComplianceFlag(
                    interaction_id=interaction_id,
                    reason=reason,
                    severity=result.get("severity", "medium"),
                ))
            interaction = db.query(models.Interaction).filter(
                models.Interaction.id == interaction_id
            ).first()
            if interaction:
                interaction.status = "pending_compliance_review"
            db.commit()
        finally:
            db.close()

    return result


# ---------------------------------------------------------------------------
# Tool 6 (bonus): suggest_next_best_action
# ---------------------------------------------------------------------------
@tool("suggest_next_best_action")
def suggest_next_best_action_tool(hcp_id: str) -> dict:
    """Suggest talking points / products for the *next* engagement with this HCP."""
    history = fetch_hcp_history_tool.invoke({"hcp_id": hcp_id, "limit": 5})
    if history.get("status") != "ok":
        return {"status": "not_found"}

    prompt = f"""Based on this HCP's profile and recent interaction history, \
suggest 2-3 concise next-best-action talking points for the rep's next visit.

Profile: {json.dumps(history['hcp_profile'])}
Recent interactions: {json.dumps(history['recent_interactions'])}

Return ONLY JSON: {{"suggestions": [string, string, ...]}}
"""
    resp = reasoning_llm.invoke(prompt)
    text = resp.content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"suggestions": []}


ALL_TOOLS = [
    log_interaction_tool,
    edit_interaction_tool,
    fetch_hcp_history_tool,
    schedule_follow_up_tool,
    compliance_flag_check_tool,
    suggest_next_best_action_tool,
]

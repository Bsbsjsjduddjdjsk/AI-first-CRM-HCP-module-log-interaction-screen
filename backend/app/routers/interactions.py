from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..agent.tools import log_interaction_tool, edit_interaction_tool, compliance_flag_check_tool

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("", response_model=dict)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    """Structured-form path: payload is already well-formed, so we skip LLM
    extraction but still run it through the same tool for consistency and
    compliance screening."""
    result = log_interaction_tool.invoke({
        "rep_id": payload.rep_id,
        "structured_payload": payload.model_dump(exclude={"rep_id", "hcp_id", "hcp_name", "created_via", "raw_input"}),
        "hcp_id": payload.hcp_id,
        "hcp_name": payload.hcp_name,
        "created_via": payload.created_via,
        "confirmed": True,
    })
    if result["status"] == "needs_clarification":
        raise HTTPException(status_code=422, detail=result)

    compliance_flag_check_tool.invoke({
        "interaction_id": result["interaction_id"],
        "products_discussed": payload.products_discussed,
        "key_discussion_points": payload.key_discussion_points or "",
        "samples_distributed": payload.samples_distributed,
    })
    return result


@router.get("/{interaction_id}", response_model=schemas.InteractionOut)
def get_interaction(interaction_id: str, db: Session = Depends(get_db)):
    interaction = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.get("", response_model=list[schemas.InteractionOut])
def list_interactions(hcp_id: str | None = None, rep_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Interaction)
    if hcp_id:
        q = q.filter(models.Interaction.hcp_id == hcp_id)
    if rep_id:
        q = q.filter(models.Interaction.rep_id == rep_id)
    return q.order_by(models.Interaction.occurred_at.desc()).all()


@router.patch("/{interaction_id}", response_model=dict)
def update_interaction(interaction_id: str, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    result = edit_interaction_tool.invoke({
        "interaction_id": interaction_id,
        "edited_by": payload.edited_by,
        "fields": payload.fields,
        "confirmed": True,
    })
    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result)
    return result

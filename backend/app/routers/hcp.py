from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..agent.tools import fetch_hcp_history_tool, suggest_next_best_action_tool

router = APIRouter(prefix="/api/hcps", tags=["hcps"])


@router.get("", response_model=list[dict])
def search_hcps(q: str = "", db: Session = Depends(get_db)):
    query = db.query(models.HCP)
    if q:
        query = query.filter(models.HCP.full_name.ilike(f"%{q}%"))
    return [
        {"id": h.id, "full_name": h.full_name, "specialty": h.specialty, "institution": h.institution}
        for h in query.limit(20).all()
    ]


@router.get("/{hcp_id}/history")
def get_hcp_history(hcp_id: str):
    result = fetch_hcp_history_tool.invoke({"hcp_id": hcp_id})
    if result.get("status") != "ok":
        raise HTTPException(status_code=404, detail="HCP not found")
    return result


@router.get("/{hcp_id}/next-best-action")
def get_next_best_action(hcp_id: str):
    return suggest_next_best_action_tool.invoke({"hcp_id": hcp_id})

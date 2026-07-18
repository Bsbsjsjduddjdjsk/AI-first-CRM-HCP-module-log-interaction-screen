from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ProductDiscussed(BaseModel):
    product_id: Optional[str] = None
    product_name: str


class SampleDistributed(BaseModel):
    product_name: str
    quantity: int


class InteractionCreate(BaseModel):
    hcp_id: Optional[str] = None
    hcp_name: Optional[str] = None  # allows fuzzy resolution if hcp_id unknown
    rep_id: str
    interaction_type: str
    occurred_at: datetime
    duration_minutes: Optional[int] = None
    products_discussed: List[ProductDiscussed] = []
    key_discussion_points: Optional[str] = None
    samples_distributed: List[SampleDistributed] = []
    hcp_sentiment: Optional[str] = None
    follow_up_needed: bool = False
    follow_up_notes: Optional[str] = None
    created_via: str = "form"
    raw_input: Optional[str] = None


class InteractionUpdate(BaseModel):
    interaction_id: str
    edited_by: str
    fields: dict = Field(default_factory=dict, description="Partial fields to update")
    raw_correction_text: Optional[str] = None  # if edit came via chat correction


class InteractionOut(BaseModel):
    id: str
    hcp_id: str
    rep_id: str
    interaction_type: str
    occurred_at: datetime
    duration_minutes: Optional[int]
    products_discussed: list
    key_discussion_points: Optional[str]
    samples_distributed: list
    hcp_sentiment: Optional[str]
    follow_up_needed: bool
    status: str
    created_via: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    session_id: str
    rep_id: str
    message: str


class ChatAgentResponse(BaseModel):
    session_id: str
    agent_message: str
    proposed_action: Optional[str] = None  # "log_interaction" | "edit_interaction" | None
    structured_preview: Optional[dict] = None
    requires_confirmation: bool = False
    interaction_id: Optional[str] = None


class ConfirmAction(BaseModel):
    session_id: str
    rep_id: str
    approved: bool
    edited_payload: Optional[dict] = None  # rep can tweak the preview before confirming

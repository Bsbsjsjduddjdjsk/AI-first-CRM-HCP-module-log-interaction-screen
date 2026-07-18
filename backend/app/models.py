import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, Enum, Boolean,
    Integer, JSON, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def gen_uuid():
    return str(uuid.uuid4())


class InteractionType(str, enum.Enum):
    visit = "visit"
    call = "call"
    email = "email"
    event = "event"
    virtual_meeting = "virtual_meeting"


class Sentiment(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionStatus(str, enum.Enum):
    draft = "draft"
    logged = "logged"
    pending_compliance_review = "pending_compliance_review"
    approved = "approved"
    rejected = "rejected"


class CreatedVia(str, enum.Enum):
    form = "form"
    chat = "chat"


class Rep(Base):
    __tablename__ = "reps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    territory = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    interactions = relationship("Interaction", back_populates="rep")


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    full_name = Column(String(255), nullable=False, index=True)
    specialty = Column(String(255))
    institution = Column(String(255))
    tier = Column(String(50))  # e.g., A/B/C prescriber tier
    consent_status = Column(Boolean, default=True)
    email = Column(String(255))
    phone = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

    interactions = relationship("Interaction", back_populates="hcp")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False, unique=True)
    approved_claims = Column(JSON, default=list)  # list of approved claim strings


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hcp_id = Column(UUID(as_uuid=False), ForeignKey("hcps.id"), nullable=False)
    rep_id = Column(UUID(as_uuid=False), ForeignKey("reps.id"), nullable=False)

    interaction_type = Column(Enum(InteractionType), nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer)

    products_discussed = Column(JSON, default=list)  # [{product_id, product_name}]
    key_discussion_points = Column(Text)
    samples_distributed = Column(JSON, default=list)  # [{product_name, quantity}]
    hcp_sentiment = Column(Enum(Sentiment))
    follow_up_needed = Column(Boolean, default=False)
    follow_up_notes = Column(Text)

    status = Column(Enum(InteractionStatus), default=InteractionStatus.logged)
    created_via = Column(Enum(CreatedVia), default=CreatedVia.form)
    raw_input = Column(Text)  # original chat transcript / form snapshot, for audit

    version = Column(Integer, default=1)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    hcp = relationship("HCP", back_populates="interactions")
    rep = relationship("Rep", back_populates="interactions")
    history = relationship("InteractionHistory", back_populates="interaction")
    compliance_flags = relationship("ComplianceFlag", back_populates="interaction")


class InteractionHistory(Base):
    """Immutable snapshot recorded on every edit for audit/regulatory traceability."""
    __tablename__ = "interaction_history"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    interaction_id = Column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=False)
    version = Column(Integer, nullable=False)
    snapshot = Column(JSON, nullable=False)  # full record state at that version
    changed_fields = Column(JSON, default=list)
    edited_by = Column(UUID(as_uuid=False), ForeignKey("reps.id"))
    edited_at = Column(DateTime, server_default=func.now())

    interaction = relationship("Interaction", back_populates="history")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    interaction_id = Column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=False)
    hcp_id = Column(UUID(as_uuid=False), ForeignKey("hcps.id"), nullable=False)
    rep_id = Column(UUID(as_uuid=False), ForeignKey("reps.id"), nullable=False)
    due_date = Column(DateTime, nullable=False)
    description = Column(Text)
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class ComplianceFlag(Base):
    __tablename__ = "compliance_flags"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    interaction_id = Column(UUID(as_uuid=False), ForeignKey("interactions.id"), nullable=False)
    reason = Column(String(500), nullable=False)
    severity = Column(String(50), default="medium")  # low / medium / high
    review_status = Column(String(50), default="pending")  # pending / cleared / escalated
    created_at = Column(DateTime, server_default=func.now())

    interaction = relationship("Interaction", back_populates="compliance_flags")

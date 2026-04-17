"""FashionFlowState model for tracking conversation flow."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from models.user import User


class FlowStep:
    IDLE = "idle"
    AWAITING_FABRIC = "awaiting_fabric"
    AWAITING_MEASUREMENTS = "awaiting_measurements"
    AWAITING_SPECS = "awaiting_specs"
    GENERATING = "generating"
    DONE = "done"


class FashionFlowState(Base):
    __tablename__ = "fashion_flow_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    current_step: Mapped[str] = mapped_column(String(50), default=FlowStep.IDLE)
    fabric_url: Mapped[str | None] = mapped_column(String(500), default=None)
    fabric_name: Mapped[str | None] = mapped_column(String(255), default=None)
    client_measurements: Mapped[dict | None] = mapped_column(JSON, default=None)
    garment_specs: Mapped[dict | None] = mapped_column(JSON, default=None)
    is_human_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="flow_state")

    def __repr__(self) -> str:
        return f"<FashionFlowState(user_id={self.user_id}, step={self.current_step})>"

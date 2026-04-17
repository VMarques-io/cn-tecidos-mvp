"""User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base

if TYPE_CHECKING:
    from models.conversation import Message
    from models.flow_state import FashionFlowState


class ProfileType:
    CURIOSO = "curioso"
    CLIENTE_PF = "cliente_pf"
    CLIENTE_PJ = "cliente_pj"
    CLIENTE_CRIATIVO = "cliente_criativo"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    remote_jid: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    profile_type: Mapped[str] = mapped_column(String(50), default=ProfileType.CURIOSO)
    body_measurements: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    flow_state: Mapped["FashionFlowState | None"] = relationship("FashionFlowState", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, remote_jid={self.remote_jid}, profile_type={self.profile_type})>"

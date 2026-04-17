"""Camada de serviço para persistência de dados do agente."""

import json
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from models.user import User
from models.conversation import Message, MessageRole, MessageType
from models.flow_state import FashionFlowState, FlowStep
from agents.state import AgentState

logger = logging.getLogger(__name__)

def get_or_create_user(db: Session, remote_jid: str) -> User:
    user = db.query(User).filter(User.remote_jid == remote_jid).first()
    if not user:
        user = User(remote_jid=remote_jid)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"[MEMORY] New user created: {remote_jid}")
    else:
        user.last_seen = datetime.utcnow()
        db.commit()
    return user

def get_or_create_flow_state(db: Session, user: User) -> FashionFlowState:
    state = db.query(FashionFlowState).filter(FashionFlowState.user_id == user.id).first()
    if not state:
        state = FashionFlowState(user_id=user.id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state

def get_recent_messages(db: Session, user: User, limit: int = 8) -> List[dict]:
    messages = db.query(Message).filter(Message.user_id == user.id).order_by(Message.created_at.desc()).limit(limit).all()
    messages.reverse()
    return [{"role": msg.role, "content": msg.content or f"[{msg.message_type}]"} for msg in messages]

def save_message(db: Session, user: User, role: MessageRole, content: Optional[str] = None, media_url: Optional[str] = None, media_mime: Optional[str] = None, evolution_message_id: Optional[str] = None) -> Message:
    msg_type = MessageType.TEXT
    if media_mime:
        if "image" in media_mime:
            msg_type = MessageType.IMAGE
        elif "audio" in media_mime:
            msg_type = MessageType.AUDIO
        elif "document" in media_mime or "pdf" in media_mime:
            msg_type = MessageType.DOCUMENT
    msg = Message(user_id=user.id, role=role, message_type=msg_type, content=content, media_url=media_url, media_mime=media_mime, evolution_message_id=evolution_message_id)
    db.add(msg)
    db.commit()
    return msg

def sync_state_to_db(db: Session, user: User, agent_state: AgentState):
    flow = get_or_create_flow_state(db, user)
    step_map = {"idle": FlowStep.IDLE, "awaiting_fabric": FlowStep.AWAITING_FABRIC, "awaiting_ref": FlowStep.AWAITING_REFERENCE, "awaiting_measurements": FlowStep.AWAITING_MEASUREMENTS, "awaiting_specs": FlowStep.AWAITING_SPECS, "generating": FlowStep.GENERATING, "done": FlowStep.DONE, "human_handoff": FlowStep.HUMAN_HANDOFF}
    flow.current_step = step_map.get(agent_state.get("flow_step", "idle"), FlowStep.IDLE)
    flow.is_human_active = agent_state.get("is_human_active", False)
    db.commit()
    logger.debug(f"[MEMORY] State synced for {user.remote_jid}: {flow.current_step}")

def load_state_from_db(db: Session, user: User) -> dict:
    flow = get_or_create_flow_state(db, user)
    step_map = {FlowStep.IDLE: "idle", FlowStep.AWAITING_FABRIC: "awaiting_fabric", FlowStep.AWAITING_REFERENCE: "awaiting_ref", FlowStep.AWAITING_MEASUREMENTS: "awaiting_measurements", FlowStep.AWAITING_SPECS: "awaiting_specs", FlowStep.GENERATING: "generating", FlowStep.DONE: "done", FlowStep.HUMAN_HANDOFF: "human_handoff"}
    return {"flow_step": step_map.get(flow.current_step, "idle"), "is_human_active": flow.is_human_active}

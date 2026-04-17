"""
Camada de serviço para persistência de dados do agente.
Gerencia usuários, mensagens e estado do fluxo fashion.
"""

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
    """Busca o usuário pelo número do WhatsApp ou cria um novo."""
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
    """Busca ou cria o estado de fluxo do usuário."""
    state = db.query(FashionFlowState).filter(FashionFlowState.user_id == user.id).first()
    if not state:
        state = FashionFlowState(user_id=user.id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_recent_messages(db: Session, user: User, limit: int = 8) -> List[dict]:
    """Retorna as últimas mensagens do usuário formatadas para o LLM."""
    messages = (
        db.query(Message)
        .filter(Message.user_id == user.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    messages.reverse()  # Ordem cronológica
    return [
        {
            "role": msg.role.value,
            "content": msg.content or f"[{msg.message_type.value}]",
        }
        for msg in messages
    ]


def save_message(
    db: Session,
    user: User,
    role: MessageRole,
    content: Optional[str] = None,
    media_url: Optional[str] = None,
    media_mime: Optional[str] = None,
    evolution_message_id: Optional[str] = None,
) -> Message:
    """Persiste uma mensagem no histórico."""
    msg_type = MessageType.TEXT
    if media_mime:
        if "image" in media_mime:
            msg_type = MessageType.IMAGE
        elif "audio" in media_mime:
            msg_type = MessageType.AUDIO
        elif "document" in media_mime or "pdf" in media_mime:
            msg_type = MessageType.DOCUMENT

    msg = Message(
        user_id=user.id,
        role=role,
        message_type=msg_type,
        content=content,
        media_url=media_url,
        media_mime=media_mime,
        evolution_message_id=evolution_message_id,
    )
    db.add(msg)
    db.commit()
    return msg


def sync_state_to_db(db: Session, user: User, agent_state: AgentState):
    """Sincroniza o estado do LangGraph com o banco de dados."""
    flow = get_or_create_flow_state(db, user)

    # Mapeia o flow_step do grafo para o enum do banco
    step_map = {
        "idle": FlowStep.IDLE,
        "awaiting_fabric": FlowStep.AWAITING_FABRIC,
        "awaiting_ref": FlowStep.AWAITING_REFERENCE,
        "awaiting_measurements": FlowStep.AWAITING_MEASUREMENTS,
        "awaiting_specs": FlowStep.AWAITING_SPECS,
        "generating": FlowStep.GENERATING,
        "done": FlowStep.DONE,
        "human_handoff": FlowStep.HUMAN_HANDOFF,
    }

    flow.current_step = step_map.get(agent_state.get("flow_step", "idle"), FlowStep.IDLE)
    flow.fabric_url = agent_state.get("fabric_url")
    flow.fabric_name = agent_state.get("fabric_name")
    flow.client_measurements = agent_state.get("client_measurements")
    flow.garment_specs = agent_state.get("garment_specs")
    flow.clothing_description = agent_state.get("clothing_description")
    flow.is_human_active = agent_state.get("is_human_active", False)

    if agent_state.get("reference_urls"):
        flow.reference_urls = json.dumps(agent_state["reference_urls"])

    db.commit()
    logger.debug(f"[MEMORY] State synced for {user.remote_jid}: {flow.current_step}")


def load_state_from_db(db: Session, user: User) -> dict:
    """Carrega o estado persistido para restaurar o grafo LangGraph."""
    flow = get_or_create_flow_state(db, user)

    step_map = {
        FlowStep.IDLE: "idle",
        FlowStep.AWAITING_FABRIC: "awaiting_fabric",
        FlowStep.AWAITING_REFERENCE: "awaiting_ref",
        FlowStep.AWAITING_MEASUREMENTS: "awaiting_measurements",
        FlowStep.AWAITING_SPECS: "awaiting_specs",
        FlowStep.GENERATING: "generating",
        FlowStep.DONE: "done",
        FlowStep.HUMAN_HANDOFF: "human_handoff",
    }

    reference_urls = None
    if flow.reference_urls:
        try:
            reference_urls = json.loads(flow.reference_urls)
        except json.JSONDecodeError:
            pass

    return {
        "flow_step": step_map.get(flow.current_step, "idle"),
        "fabric_url": flow.fabric_url,
        "fabric_name": flow.fabric_name,
        "client_measurements": flow.client_measurements,
        "garment_specs": flow.garment_specs,
        "reference_urls": reference_urls,
        "clothing_description": flow.clothing_description,
        "is_human_active": flow.is_human_active,
    }

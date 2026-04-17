"""
Pytest configuration and fixtures for C&N Tecidos AI Agent tests.

Fixtures:
- db_session: SQLAlchemy session with SQLite in-memory
- mock_evolution_api: Mock httpx.AsyncClient for Evolution API
- mock_gemini: Mock Gemini API responses
- sample_agent_state: Pre-built AgentState for tests
- client: FastAPI TestClient
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Set test environment variables before any imports
import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GEMINI_API_KEY"] = "test-api-key"
os.environ["EVOLUTION_API_URL"] = "http://test-evolution-api.local"
os.environ["AUTHENTICATION_API_KEY"] = "test-auth-key"
os.environ["HANDOFF_LINK"] = "https://test-handoff.link"

# SQLAlchemy imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Import models to register them in SQLAlchemy Base
from db.database import Base, get_db
from models.user import User, ProfileType
from agents.state import AgentState, default_state


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create a SQLite in-memory database engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def mock_user(db_session: Session) -> User:
    """Create a test user in the database."""
    user = User(
        remote_jid="558399999999@s.whatsapp.net",
        profile_type=ProfileType.CLIENTE_CRIATIVO,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session):
    """Create a FastAPI TestClient with overridden database dependency."""
    from main import app
    
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


# =============================================================================
# Agent State Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_state() -> AgentState:
    """Return a pre-built AgentState for testing."""
    return default_state(
        remote_jid="558399999999@s.whatsapp.net",
        instance_name="test-instance",
        profile_type="curioso",
        incoming_text="Olá, gostaria de saber sobre tecidos",
        intent="FAQ",
        flow_step="idle",
        chat_history=[],
        response=None,
        is_human_active=False,
        should_end=False,
    )


@pytest.fixture
def sample_agent_state_human_active() -> AgentState:
    """Return an AgentState with human already active."""
    return default_state(
        remote_jid="558399999999@s.whatsapp.net",
        instance_name="test-instance",
        profile_type="curioso",
        incoming_text="Preciso falar com um humano",
        intent="HUMANO",
        flow_step="idle",
        chat_history=[],
        response=None,
        is_human_active=True,
        should_end=False,
    )


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_gemini():
    """Mock Gemini API responses."""
    with patch("agents.nodes.classify_with_gemini") as mock:
        mock.return_value = "FAQ"
        yield mock


@pytest.fixture
def mock_gemini_faq_response():
    """Mock Gemini to return FAQ classification."""
    with patch("agents.nodes.classify_with_gemini") as mock:
        mock.return_value = "FAQ"
        yield mock


@pytest.fixture
def mock_gemini_humano_response():
    """Mock Gemini to return HUMANO classification."""
    with patch("agents.nodes.classify_with_gemini") as mock:
        mock.return_value = "HUMANO"
        yield mock


@pytest.fixture
def mock_gemini_cancel_response():
    """Mock Gemini to return CANCEL classification."""
    with patch("agents.nodes.classify_with_gemini") as mock:
        mock.return_value = "CANCEL"
        yield mock


@pytest.fixture
def mock_gemini_unavailable():
    """Mock Gemini to simulate API unavailability."""
    with patch("agents.nodes.classify_with_gemini") as mock:
        # Will trigger keyword fallback
        mock.side_effect = Exception("Gemini API unavailable")
        yield mock


@pytest.fixture
def mock_evolution_api():
    """Mock httpx.AsyncClient for Evolution API calls."""
    with patch("services.whatsapp.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "message": "sent"}
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client


@pytest.fixture
def mock_whatsapp_send():
    """Mock WhatsApp send functions."""
    with patch("services.whatsapp.send_text") as mock_text, \
         patch("services.whatsapp.send_image") as mock_image:
        mock_text.return_value = {"status": "simulated", "message": "sent"}
        mock_image.return_value = {"status": "simulated", "message": "sent"}
        yield {"text": mock_text, "image": mock_image}


@pytest.fixture
def mock_fashion_graph():
    """Mock the fashion graph for testing."""
    with patch("agents.fashion_graph.get_fashion_graph") as mock:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "response": "Test response",
            "flow_step": "idle",
        })
        mock.return_value = mock_graph
        yield mock_graph


# =============================================================================
# Webhook Payload Fixtures
# =============================================================================

@pytest.fixture
def valid_text_message_payload():
    """Return a valid text message webhook payload."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "558399999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test-message-id-123"
            },
            "message": {
                "conversation": "Olá, gostaria de saber sobre tecidos"
            }
        }
    }


@pytest.fixture
def from_me_message_payload():
    """Return a webhook payload where fromMe=True (bot message)."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "558399999999@s.whatsapp.net",
                "fromMe": True,
                "id": "test-message-id-456"
            },
            "message": {
                "conversation": "Mensagem do bot"
            }
        }
    }


@pytest.fixture
def group_message_payload():
    """Return a webhook payload for a group message (@g.us)."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "558399999999-1234567890@g.us",
                "fromMe": False,
                "id": "test-message-id-789"
            },
            "message": {
                "conversation": "Mensagem em grupo"
            }
        }
    }


@pytest.fixture
def extended_text_message_payload():
    """Return a webhook payload with extendedTextMessage."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "558399999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test-message-id-ext"
            },
            "message": {
                "extendedTextMessage": {
                    "text": "Texto com formatação"
                }
            }
        }
    }


@pytest.fixture
def media_message_payload():
    """Return a webhook payload with image message (should be ignored)."""
    return {
        "event": "messages.upsert",
        "instance": "test-instance",
        "data": {
            "key": {
                "remoteJid": "558399999999@s.whatsapp.net",
                "fromMe": False,
                "id": "test-message-id-media"
            },
            "message": {
                "imageMessage": {
                    "caption": "Foto do tecido",
                    "url": "http://example.com/image.jpg",
                    "mimetype": "image/jpeg"
                }
            }
        }
    }

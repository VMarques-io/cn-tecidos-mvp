"""Pytest configuration and fixtures for C&N Tecidos AI Agent tests."""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["GEMINI_API_KEY"] = "test-api-key"
os.environ["EVOLUTION_API_URL"] = "http://test.local"
os.environ["AUTHENTICATION_API_KEY"] = "test-auth"
os.environ["HANDOFF_LINK"] = "https://test-handoff.link"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base
from models.user import User, ProfileType
from agents.state import default_state


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def mock_user(db_session):
    user = User(remote_jid="558399999999@s.whatsapp.net", profile_type=ProfileType.CLIENTE_CRIATIVO)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def client(db_session):
    from main import app
    from db.database import get_db
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_agent_state():
    return default_state(remote_jid="558399999999@s.whatsapp.net", instance_name="test-instance", incoming_text="Olá, quero saber sobre tecidos", intent="FAQ", flow_step="idle", is_human_active=False)


@pytest.fixture
def mock_fashion_graph():
    with patch("agents.fashion_graph.get_fashion_graph") as mock:
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"response": "Test response", "flow_step": "idle"})
        mock.return_value = mock_graph
        yield mock_graph


@pytest.fixture
def valid_text_message_payload():
    return {"event": "messages.upsert", "instance": "test-instance", "data": {"key": {"remoteJid": "558399999999@s.whatsapp.net", "fromMe": False, "id": "test-msg-123"}, "message": {"conversation": "Olá, gostaria de saber sobre tecidos"}}}


@pytest.fixture
def from_me_message_payload():
    return {"event": "messages.upsert", "instance": "test-instance", "data": {"key": {"remoteJid": "558399999999@s.whatsapp.net", "fromMe": True, "id": "bot-msg"}, "message": {"conversation": "Mensagem do bot"}}}


@pytest.fixture
def group_message_payload():
    return {"event": "messages.upsert", "instance": "test-instance", "data": {"key": {"remoteJid": "551199999999-123456@g.us", "fromMe": False, "id": "group-msg"}, "message": {"conversation": "Mensagem em grupo"}}}


@pytest.fixture
def media_message_payload():
    return {"event": "messages.upsert", "instance": "test-instance", "data": {"key": {"remoteJid": "558399999999@s.whatsapp.net", "fromMe": False, "id": "img-msg"}, "message": {"imageMessage": {"caption": "Foto", "url": "http://exemplo.com/img.jpg", "mimetype": "image/jpeg"}}}}

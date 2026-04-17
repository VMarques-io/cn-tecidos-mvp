# C&N Tecidos AI Agent

Agente de IA para atendimento via WhatsApp (MVP FAQ + Handoff).

## Stack
- FastAPI + Uvicorn
- LangGraph (triage → FAQ/HUMANO/CANCEL)
- PostgreSQL (SQLAlchemy + Alembic)
- Evolution API (WhatsApp Business)
- Google Gemini (LLM)
- Docker + Easypanel deploy

## Setup Local

```bash
cd backend
cp .env.example .env  # preencher variáveis
docker compose up -d
curl http://localhost:3000/health
```

## Testes

```bash
pytest tests/ -v
```

## Deploy (Easypanel)

1. New Project → Blank
2. Add Service → PostgreSQL (db)
3. Add Service → App (GitHub: VMarques-io/cn-tecidos-mvp)
4. Dockerfile Path: `backend/Dockerfile`
5. Build Context: `/`
6. Configurar env vars
7. Deploy

"""
C&N Tecidos AI Agent — FastAPI entrypoint.

Startup is designed to be RESILIENT: the app will ALWAYS start,
even if database, LLM, or LangGraph dependencies are unavailable.
Degraded mode: only the /health and / endpoints work.
Full mode: webhook routes are available.
"""

import sys
import logging
import os

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

print("[STARTUP] === C&N Tecidos AI Agent starting ===", flush=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("[STARTUP] dotenv loaded", flush=True)
except Exception as e:
    print(f"[STARTUP] dotenv load failed: {e}", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[LIFESPAN] === Lifecycle starting ===", flush=True)
    logger.info("🚀 C&N Tecidos AI Agent iniciando...")

    # Database init (non-fatal if it fails)
    try:
        print("[LIFESPAN] Creating database tables...", flush=True)
        import db.database as db_mod
        print(f"[LIFESPAN] db.database attrs: {[a for a in dir(db_mod) if not a.startswith('_')]}", flush=True)
        if hasattr(db_mod, 'create_all_tables'):
            db_mod.create_all_tables()
            print("[LIFESPAN] ✅ Database initialized", flush=True)
            logger.info("✅ Banco de dados inicializado")
            # Seed data on startup
            try:
                from db.seed import seed_if_empty
                seed_if_empty()
                print("[LIFESPAN] ✅ Database seeded", flush=True)
            except Exception as e:
                print(f"[LIFESPAN] ⚠️ Seed failed: {e}", flush=True)
        else:
            # Fallback: create tables directly
            print("[LIFESPAN] create_all_tables not found, using fallback", flush=True)
            engine = db_mod.get_engine()
            if engine is not None:
                db_mod.Base.metadata.create_all(bind=engine)
                print("[LIFESPAN] ✅ Database initialized (fallback)", flush=True)
                logger.info("✅ Banco de dados inicializado (fallback)")
            else:
                print("[LIFESPAN] ⚠️ No database engine available", flush=True)
    except Exception as e:
        print(f"[LIFESPAN] ⚠️ Database unavailable: {e}", flush=True)
        logger.warning(f"⚠️ Banco de dados não disponível no startup: {e}")

    # LangGraph compilation (non-fatal if it fails)
    try:
        print("[LIFESPAN] Compiling LangGraph...", flush=True)
        from agents.fashion_graph import get_fashion_graph
        graph = get_fashion_graph()
        print(f"[LIFESPAN] ✅ LangGraph compiled: {type(graph).__name__}", flush=True)
        logger.info("✅ Grafo LangGraph compilado")
    except Exception as e:
        print(f"[LIFESPAN] ⚠️ LangGraph compilation failed: {e}", flush=True)
        logger.warning(f"⚠️ Grafo LangGraph não compilado no startup: {e}")

    print("[LIFESPAN] === Lifecycle ready ===", flush=True)
    yield
    logger.info("🛑 C&N Tecidos AI Agent encerrando...")


print("[STARTUP] Creating FastAPI app...", flush=True)
app = FastAPI(
    title="C&N Tecidos AI Agent",
    description="Agente de IA para atendimento via WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


print("[STARTUP] Registering webhook routes...", flush=True)
try:
    from routes.webhook import router as whatsapp_router
    app.include_router(whatsapp_router, prefix="/api/v1", tags=["WhatsApp"])
    print("[STARTUP] ✅ WhatsApp routes registered", flush=True)
    logger.info("✅ Rotas WhatsApp registradas")
except Exception as e:
    print(f"[STARTUP] ⚠️ WhatsApp routes NOT registered: {e}", flush=True)
    logger.warning(f"⚠️ Rotas WhatsApp não registradas no startup: {e}")


@app.get("/", tags=["Infra"])
def root():
    return {"status": "ok", "service": "cn_tecidos_ai", "version": "1.0.0"}


@app.get("/health", tags=["Infra"])
def health_check():
    return {"status": "ok", "service": "cn_tecidos_ai", "version": "1.0.0"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"[STARTUP] Starting uvicorn on 0.0.0.0:{port}", flush=True)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False, log_level="info")


print(f"[STARTUP] Module loaded. Routes: {[r.path for r in app.routes]}", flush=True)

"""
Integração com a Evolution API v2.3.7.
Envio de mensagens de texto, imagens e download de mídias recebidas.
"""

import os
import logging
import httpx
from typing import Optional, List, Dict
import time

logger = logging.getLogger(__name__)

# Cache global para testes locais (frontend de simulação)
# Estrutura: { jid: [ {role: 'agent', content: '...', timestamp: ...}, ... ] }
test_message_cache: Dict[str, List[Dict]] = {}

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
AUTHENTICATION_API_KEY = os.getenv("AUTHENTICATION_API_KEY", "")

# Verifica se a configuração está completa
_is_configured = bool(EVOLUTION_API_URL) and "localhost" not in EVOLUTION_API_URL.lower()

if not _is_configured:
    logger.warning(
        "[WPP] EVOLUTION_API_URL não configurado ou aponta para localhost. "
        "Modo de simulação ativado (mensagens serão logadas, não enviadas)."
    )


def _get_headers() -> Dict[str, str]:
    """Retorna headers padrão para chamadas à Evolution API."""
    return {
        "apikey": AUTHENTICATION_API_KEY,
        "Content-Type": "application/json",
    }


async def send_text(instance_name: str, remote_jid: str, text: str) -> dict:
    """
    Envia uma mensagem de texto simples para o cliente via Evolution API v2.3.7.
    """
    url = f"{EVOLUTION_API_URL}/message/sendText/{instance_name}"
    payload = {
        "number": remote_jid,
        "text": text,
        "delay": 1200,  # Simula digitação (ms) - evita ban do WhatsApp
    }

    logger.info(f"[WPP] send_text → {remote_jid[:10]}... len={len(text)}")

    # REGISTRO PARA TESTE LOCAL: Armazena no cache para o frontend de teste poder ler
    if remote_jid not in test_message_cache:
        test_message_cache[remote_jid] = []
    test_message_cache[remote_jid].append({
        "role": "agent",
        "content": text,
        "type": "text",
        "timestamp": time.time()
    })
    # Limita o cache por JID para as últimas 10 mensagens
    test_message_cache[remote_jid] = test_message_cache[remote_jid][-10:]

    # Se não houver configuração de URL real, retorna sucesso simulado
    if not _is_configured:
        return {"status": "simulated", "message": "Cache updated"}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=payload, headers=_get_headers())
        response.raise_for_status()
        return response.json()


async def send_image(
    instance_name: str,
    remote_jid: str,
    image_url: str,
    caption: Optional[str] = None,
) -> dict:
    """
    Envia uma imagem para o cliente com legenda opcional.
    """
    url = f"{EVOLUTION_API_URL}/message/sendMedia/{instance_name}"
    payload = {
        "number": remote_jid,
        "mediatype": "image",
        "mimetype": "image/jpeg",
        "caption": caption or "",
        "media": image_url,  # URL pública da imagem
    }

    logger.info(f"[WPP] send_image → {remote_jid[:10]}... url={image_url[:50]}")

    # REGISTRO PARA TESTE LOCAL
    if remote_jid not in test_message_cache:
        test_message_cache[remote_jid] = []
    test_message_cache[remote_jid].append({
        "role": "agent",
        "content": caption or "[Imagem]",
        "media_url": image_url,
        "type": "image",
        "timestamp": time.time()
    })

    if not _is_configured:
        return {"status": "simulated", "message": "Cache updated (image)"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=_get_headers())
        response.raise_for_status()
        return response.json()


async def send_typing(instance_name: str, remote_jid: str, duration: int = 2000):
    """
    Simula o indicador 'digitando...' para o cliente.
    """
    url = f"{EVOLUTION_API_URL}/chat/sendPresence/{instance_name}"
    payload = {
        "number": remote_jid,
        "options": {
            "presence": "composing",
            "delay": duration,
        }
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, json=payload, headers=_get_headers())
    except Exception:
        pass  # Não crítico

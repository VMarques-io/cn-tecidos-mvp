"""Webhook handler para receber eventos da Evolution API v2.3.7."""

import os
import logging
from fastapi import APIRouter, Request, HTTPException

from services import whatsapp as wpp_service
from agents.state import AgentState

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "cn-tecidos")

HANDOFF_LINK = (
    "https://api.whatsapp.com/send/?phone=558335073620"
    "&text=Ol%C3%A1%21+Gostaria+de+falar+com+um+atendente+da+C%26N+Tecidos."
    "&type=phone_number&app_absent=0"
)

_processed_message_ids: set = set()


@router.post("/evolution/webhook")
async def evolution_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning(f"[WEBHOOK] Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event", "")
    instance = payload.get("instance") or DEFAULT_INSTANCE
    
    event_upper = event.upper()
    if event_upper != "MESSAGES_UPSERT" and event_upper != "MESSAGES.UPSERT":
        logger.debug(f"[WEBHOOK] Ignored event: {event}")
        return {"status": "ignored", "event": event}

    data = payload.get("data", {})
    message_data = data if isinstance(data, dict) else {}

    if "messages" in message_data and isinstance(message_data["messages"], list):
        results = []
        for msg in message_data.get("messages", []):
            result = await _process_message(msg, instance)
            results.append(result)
        return {"status": "processed", "results": results}

    result = await _process_message(message_data, instance)
    return {"status": "processed", "result": result}


async def _process_message(message: dict, instance_name: str) -> dict:
    global _processed_message_ids
    
    key = message.get("key", {})
    remote_jid = key.get("remoteJid", "")
    from_me = key.get("fromMe", False)
    message_id = key.get("id", "")
    
    if not remote_jid:
        logger.warning("[WEBHOOK] Missing remote_jid")
        return {"status": "error", "reason": "missing_remote_jid"}
    
    if not message_id:
        logger.warning("[WEBHOOK] Missing message_id")
        return {"status": "error", "reason": "missing_message_id"}
    
    if from_me:
        logger.debug(f"[WEBHOOK] Ignored (fromMe=True): {message_id}")
        return {"status": "ignored", "reason": "from_me"}
    
    if "@g.us" in remote_jid:
        logger.debug(f"[WEBHOOK] Ignored (group): {remote_jid}")
        return {"status": "ignored", "reason": "group"}
    
    if message_id in _processed_message_ids:
        logger.debug(f"[WEBHOOK] Ignored (duplicate): {message_id}")
        return {"status": "ignored", "reason": "duplicate"}
    
    _processed_message_ids.add(message_id)
    
    parsed = _parse_message_content(message)
    incoming_text = parsed.get("text")
    incoming_media_type = parsed.get("media_type")
    
    if incoming_media_type != "text":
        logger.info(f"[WEBHOOK] Ignored media message: {incoming_media_type} from {remote_jid[:12]}...")
        return {"status": "ignored", "reason": "media_not_supported", "media_type": incoming_media_type}
    
    if not incoming_text:
        logger.warning(f"[WEBHOOK] Empty text message from {remote_jid[:12]}...")
        return {"status": "ignored", "reason": "empty_text"}
    
    logger.info(f"[WEBHOOK] Processing: jid={remote_jid[:12]}... msg_id={message_id[:16]}...")
    
    initial_state: AgentState = {
        "remote_jid": remote_jid,
        "instance_name": instance_name,
        "profile_type": "curioso",
        "incoming_text": incoming_text,
        "intent": None,
        "flow_step": "idle",
        "chat_history": [],
        "response": None,
        "is_human_active": False,
        "should_end": False,
    }
    
    try:
        from agents.fashion_graph import fashion_graph
        final_state = await fashion_graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"[WEBHOOK] Graph error: {e}")
        error_message = f"Ops! Ocorreu um erro interno. Por favor, tente novamente ou fale com um atendente:\n{HANDOFF_LINK} 🙏"
        try:
            await wpp_service.send_text(instance_name, remote_jid, error_message)
        except Exception as send_error:
            logger.error(f"[WEBHOOK] Failed to send error message: {send_error}")
        return {"status": "error", "reason": "graph_error", "error": str(e)}
    
    response_text = final_state.get("response")
    
    try:
        if response_text:
            await wpp_service.send_text(instance_name, remote_jid, response_text)
            logger.info(f"[WEBHOOK] Sent text to {remote_jid[:12]}...")
        else:
            logger.warning(f"[WEBHOOK] No response to send for {remote_jid[:12]}...")
            
    except Exception as e:
        logger.error(f"[WEBHOOK] Failed to send response: {e}")
        return {"status": "error", "reason": "send_failed", "error": str(e)}
    
    logger.info(f"[WEBHOOK] Done: jid={remote_jid[:12]}... step={final_state.get('flow_step')}")
    return {"status": "success", "flow_step": final_state.get("flow_step")}


def _parse_message_content(message: dict) -> dict:
    result = {"text": None, "media_url": None, "media_type": "unknown", "media_mime": None}
    msg_content = message.get("message", {})
    if not msg_content:
        return result
    
    if "conversation" in msg_content:
        result["text"] = msg_content["conversation"]
        result["media_type"] = "text"
        return result
    
    if "extendedTextMessage" in msg_content:
        result["text"] = msg_content["extendedTextMessage"].get("text", "")
        result["media_type"] = "text"
        return result
    
    if "imageMessage" in msg_content:
        img = msg_content["imageMessage"]
        result["text"] = img.get("caption", "")
        result["media_url"] = img.get("url", "") or img.get("directPath", "")
        result["media_type"] = "image"
        result["media_mime"] = img.get("mimetype", "image/jpeg")
        return result
    
    if "videoMessage" in msg_content:
        vid = msg_content["videoMessage"]
        result["text"] = vid.get("caption", "")
        result["media_type"] = "video"
        result["media_mime"] = vid.get("mimetype", "video/mp4")
        return result
    
    if "audioMessage" in msg_content or "pttMessage" in msg_content:
        audio = msg_content.get("audioMessage") or msg_content.get("pttMessage", {})
        result["media_type"] = "audio"
        result["media_mime"] = audio.get("mimetype", "audio/ogg")
        return result
    
    if "documentMessage" in msg_content:
        doc = msg_content["documentMessage"]
        result["text"] = doc.get("caption", doc.get("fileName", ""))
        result["media_type"] = "document"
        result["media_mime"] = doc.get("mimetype", "application/pdf")
        return result
    
    if "stickerMessage" in msg_content:
        result["text"] = "[sticker]"
        result["media_type"] = "sticker"
        return result
    
    return result

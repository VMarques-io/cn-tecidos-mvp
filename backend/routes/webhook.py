"""Webhook handler para receber eventos da Evolution API v2.3.7."""

import os
import time
import logging
import traceback
from fastapi import APIRouter, Request, HTTPException

from services import whatsapp as wpp_service
from agents.state import AgentState

logger = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "cn-tecidos")

HANDOFF_LINK = os.environ.get(
    "HANDOFF_LINK",
    "https://api.whatsapp.com/send/?phone=558335073620"
    "&text=Ol%C3%A1%21+Gostaria+de+falar+com+um+atendente+da+C%26N+Tecidos."
    "&type=phone_number&app_absent=0"
)

AI_FAILURE_MESSAGE = (
    "Me perdoa, mas vou ter que transferir seu atendimento, tá bom? 🙏\n\n"
    f"É só clicar aqui pra falar com a gente: {HANDOFF_LINK}"
)

_processed_message_ids: set = set()


@router.post("/evolution/webhook")
@router.post("/evolution/webhook/{event_path}")
async def evolution_webhook(request: Request, event_path: str = ""):
    """Handle webhook from Evolution API."""
    t0 = time.time()
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning(f"[WEBHOOK] Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("event", "")
    if not event and event_path:
        event = event_path.upper().replace("-", "_")
        payload["event"] = event

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
        elapsed = time.time() - t0
        logger.info(f"[WEBHOOK] Batch complete: {len(results)} msgs in {elapsed:.2f}s")
        return {"status": "processed", "results": results, "elapsed_s": round(elapsed, 2)}

    result = await _process_message(message_data, instance)
    elapsed = time.time() - t0
    result["elapsed_s"] = round(elapsed, 2)
    logger.info(f"[WEBHOOK] Complete: status={result.get('status')} elapsed={elapsed:.2f}s")
    return {"status": "processed", "result": result}


async def _process_message(message: dict, instance_name: str) -> dict:
    global _processed_message_ids
    t0 = time.time()
    
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
        logger.debug(f"[WEBHOOK] Ignored (fromMe): {message_id}")
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
        logger.info(f"[WEBHOOK] Ignored media: {incoming_media_type} from {remote_jid[:20]}")
        return {"status": "ignored", "reason": "media_not_supported", "media_type": incoming_media_type}
    
    if not incoming_text:
        logger.warning(f"[WEBHOOK] Empty text from {remote_jid[:20]}")
        return {"status": "ignored", "reason": "empty_text"}
    
    logger.info(f"[WEBHOOK] >>> START processing: jid={remote_jid[:20]} text=\"{incoming_text[:50]}\" msg_id={message_id[:20]}")
    
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
    logger.info(f"[WEBHOOK] Step 1: State built ({time.time()-t0:.2f}s)")
    
    # Step 2: Run LangGraph
    try:
        logger.info(f"[WEBHOOK] Step 2: Invoking graph...")
        from agents.fashion_graph import fashion_graph
        logger.info(f"[WEBHOOK] Step 2a: Graph imported ({time.time()-t0:.2f}s)")
        final_state = await fashion_graph.ainvoke(initial_state)
        logger.info(f"[WEBHOOK] Step 2b: Graph completed ({time.time()-t0:.2f}s) intent={final_state.get('intent')} step={final_state.get('flow_step')}")
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"[WEBHOOK] Step 2 FAILED: Graph error after {elapsed:.2f}s: {e}\n{traceback.format_exc()}")
        # Send friendly failure message instead of raw error
        try:
            await wpp_service.send_text(instance_name, remote_jid, AI_FAILURE_MESSAGE)
            logger.info(f"[WEBHOOK] Sent AI failure handoff message to {remote_jid[:20]}")
        except Exception as send_error:
            logger.error(f"[WEBHOOK] Failed to send even the failure message: {send_error}")
        return {"status": "error", "reason": "graph_error", "error": str(e), "elapsed_s": round(elapsed, 2)}
    
    # Step 3: Send response
    response_text = final_state.get("response")
    logger.info(f"[WEBHOOK] Step 3: Response generated ({time.time()-t0:.2f}s) len={len(response_text) if response_text else 0}")
    
    try:
        if response_text:
            await wpp_service.send_text(instance_name, remote_jid, response_text)
            elapsed = time.time() - t0
            logger.info(f"[WEBHOOK] Step 3a: Response sent ({elapsed:.2f}s)")
        else:
            # No response from graph — send failure handoff
            logger.warning(f"[WEBHOOK] Step 3a: No response generated — sending AI failure handoff")
            await wpp_service.send_text(instance_name, remote_jid, AI_FAILURE_MESSAGE)
            elapsed = time.time() - t0
            logger.info(f"[WEBHOOK] Step 3a: Failure handoff sent ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"[WEBHOOK] Step 3 FAILED: Send error after {elapsed:.2f}s: {e}\n{traceback.format_exc()}")
        return {"status": "error", "reason": "send_failed", "error": str(e), "elapsed_s": round(elapsed, 2)}
    
    elapsed = time.time() - t0
    logger.info(f"[WEBHOOK] <<< DONE: jid={remote_jid[:20]} intent={final_state.get('intent')} step={final_state.get('flow_step')} total={elapsed:.2f}s")
    return {"status": "success", "flow_step": final_state.get("flow_step"), "intent": final_state.get("intent"), "elapsed_s": round(elapsed, 2)}


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

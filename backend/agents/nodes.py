import os
import logging
from typing import Dict, Any

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .state import AgentState

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

HANDOFF_LINK = os.environ.get(
    "HANDOFF_LINK",
    "https://api.whatsapp.com/send/?phone=558335073620"
    "&text=Ol%C3%A1%21+Gostaria+de+falar+com+um+atendente+da+C%26N+Tecidos."
    "&type=phone_number&app_absent=0"
)

AI_FAILURE_MESSAGE = (
    "Me perdoa, mas vou ter que transferir seu atendimento, tá bom?\n\n"
    f"É só clicar aqui pra falar com a gente: {HANDOFF_LINK}"
)

STORE_CONTEXT = (
    "C&N Tecidos é uma loja de tecidos e aviamentos em Campina Grande, PB. "
    "Oferece tecidos variados: algodão, linho, seda, viscose, jeans, malha, "
    "tecido para festa, tecido para decoração, aviamentos como botões, "
    "zíperes, linhas, elásticos. Atende tanto pessoa física quanto profissional "
    "de moda e costura. Preços acessíveis e atendimento personalizado."
)


def _call_gemini(prompt: str) -> str:
    """Call Gemini API. Returns empty string on any failure."""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")
        if genai is None:
            raise RuntimeError("google-generativeai not installed")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)

        if response and response.text:
            return response.text
        raise ValueError("Empty Gemini response")
    except Exception as e:
        logger.error(f"[GEMINI] FAILED: {e}")
        return ""


def conversation_node(state: AgentState) -> Dict[str, Any]:
    """Single conversational node. Camila talks naturally and decides
    what to do based on the conversation flow, not robotic classification."""
    incoming = state.get("incoming_text", "")
    is_human_active = state.get("is_human_active", False)

    # If customer already asked for human and we transferred,
    # stay in handoff mode (but allow them to come back)
    if is_human_active:
        # If they send a new message after handoff, reset and talk again
        # (maybe the human didn't respond and they're trying the bot again)
        lower = incoming.lower().strip()
        comeback_words = ["voltar", "quero voltar", "cancelar", "esquece", "conversar com voce", "falar com voce"]
        if any(w in lower for w in comeback_words):
            is_human_active = False
        else:
            return {
                "node": "END",
                "state_update": {"flow_step": "handoff"},
                "response": f"Seu atendimento já foi transferido! Se quiser voltar a conversar comigo, é só mandar uma mensagem.\n\nPro atendente: {HANDOFF_LINK}",
            }

    # Build conversation prompt
    prompt = (
        "Você é a Camila, que trabalha na C&N Tecidos em Campina Grande, PB. "
        "Você atende clientes pelo WhatsApp de forma natural, como uma pessoa real conversando.\n\n"
        "REGRAS:\n"
        "- Converse normalmente, como uma pessoa real no WhatsApp\n"
        "- Seja breve (2-4 linhas)\n"
        "- NAO use emojis\n"
        "- NAO se apresente como bot, assistente ou IA\n"
        "- NAO diga 'como posso ajudar' se ja esta respondendo algo\n"
        "- NAO liste opcoes numeradas\n"
        "- Se nao souber algo, seja honesta e sugira visitar a loja\n"
        "- Se o cliente pedir explicitamente para falar com atendente/humano, responda EXATAMENTE assim: [HANDOFF]\n"
        "- Se o cliente quiser encerrar, responda EXATAMENTE assim: [CANCEL]\n"
        "- Para qualquer outra coisa, apenas converse naturalmente\n\n"
        f"Sobre a loja: {STORE_CONTEXT}\n\n"
        f"Cliente diz: {incoming}\n\n"
        "Sua resposta:"
    )

    answer = _call_gemini(prompt)

    # Gemini failed (quota, error, etc)
    if not answer:
        logger.warning(f"[CONVERSATION] Gemini failed — sending failure handoff")
        return {
            "node": "END",
            "state_update": {"flow_step": "ai_failure", "is_human_active": True},
            "response": AI_FAILURE_MESSAGE,
        }

    # Check if Gemini decided to handoff or cancel
    answer_stripped = answer.strip()
    if "[HANDOFF]" in answer_stripped:
        # Remove the tag and send friendly handoff
        clean = answer_stripped.replace("[HANDOFF]", "").strip()
        handoff_msg = f"{clean}\n\nÉ só clicar aqui: {HANDOFF_LINK}"
        return {
            "node": "END",
            "state_update": {"is_human_active": True, "flow_step": "handoff"},
            "response": handoff_msg,
        }

    if "[CANCEL]" in answer_stripped:
        clean = answer_stripped.replace("[CANCEL]", "").strip()
        goodbye = clean if clean else "Tudo bem! Se precisar, é só mandar mensagem."
        return {
            "node": "END",
            "state_update": {"flow_step": "idle"},
            "response": goodbye,
        }

    # Normal conversation response
    logger.info(f"[CONVERSATION] Replied to \"{incoming[:50]}\" → {len(answer)} chars")
    return {
        "node": "END",
        "state_update": {"flow_step": "idle"},
        "response": answer_stripped,
    }

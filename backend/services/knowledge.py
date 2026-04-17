"""Módulo de base de conhecimento para C&N Tecidos MVP."""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWLEDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "knowledge", "processed_knowledge.json")


def _load_knowledge() -> dict:
    try:
        with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("[KNOWLEDGE] processed_knowledge.json não encontrado.")
        return {}
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao carregar base: {e}")
        return {}

_KNOWLEDGE: dict = _load_knowledge()


def get_fabric_context() -> str:
    fabrics = _KNOWLEDGE.get("fabrics", [])
    if not fabrics:
        return ""
    lines = ["TECIDOS E SUAS APLICAÇÕES IDEAIS:"]
    for f in fabrics:
        nome = f.get("nome", "")
        desc = f.get("descricao", "Sem descrição")
        lines.append(f"- {nome}: {desc}")
    return "\n".join(lines)


def resolve_color(query: str) -> Optional[dict]:
    color_map = _KNOWLEDGE.get("color_variations", {})
    return color_map.get(query.lower().strip())



def get_body_type_guide(body_type: str) -> Optional[dict]:
    guide = _KNOWLEDGE.get("body_types_guide", {})
    for key, value in guide.items():
        if key.lower() in body_type.lower() or body_type.lower() in key.lower():
            return value
    return None

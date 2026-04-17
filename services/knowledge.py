"""Módulo de base de conhecimento para C&N Tecidos MVP.

Fornece acesso aos tecidos, variações de cor e guias de estilo.
O conhecimento é cacheado em nível de módulo na primeira importação.
"""

import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_KNOWLEDGE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "knowledge", "processed_knowledge.json"
)


def _load_knowledge() -> dict:
    """Carrega e cacheia a base de conhecimento em memória.

    Returns:
        dict: Base de conhecimento completa ou dict vazio se não encontrar.
    """
    try:
        with open(_KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(
            "[KNOWLEDGE] processed_knowledge.json não encontrado. FAQ sem base especializada."
        )
        return {}
    except Exception as e:
        logger.error(f"[KNOWLEDGE] Erro ao carregar base: {e}")
        return {}


# Cache em módulo (carrega uma vez na inicialização)
_KNOWLEDGE: dict = _load_knowledge()


def _get_fabric_context() -> str:
    """Formata a lista de tecidos para injeção no prompt do Gemini.

    Returns:
        str: Texto formatado com todos os tecidos e suas aplicações ideais.
    """
    fabrics = _KNOWLEDGE.get("fabrics", [])
    if not fabrics:
        return ""

    lines = ["TECIDOS E SUAS APLICAÇÕES IDEAIS:"]
    for f in fabrics:
        nome = f.get("nome", "")
        desc = f.get("descricao", "Sem descrição")
        lines.append(f"- {nome}: {desc}")

    return "\n".join(lines)


def _resolve_color(query: str) -> Optional[dict]:
    """Resolve uma variação de cor informal para a cor base e tecidos associados.

    Ex: "carmim" → {"cor_base": "vermelho escuro", "tecidos": [...]}

    Args:
        query: Nome da cor a resolver (case-insensitive).

    Returns:
        dict com cor_base e tecidos, ou None se não encontrar.
    """
    color_map = _KNOWLEDGE.get("color_variations", {})
    return color_map.get(query.lower().strip())


def _get_body_type_guide(body_type: str) -> Optional[dict]:
    """Retorna o guia de estilo para um determinado biotipo.

    Args:
        body_type: Nome do biotipo (busca case-insensitive).

    Returns:
        dict com o guia de estilo ou None se não encontrar.
    """
    guide = _KNOWLEDGE.get("body_types_guide", {})
    # Busca case-insensitive
    for key, value in guide.items():
        if key.lower() in body_type.lower() or body_type.lower() in key.lower():
            return value
    return None

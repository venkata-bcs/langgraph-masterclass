"""Filename/content based routing classification, backed by the LLM
fallback chain with a deterministic heuristic fallback so the router still
works offline / without valid API keys.
"""
from __future__ import annotations

import json
import re

from src.common.llm_clients import LLMUnavailableError, chat

# Files written by our own genai_datagen pipeline are named
# `<YYYYMMDD>_<HHMMSS>_<table-name>.csv` -- when that pattern matches, the
# table name IS the target folder, full stop. Routing those through the LLM
# is both wasteful and risky: a semantically-reasoning model can talk itself
# into merging two clearly-distinct tables (e.g. "products" into "inventory")
# because their columns are thematically related. The LLM/heuristic path
# below is reserved for genuinely unpredictable external filenames (e.g.
# "sales-2034", "daily-sale") where no such convention exists.
_GENERATOR_FILENAME_RE = re.compile(r"^\d{8}_\d{6}_([\w-]+)\.csv$", re.IGNORECASE)

_KNOWN_HINTS = {
    "product-category": ["category", "categories"],
    "product-prices-month-year": ["price", "prices"],
    "products": ["product"],
    "inventory": ["inventory", "stock"],
    "sales": ["sale", "sales"],
    "daily-sale": ["daily-sale", "daily_sale"],
}


def _heuristic_classify(filename: str, known_targets: list) -> dict:
    name = filename.lower()
    for target, hints in _KNOWN_HINTS.items():
        if any(h in name for h in hints):
            return {
                "target_folder": target,
                "is_new_category": target not in known_targets,
                "confidence": 0.6,
                "reasoning": f"heuristic keyword match on '{name}'",
            }
    stem = name.rsplit(".", 1)[0]
    fallback_target = re.sub(r"[\d_]+", "-", stem).strip("-_ ") or "misc"
    return {
        "target_folder": fallback_target,
        "is_new_category": fallback_target not in known_targets,
        "confidence": 0.3,
        "reasoning": "no keyword hint matched; derived folder name from filename",
    }


def classify_file(filename: str, header_preview: str, known_targets: list) -> dict:
    generator_match = _GENERATOR_FILENAME_RE.match(filename)
    if generator_match:
        table_name = generator_match.group(1)
        return {
            "target_folder": table_name,
            "is_new_category": table_name not in known_targets,
            "confidence": 1.0,
            "reasoning": f"filename matches the genai_datagen naming convention for table '{table_name}'",
        }

    prompt = (
        f"A new data file named '{filename}' appeared in a source-data drop "
        f"folder. Its header/first line is: {header_preview!r}. Existing "
        f"target-data subfolders are: {known_targets}. Decide which target "
        "subfolder this file belongs in. If it clearly matches an existing "
        "one, reuse it exactly. If it's a genuinely new kind of data, propose "
        "a new short kebab-case folder name. Reply with ONLY a JSON object: "
        '{"target_folder": str, "is_new_category": bool, "confidence": '
        '0-1 float, "reasoning": str}.'
    )
    try:
        raw, _provider = chat(prompt, system="You are a precise data routing assistant. Reply with strict JSON only.")
        start, end = raw.find("{"), raw.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no JSON object found in LLM response")
        decision = json.loads(raw[start : end + 1])
        decision.setdefault("target_folder", "misc")
        decision.setdefault("is_new_category", decision["target_folder"] not in known_targets)
        return decision
    except (LLMUnavailableError, ValueError, json.JSONDecodeError, KeyError):
        return _heuristic_classify(filename, known_targets)

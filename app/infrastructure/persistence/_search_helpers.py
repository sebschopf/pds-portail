"""Helper partage : parsing de tags CSV/JSON.

Utilise par dataset_detail_adapter, compare_adapter et search_adapter.
ADR-003 (SRP) : ce module ne fait QUE du parsing de donnees,
pas d'agregation SQL ni de presentation.
"""

from __future__ import annotations

import json
from typing import cast


def parse_tags(tags_str: str | None) -> list[str]:
    """Parse la chaine CSV-like de tags vers une liste.

    Formats acceptes :
    - CSV: "tag1, tag2, tag3"
    - JSON: '["tag1", "tag2"]'
    """
    if not tags_str:
        return []
    if tags_str.startswith("["):
        try:
            parsed = json.loads(tags_str)
            if isinstance(parsed, list):
                parsed_list = cast(list[object], parsed)
                return [str(item).strip() for item in parsed_list if str(item).strip()]
            return []
        except (json.JSONDecodeError, ValueError):
            return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]

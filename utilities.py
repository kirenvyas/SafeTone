from __future__ import annotations

from difflib import get_close_matches
from typing import Iterable, Optional


def fuzzy_match(text: str, choices: Iterable[str], cutoff: float) -> Optional[str]:
    if not text:
        return None
    choice_list = list(choices)
    matches = get_close_matches(text.lower().strip(), [c.lower() for c in choice_list], n=1, cutoff=cutoff)
    if not matches:
        return None
    lookup = {c.lower(): c for c in choice_list}
    return lookup.get(matches[0])

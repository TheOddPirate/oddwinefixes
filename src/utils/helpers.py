"""
Helper utilities for scoring and prioritizing runtime verbs.
"""

import re
from typing import List, Optional

from oddwinefixes.const import DOTNET_RELEASE_MAP

#did i end up with double implmentation of this?
def prioritize_verbs_by_year(verbs: List[str], build_year: Optional[int]) -> List[str]:
    """Sorts verbs (e.g. vcrun or dotnet) according to proximity to target build year."""
    if not build_year:
        return verbs

    def calculate_score(verb: str) -> int:
        verb_lower = verb.lower()

        match = re.search(r"\d{4}", verb)
        if match:
            target = int(match.group())
            return abs(build_year - target)

        for dotnet_verb, year in DOTNET_RELEASE_MAP.items():
            if dotnet_verb in verb_lower:
                return abs(build_year - year)

        return 999

    return sorted(verbs, key=calculate_score)

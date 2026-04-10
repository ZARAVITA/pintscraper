"""
Scoring Module
Assigns a performance score to each scraped pin.

Current formula (v1):
    score = (1 / position) * POSITION_WEIGHT
            + repetition_factor * REPETITION_WEIGHT

Future extensions:
    - NLP signals (keyword density in title/description)
    - Image quality signals
    - Temporal signals (recency boost)
    - Engagement estimates via third-party APIs
"""

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scraper.pinterest_scraper import Pin

# ---------------------------------------------------------------------------
# Weights — tweak without touching algorithm logic
# ---------------------------------------------------------------------------

POSITION_WEIGHT: float = 1.0
REPETITION_WEIGHT: float = 0.5
MAX_REPETITION_BONUS: float = 2.0  # Cap so outliers don't dominate


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_scores(pins: list["Pin"]) -> list["Pin"]:
    """
    Mutates each Pin in-place, setting its `.score` attribute.
    Returns the same list for convenience.
    """
    if not pins:
        return pins

    repetition_map = _build_repetition_map(pins)

    for pin in pins:
        pin.score = _compute_score(pin.position, repetition_map.get(pin.image_url, 1))

    return pins


def _build_repetition_map(pins: list["Pin"]) -> dict[str, int]:
    """
    Count how many times each image_url appears across all results.
    A pin appearing multiple times likely has higher organic traction.
    """
    image_counts = Counter(p.image_url for p in pins if p.image_url)
    return dict(image_counts)


def _compute_score(position: int, repetitions: int) -> float:
    """
    Core scoring formula.

    Args:
        position: 1-indexed rank in search results (lower = better).
        repetitions: How many times this pin's image appeared in results.

    Returns:
        Float score (higher = better performing).
    """
    if position <= 0:
        position = 1

    position_score = POSITION_WEIGHT / position

    # Repetition factor: 1 appearance = 0 bonus, 2+ appearances = bonus
    rep_factor = min(repetitions - 1, MAX_REPETITION_BONUS)
    repetition_score = REPETITION_WEIGHT * rep_factor

    return round(position_score + repetition_score, 6)


# ---------------------------------------------------------------------------
# Future: NLP scoring signals (stub — ready for implementation)
# ---------------------------------------------------------------------------

def nlp_title_score(title: str, keyword: str) -> float:
    """
    Placeholder for NLP-based title relevance scoring.
    Intended extension: use spaCy / transformers to score semantic similarity.
    """
    if not title or not keyword:
        return 0.0
    # Simple keyword-in-title check as v0 baseline
    return 0.1 if keyword.lower() in title.lower() else 0.0


def keyword_density_score(text: str, keyword: str) -> float:
    """
    Placeholder for keyword density analysis.
    Future: integrate with NLP pipeline.
    """
    if not text or not keyword:
        return 0.0
    words = text.lower().split()
    kw_words = keyword.lower().split()
    matches = sum(1 for w in words if w in kw_words)
    return round(matches / max(len(words), 1), 4)
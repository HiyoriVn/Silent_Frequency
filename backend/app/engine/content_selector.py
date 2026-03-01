"""
Silent Frequency — Adaptive Content Selector
==============================================

Selects the next puzzle item based on current mastery and recent history.

SELECTION STRATEGY
------------------

1. DIFFICULTY MAPPING (deterministic)
   Given mastery P(Lₙ):
       P(Lₙ) < 0.4          → tier "low"   (difficulty 1)
       0.4 ≤ P(Lₙ) < 0.7    → tier "mid"   (difficulty 2)
       P(Lₙ) ≥ 0.7          → tier "high"  (difficulty 3)

   This is delegated to bkt_core.select_difficulty() for consistency.

2. POOL FILTERING
   From the full item catalog, keep only items that match:
     a) the requested skill
     b) the target difficulty tier

3. REPETITION PREVENTION
   Remove any item whose item_id appears in `recent_ids` (the last N items served).
   This prevents the player from seeing the same puzzle variant back-to-back.

4. FALLBACK TIERS
   If the filtered pool is empty after steps 2–3, relax the difficulty constraint:
     - Try the adjacent tier first (mid→low or mid→high, preferring easier)
     - Then try all remaining tiers
   This guarantees a result as long as the catalog has ≥1 item for the skill.

5. WEIGHTED RANDOM SELECTION
   Among eligible items, pick one using weighted random sampling:
     - Each item has a base `weight` (default 1.0).
     - Items that have NOT appeared in `recent_ids` already passed step 3,
       but items that appeared further back in history get a mild bonus
       (recency decay) to further diversify selection.
   The formula for effective weight:
       w_eff = item.weight × recency_boost
   where recency_boost = 1.0 for items not in history, and the boost is
   omitted entirely for items removed in step 3.

   Weighted sampling uses the standard cumulative-distribution approach
   with Python's `random` module — no external libraries.

EDGE CASES
----------
- Empty catalog for skill         → raises ValueError (configuration error)
- All items exhausted by history  → clear history and retry (graceful reset)
- Single item in pool             → deterministic pick, no randomness needed
- mastery exactly on threshold    → handled by ≥ comparison (0.4 → mid, 0.7 → high)
"""

import random
from typing import Sequence

from .bkt_core import select_difficulty
from .bkt_params import DifficultyTier
from .selector_types import PuzzleItem, SelectionResult

# ──────────────────────────────────────────────
# Tier fallback order: when the ideal tier is
# empty, try these tiers in listed order.
# ──────────────────────────────────────────────
_FALLBACK_ORDER: dict[DifficultyTier, list[DifficultyTier]] = {
    "low":  ["mid", "high"],
    "mid":  ["low", "high"],
    "high": ["mid", "low"],
}

# Maximum recent-history length.  Larger values prevent more repetition
# but risk exhausting small pools.  5 is tuned for a 15–20 min demo with
# ~15 puzzle variants per skill.
DEFAULT_HISTORY_SIZE: int = 5


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def select_difficulty_from_mastery(mastery: float) -> DifficultyTier:
    """
    Pure mapping from mastery probability to difficulty tier.

    Delegates to bkt_core.select_difficulty() so the thresholds
    are defined in exactly one place.

    Parameters
    ----------
    mastery : float — P(Lₙ) in [0, 1].

    Returns
    -------
    DifficultyTier — "low", "mid", or "high".
    """
    return select_difficulty(mastery)


def select_item(
    catalog: Sequence[PuzzleItem],
    skill: str,
    mastery: float,
    recent_ids: list[str] | None = None,
    rng: random.Random | None = None,
) -> SelectionResult:
    """
    Pick the next puzzle item adaptively.

    Parameters
    ----------
    catalog    : Sequence[PuzzleItem] — Full item pool (all skills, all tiers).
    skill      : str                  — Target skill code ("vocabulary", etc.).
    mastery    : float                — Current P(Lₙ) for this skill.
    recent_ids : list[str] | None     — Item IDs recently served (most-recent last).
                                        Pass the mutable list; this function will
                                        append the selected ID and trim to history size.
    rng        : random.Random | None — Injectable RNG for deterministic testing.
                                        If None, uses module-level random.

    Returns
    -------
    SelectionResult — The chosen item plus metadata.

    Raises
    ------
    ValueError — If the catalog has zero items for the requested skill.
    """
    if rng is None:
        rng = random.Random()

    if recent_ids is None:
        recent_ids = []

    # ── Step 1: Determine target tier ──
    target_tier = select_difficulty_from_mastery(mastery)

    # ── Step 2: Filter by skill ──
    skill_pool = [item for item in catalog if item.skill == skill]

    if not skill_pool:
        raise ValueError(
            f"No items in catalog for skill '{skill}'. "
            f"Check puzzle configuration."
        )

    # ── Step 3: Filter by tier + remove recent ──
    result = _try_select_from_tier(skill_pool, target_tier, recent_ids, rng)

    if result is not None:
        _update_history(recent_ids, result.selected.item_id)
        return result

    # ── Step 4: Fallback tiers ──
    for fallback_tier in _FALLBACK_ORDER[target_tier]:
        result = _try_select_from_tier(skill_pool, fallback_tier, recent_ids, rng)
        if result is not None:
            _update_history(recent_ids, result.selected.item_id)
            return SelectionResult(
                selected=result.selected,
                tier_used=fallback_tier,
                pool_size=result.pool_size,
                fallback_used=True,
            )

    # ── Step 5: All tiers exhausted by history → reset history and retry ──
    recent_ids.clear()
    return select_item(catalog, skill, mastery, recent_ids, rng)


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

def _try_select_from_tier(
    skill_pool: list[PuzzleItem],
    tier: DifficultyTier,
    recent_ids: list[str],
    rng: random.Random,
) -> SelectionResult | None:
    """
    Attempt to pick an item from a specific tier, excluding recent IDs.
    Returns None if no eligible items remain.
    """
    tier_pool = [
        item for item in skill_pool
        if item.difficulty == tier and item.item_id not in recent_ids
    ]

    if not tier_pool:
        return None

    selected = _weighted_choice(tier_pool, rng)

    return SelectionResult(
        selected=selected,
        tier_used=tier,
        pool_size=len(tier_pool),
        fallback_used=False,
    )


def _weighted_choice(items: list[PuzzleItem], rng: random.Random) -> PuzzleItem:
    """
    Weighted random selection from a non-empty list of PuzzleItems.

    Uses cumulative distribution sampling:
        1. Compute cumulative weights.
        2. Draw uniform random in [0, total_weight).
        3. Binary-search (linear here — pools are small) for the bucket.

    If all weights are 0, falls back to uniform random.
    """
    total = sum(item.weight for item in items)

    if total == 0.0:
        # Degenerate: all zero-weight items → uniform fallback
        return rng.choice(items)

    r = rng.uniform(0.0, total)
    cumulative = 0.0

    for item in items:
        cumulative += item.weight
        if r <= cumulative:
            return item

    # Floating-point guard: return last item
    return items[-1]


def _update_history(recent_ids: list[str], item_id: str) -> None:
    """
    Append the selected item ID and trim the history to DEFAULT_HISTORY_SIZE.
    """
    recent_ids.append(item_id)
    while len(recent_ids) > DEFAULT_HISTORY_SIZE:
        recent_ids.pop(0)

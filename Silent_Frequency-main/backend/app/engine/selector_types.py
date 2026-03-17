"""
Silent Frequency — Content Selection Data Structures

Defines the puzzle item catalog types used by the adaptive selector.
No external dependencies.
"""

from dataclasses import dataclass, field
from typing import Literal

from .bkt_params import DifficultyTier


@dataclass(frozen=True)
class PuzzleItem:
    """
    One selectable puzzle variant in the item pool.

    Attributes
    ----------
    item_id     : str            — Unique identifier (e.g., "room1_vocab_decode__mid").
    puzzle_id   : str            — Parent puzzle group this variant belongs to.
    skill       : str            — Skill code: "vocabulary", "grammar", or "listening".
    difficulty  : DifficultyTier — "low", "mid", or "high".
    weight      : float          — Base selection weight (higher = more likely to be picked).
                                   Default 1.0; can be authored higher for pedagogically
                                   preferred items.
    """

    item_id: str
    puzzle_id: str
    skill: str
    difficulty: DifficultyTier
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight < 0.0:
            raise ValueError(f"weight must be ≥ 0, got {self.weight}")


@dataclass(frozen=True)
class SelectionResult:
    """
    Immutable record returned by select_item().

    Attributes
    ----------
    selected      : PuzzleItem       — The chosen item.
    tier_used     : DifficultyTier   — Difficulty tier that was targeted.
    pool_size     : int              — How many candidates were in the eligible pool.
    fallback_used : bool             — True if the selector had to relax tier constraints.
    """

    selected: PuzzleItem
    tier_used: DifficultyTier
    pool_size: int
    fallback_used: bool

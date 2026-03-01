"""
Silent Frequency — Adaptive Learning Engine

A pure-Python, modular implementation of:
  1. Bayesian Knowledge Tracing (BKT) — mastery estimation
  2. Content Selector — adaptive item selection with weighted randomness
"""

from .bkt_core import update_mastery, apply_learning_transition, select_difficulty
from .bkt_params import SkillParams, SkillState, AttemptResult
from .content_selector import select_difficulty_from_mastery, select_item
from .selector_types import PuzzleItem, SelectionResult

__all__ = [
    # BKT core
    "update_mastery",
    "apply_learning_transition",
    "select_difficulty",
    "SkillParams",
    "SkillState",
    "AttemptResult",
    # Content selector
    "select_difficulty_from_mastery",
    "select_item",
    "PuzzleItem",
    "SelectionResult",
]

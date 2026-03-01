"""
BKT data structures.

Plain dataclasses — no external dependencies.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class SkillParams:
    """
    Immutable BKT parameters for a single skill.

    Attributes
    ----------
    p_init : float   — P(L₀)  Prior probability the student already knows the skill.
    p_learn : float  — P(T)   Probability of transitioning from unlearned → learned on each opportunity.
    p_guess : float  — P(G)   Probability of a correct answer despite NOT knowing the skill.
    p_slip : float   — P(S)   Probability of an incorrect answer despite knowing the skill.
    """

    p_init: float
    p_learn: float
    p_guess: float
    p_slip: float

    def __post_init__(self) -> None:
        for name in ("p_init", "p_learn", "p_guess", "p_slip"):
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0, 1], got {value}")


@dataclass
class SkillState:
    """
    Mutable BKT state for one (session × skill) pair.

    Attributes
    ----------
    p_learned : float     — P(Lₙ) Current posterior mastery estimate.
    update_count : int    — Number of BKT updates applied so far.
    """

    p_learned: float
    update_count: int = 0

    @classmethod
    def from_params(cls, params: SkillParams) -> "SkillState":
        """Initialise state from skill-level defaults."""
        return cls(p_learned=params.p_init, update_count=0)


DifficultyTier = Literal["low", "mid", "high"]


@dataclass(frozen=True)
class AttemptResult:
    """
    Immutable record returned after every BKT update.

    Attributes
    ----------
    p_learned_before : float       — Mastery BEFORE this attempt.
    p_learned_after : float        — Mastery AFTER this attempt (including learning transition).
    posterior_given_obs : float     — Intermediate: P(Lₙ | obs) before learning transition.
    is_correct : bool              — Whether the student answered correctly.
    recommended_tier : DifficultyTier — Difficulty tier suggested for the NEXT puzzle.
    """

    p_learned_before: float
    p_learned_after: float
    posterior_given_obs: float
    is_correct: bool
    recommended_tier: DifficultyTier

"""
Silent Frequency — BKT Core Mathematics
=========================================

Standard Bayesian Knowledge Tracing (Corbett & Anderson, 1994).

NOTATION
--------
P(Lₙ)   — probability the student has LEARNED the skill after observation n
P(T)     — probability of learning on each opportunity  (learn rate)
P(G)     — probability of a correct response given the skill is NOT learned  (guess)
P(S)     — probability of an incorrect response given the skill IS learned   (slip)

STEP 1 — POSTERIOR UPDATE  (condition on observed response)
-----------------------------------------------------------
Given observation oₙ ∈ {correct, incorrect}:

  If oₙ = correct:
      P(Lₙ | correct) = P(Lₙ) · (1 − P(S))
                         ─────────────────────────────────────
                         P(Lₙ) · (1 − P(S)) + (1 − P(Lₙ)) · P(G)

  If oₙ = incorrect:
      P(Lₙ | incorrect) = P(Lₙ) · P(S)
                           ─────────────────────────────────────
                           P(Lₙ) · P(S) + (1 − P(Lₙ)) · (1 − P(G))

STEP 2 — LEARNING TRANSITION  (student may learn after the attempt)
-------------------------------------------------------------------
After incorporating the observation, an unlearned student may transition
to the learned state with probability P(T):

      P(Lₙ₊₁) = P(Lₙ | oₙ) + (1 − P(Lₙ | oₙ)) · P(T)

This is the new prior for the NEXT observation.

DIFFICULTY SELECTION
--------------------
Based on the updated mastery, select difficulty tier:
      P(Lₙ₊₁) < 0.4          → low
      0.4 ≤ P(Lₙ₊₁) < 0.7    → mid
      P(Lₙ₊₁) ≥ 0.7          → high
"""

from .bkt_params import SkillParams, SkillState, AttemptResult, DifficultyTier

# ──────────────────────────────────────────────
# Difficulty thresholds (configurable constants)
# ──────────────────────────────────────────────
THRESHOLD_LOW_MID: float = 0.4
THRESHOLD_MID_HIGH: float = 0.7


def _posterior_correct(p_learned: float, p_slip: float, p_guess: float) -> float:
    """
    P(Lₙ | oₙ = correct)

    Bayes' rule:
        numerator   = P(correct | learned) · P(learned) = (1 − S) · P(Lₙ)
        denominator = P(correct)           = (1 − S) · P(Lₙ) + G · (1 − P(Lₙ))
    """
    numerator = p_learned * (1.0 - p_slip)
    denominator = numerator + (1.0 - p_learned) * p_guess
    if denominator == 0.0:
        return p_learned  # degenerate case: avoid division by zero
    return numerator / denominator


def _posterior_incorrect(p_learned: float, p_slip: float, p_guess: float) -> float:
    """
    P(Lₙ | oₙ = incorrect)

    Bayes' rule:
        numerator   = P(incorrect | learned) · P(learned) = S · P(Lₙ)
        denominator = P(incorrect)           = S · P(Lₙ) + (1 − G) · (1 − P(Lₙ))
    """
    numerator = p_learned * p_slip
    denominator = numerator + (1.0 - p_learned) * (1.0 - p_guess)
    if denominator == 0.0:
        return p_learned
    return numerator / denominator


def apply_learning_transition(posterior: float, p_learn: float) -> float:
    """
    Apply the learning transition AFTER the posterior update.

    P(Lₙ₊₁) = P(Lₙ | oₙ) + (1 − P(Lₙ | oₙ)) · P(T)

    Parameters
    ----------
    posterior : float — P(Lₙ | oₙ) from Bayesian update step.
    p_learn   : float — P(T) transition probability.

    Returns
    -------
    float — Updated mastery P(Lₙ₊₁).
    """
    return posterior + (1.0 - posterior) * p_learn


def select_difficulty(p_learned: float) -> DifficultyTier:
    """
    Map current mastery estimate to a difficulty tier.

    Parameters
    ----------
    p_learned : float — Current P(Lₙ).

    Returns
    -------
    DifficultyTier — "low", "mid", or "high".
    """
    if p_learned < THRESHOLD_LOW_MID:
        return "low"
    elif p_learned < THRESHOLD_MID_HIGH:
        return "mid"
    else:
        return "high"


def update_mastery(
    state: SkillState,
    params: SkillParams,
    is_correct: bool,
) -> AttemptResult:
    """
    Full BKT update cycle: posterior update → learning transition → difficulty selection.

    This is the single public entry point called by the API layer on every puzzle attempt.

    Parameters
    ----------
    state      : SkillState  — Mutable state object; will be modified IN-PLACE.
    params     : SkillParams — Immutable BKT parameters for the skill.
    is_correct : bool        — Whether the student's response was correct.

    Returns
    -------
    AttemptResult — Frozen record of what happened (for logging / response).
    """
    p_before = state.p_learned

    # ── Step 1: Bayesian posterior update ──
    if is_correct:
        posterior = _posterior_correct(p_before, params.p_slip, params.p_guess)
    else:
        posterior = _posterior_incorrect(p_before, params.p_slip, params.p_guess)

    # ── Step 2: Learning transition ──
    p_after = apply_learning_transition(posterior, params.p_learn)

    # ── Step 3: Select difficulty for next puzzle ──
    tier = select_difficulty(p_after)

    # ── Mutate state in-place ──
    state.p_learned = p_after
    state.update_count += 1

    return AttemptResult(
        p_learned_before=p_before,
        p_learned_after=p_after,
        posterior_given_obs=posterior,
        is_correct=is_correct,
        recommended_tier=tier,
    )

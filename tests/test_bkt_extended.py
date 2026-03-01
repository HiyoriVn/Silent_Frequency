"""
Silent Frequency — QA Extended BKT + Adaptive Difficulty Tests

Covers edge cases, convergence properties, numerical stability,
and cross-component integration between BKT engine and content selector.

Run with:  python -m pytest tests/test_bkt_extended.py -v
"""

import math
import random
import pytest

from backend.app.engine.bkt_params import SkillParams, SkillState, AttemptResult
from backend.app.engine.bkt_core import (
    _posterior_correct,
    _posterior_incorrect,
    apply_learning_transition,
    select_difficulty,
    update_mastery,
    THRESHOLD_LOW_MID,
    THRESHOLD_MID_HIGH,
)
from backend.app.engine.content_selector import (
    select_difficulty_from_mastery,
    select_item,
    DEFAULT_HISTORY_SIZE,
)
from backend.app.engine.selector_types import PuzzleItem


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────

@pytest.fixture
def default_params() -> SkillParams:
    return SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.25, p_slip=0.10)


@pytest.fixture
def high_guess_params() -> SkillParams:
    """Edge: very high guessing probability."""
    return SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.90, p_slip=0.10)


@pytest.fixture
def high_slip_params() -> SkillParams:
    """Edge: very high slip probability."""
    return SkillParams(p_init=0.50, p_learn=0.20, p_guess=0.25, p_slip=0.90)


@pytest.fixture
def full_catalog() -> list[PuzzleItem]:
    """Catalog with 3 tiers × 3 items for all 3 skills = 27 items."""
    items = []
    for skill in ("vocabulary", "grammar", "listening"):
        for tier in ("low", "mid", "high"):
            for i in range(3):
                items.append(
                    PuzzleItem(
                        item_id=f"{skill}_{tier}_{i}",
                        puzzle_id=f"p_{skill}_{tier}",
                        skill=skill,
                        difficulty=tier,
                        weight=1.0,
                    )
                )
    return items


# ══════════════════════════════════════
# 1. BKT UPDATE — CONVERGENCE & STABILITY
# ══════════════════════════════════════

class TestBKTConvergence:
    """Verify long-run convergence properties of the BKT update cycle."""

    def test_all_correct_converges_to_one(self, default_params: SkillParams) -> None:
        """100 consecutive correct answers → mastery ≈ 1.0"""
        state = SkillState.from_params(default_params)
        for _ in range(100):
            update_mastery(state, default_params, is_correct=True)
        assert state.p_learned > 0.999

    def test_all_incorrect_stays_bounded(self, default_params: SkillParams) -> None:
        """100 consecutive wrong answers → mastery stays in [0, 1] and doesn't go negative."""
        state = SkillState.from_params(default_params)
        for _ in range(100):
            update_mastery(state, default_params, is_correct=False)
        assert 0.0 <= state.p_learned <= 1.0

    def test_all_incorrect_with_learning_transition(self, default_params: SkillParams) -> None:
        """
        Even with all wrong answers, learning transition P(T)=0.20 
        pushes mastery upward over time. After 100 wrongs mastery should 
        be notably higher than init due to the transition term.
        """
        state = SkillState.from_params(default_params)
        for _ in range(100):
            update_mastery(state, default_params, is_correct=False)
        # Learning transition dominates → mastery should climb despite all wrong
        assert state.p_learned > default_params.p_init

    def test_alternating_correct_incorrect(self, default_params: SkillParams) -> None:
        """
        Mixed signal: correct → incorrect → correct → incorrect …
        Should still converge but slower than all-correct.
        """
        state = SkillState.from_params(default_params)
        for i in range(100):
            update_mastery(state, default_params, is_correct=(i % 2 == 0))
        assert 0.0 <= state.p_learned <= 1.0
        # Should be moderately high (not near 0, not near 1)
        assert state.p_learned > 0.3

    def test_mastery_monotone_under_all_correct(self, default_params: SkillParams) -> None:
        """Mastery is strictly monotonically increasing under all-correct."""
        state = SkillState.from_params(default_params)
        prev = state.p_learned
        for _ in range(20):
            update_mastery(state, default_params, is_correct=True)
            assert state.p_learned > prev
            prev = state.p_learned


class TestBKTNumericalStability:
    """Verify the engine handles degenerate parameter values without crashing."""

    def test_zero_init_mastery(self) -> None:
        """P(L₀) = 0.0 — student starts knowing nothing."""
        params = SkillParams(p_init=0.0, p_learn=0.2, p_guess=0.25, p_slip=0.1)
        state = SkillState.from_params(params)
        result = update_mastery(state, params, is_correct=True)
        assert 0.0 <= result.p_learned_after <= 1.0

    def test_full_init_mastery(self) -> None:
        """P(L₀) = 1.0 — student starts fully mastered."""
        params = SkillParams(p_init=1.0, p_learn=0.2, p_guess=0.25, p_slip=0.1)
        state = SkillState.from_params(params)
        result = update_mastery(state, params, is_correct=False)
        assert 0.0 <= result.p_learned_after <= 1.0

    def test_zero_learn_rate(self) -> None:
        """P(T) = 0.0 — learning never happens via transition."""
        params = SkillParams(p_init=0.1, p_learn=0.0, p_guess=0.25, p_slip=0.1)
        state = SkillState.from_params(params)
        r1 = update_mastery(state, params, is_correct=True)
        # Without learning transition, posterior IS the new mastery
        assert math.isclose(r1.p_learned_after, r1.posterior_given_obs, rel_tol=1e-9)

    def test_perfect_guess_rate(self, high_guess_params: SkillParams) -> None:
        """P(G) = 0.90 — correct answers are mostly guessing."""
        state = SkillState.from_params(high_guess_params)
        r = update_mastery(state, high_guess_params, is_correct=True)
        # Correct answer is weak evidence → mastery should not jump much
        assert r.p_learned_after < 0.5

    def test_perfect_slip_rate(self, high_slip_params: SkillParams) -> None:
        """P(S) = 0.90 — wrong answers common even when learned."""
        state = SkillState.from_params(high_slip_params)
        r = update_mastery(state, high_slip_params, is_correct=False)
        # Wrong answer is weak evidence against knowledge
        assert 0.0 <= r.p_learned_after <= 1.0

    def test_zero_guess_zero_slip(self) -> None:
        """P(G)=0, P(S)=0 — deterministic model."""
        params = SkillParams(p_init=0.5, p_learn=0.2, p_guess=0.0, p_slip=0.0)
        state = SkillState.from_params(params)
        # Correct → proves knowledge → posterior = 1.0
        r = update_mastery(state, params, is_correct=True)
        assert math.isclose(r.posterior_given_obs, 1.0, rel_tol=1e-9)

    def test_all_params_at_boundary_zero(self) -> None:
        """All parameters = 0.0 — degenerate case should not crash."""
        params = SkillParams(p_init=0.0, p_learn=0.0, p_guess=0.0, p_slip=0.0)
        state = SkillState.from_params(params)
        r = update_mastery(state, params, is_correct=True)
        assert 0.0 <= r.p_learned_after <= 1.0

    def test_all_params_at_boundary_one(self) -> None:
        """All parameters = 1.0 — degenerate case should not crash."""
        params = SkillParams(p_init=1.0, p_learn=1.0, p_guess=1.0, p_slip=1.0)
        state = SkillState.from_params(params)
        r = update_mastery(state, params, is_correct=False)
        assert 0.0 <= r.p_learned_after <= 1.0


class TestBKTUpdateInvariant:
    """Mathematical invariants that must hold for every update."""

    @pytest.mark.parametrize("p_l", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    def test_posterior_correct_gte_incorrect(self, p_l: float) -> None:
        """For any prior, P(L|correct) ≥ P(L|incorrect)."""
        pc = _posterior_correct(p_l, 0.1, 0.25)
        pi = _posterior_incorrect(p_l, 0.1, 0.25)
        assert pc >= pi - 1e-12  # allow tiny floating-point slack

    @pytest.mark.parametrize("is_correct", [True, False])
    def test_update_preserves_probability_range(self, is_correct: bool) -> None:
        """After any single update, mastery ∈ [0, 1]."""
        params = SkillParams(p_init=0.5, p_learn=0.2, p_guess=0.25, p_slip=0.1)
        state = SkillState.from_params(params)
        update_mastery(state, params, is_correct=is_correct)
        assert 0.0 <= state.p_learned <= 1.0

    def test_learning_transition_never_decreases(self) -> None:
        """apply_learning_transition always returns ≥ input posterior."""
        for posterior in [0.0, 0.01, 0.1, 0.5, 0.9, 0.99, 1.0]:
            for p_t in [0.0, 0.1, 0.5, 1.0]:
                result = apply_learning_transition(posterior, p_t)
                assert result >= posterior - 1e-12


# ══════════════════════════════════════
# 2. ADAPTIVE DIFFICULTY — INTEGRATION
# ══════════════════════════════════════

class TestAdaptiveDifficultyIntegration:
    """Test that BKT update → difficulty selection → content selection form a coherent pipeline."""

    def test_low_mastery_selects_easy_items(
        self, default_params: SkillParams, full_catalog: list[PuzzleItem]
    ) -> None:
        """New student (mastery=0.1) should get low-tier puzzles."""
        state = SkillState.from_params(default_params)
        tier = select_difficulty(state.p_learned)
        assert tier == "low"
        result = select_item(full_catalog, "vocabulary", state.p_learned, rng=random.Random(42))
        assert result.selected.difficulty == "low"

    def test_mastery_progression_changes_difficulty(
        self, default_params: SkillParams, full_catalog: list[PuzzleItem]
    ) -> None:
        """After enough correct answers, difficulty should escalate from low → mid → high."""
        state = SkillState.from_params(default_params)
        tiers_seen = set()

        # Capture the initial tier BEFORE any updates
        tiers_seen.add(select_difficulty(state.p_learned))

        for _ in range(30):
            update_mastery(state, default_params, is_correct=True)
            tier = select_difficulty(state.p_learned)
            tiers_seen.add(tier)
            if tiers_seen == {"low", "mid", "high"}:
                break

        assert "low" in tiers_seen
        assert "mid" in tiers_seen
        assert "high" in tiers_seen

    def test_difficulty_tier_matches_selected_item(
        self, default_params: SkillParams, full_catalog: list[PuzzleItem]
    ) -> None:
        """The tier from select_difficulty matches the tier of the selected item."""
        state = SkillState.from_params(default_params)
        rng = random.Random(42)

        for _ in range(10):
            update_mastery(state, default_params, is_correct=True)
            expected_tier = select_difficulty(state.p_learned)
            result = select_item(
                full_catalog, "vocabulary", state.p_learned, recent_ids=[], rng=rng
            )
            # If no fallback used, tiers must match
            if not result.fallback_used:
                assert result.selected.difficulty == expected_tier

    def test_select_difficulty_and_mastery_consistency(self) -> None:
        """select_difficulty_from_mastery is a pure alias for select_difficulty."""
        for m in [0.0, 0.1, 0.39, 0.4, 0.5, 0.69, 0.7, 0.85, 1.0]:
            assert select_difficulty(m) == select_difficulty_from_mastery(m)


class TestAdaptiveDifficultyEdgeCases:
    """Threshold boundary and transition edge cases."""

    def test_mastery_just_below_low_mid(self) -> None:
        assert select_difficulty(0.3999999) == "low"

    def test_mastery_exactly_low_mid(self) -> None:
        assert select_difficulty(0.4) == "mid"

    def test_mastery_just_above_low_mid(self) -> None:
        assert select_difficulty(0.4000001) == "mid"

    def test_mastery_just_below_mid_high(self) -> None:
        assert select_difficulty(0.6999999) == "mid"

    def test_mastery_exactly_mid_high(self) -> None:
        assert select_difficulty(0.7) == "high"

    def test_mastery_just_above_mid_high(self) -> None:
        assert select_difficulty(0.7000001) == "high"

    def test_negative_mastery_treated_as_low(self) -> None:
        """Defensive: if mastery is somehow negative, should still return 'low'."""
        assert select_difficulty(-0.1) == "low"

    def test_mastery_above_one_treated_as_high(self) -> None:
        """Defensive: if mastery exceeds 1.0, should return 'high'."""
        assert select_difficulty(1.5) == "high"

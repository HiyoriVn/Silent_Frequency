"""
Silent Frequency — BKT Engine Unit Tests

Run with:  python -m pytest backend/app/engine/test_bkt.py -v
"""

import math
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


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────
@pytest.fixture
def default_params() -> SkillParams:
    return SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.25, p_slip=0.10)


@pytest.fixture
def default_state(default_params: SkillParams) -> SkillState:
    return SkillState.from_params(default_params)


# ──────────────────────────────────────
# 1. SkillParams validation
# ──────────────────────────────────────
class TestSkillParams:
    def test_valid_params(self) -> None:
        p = SkillParams(p_init=0.5, p_learn=0.3, p_guess=0.2, p_slip=0.1)
        assert p.p_init == 0.5

    def test_boundary_zero(self) -> None:
        p = SkillParams(p_init=0.0, p_learn=0.0, p_guess=0.0, p_slip=0.0)
        assert p.p_init == 0.0

    def test_boundary_one(self) -> None:
        p = SkillParams(p_init=1.0, p_learn=1.0, p_guess=1.0, p_slip=1.0)
        assert p.p_init == 1.0

    def test_reject_negative(self) -> None:
        with pytest.raises(ValueError, match="p_init"):
            SkillParams(p_init=-0.1, p_learn=0.2, p_guess=0.25, p_slip=0.1)

    def test_reject_over_one(self) -> None:
        with pytest.raises(ValueError, match="p_slip"):
            SkillParams(p_init=0.1, p_learn=0.2, p_guess=0.25, p_slip=1.1)

    def test_immutable(self) -> None:
        p = SkillParams(p_init=0.1, p_learn=0.2, p_guess=0.25, p_slip=0.1)
        with pytest.raises(AttributeError):
            p.p_init = 0.5  # type: ignore[misc]


# ──────────────────────────────────────
# 2. SkillState
# ──────────────────────────────────────
class TestSkillState:
    def test_from_params(self, default_params: SkillParams) -> None:
        state = SkillState.from_params(default_params)
        assert state.p_learned == default_params.p_init
        assert state.update_count == 0

    def test_mutable(self) -> None:
        state = SkillState(p_learned=0.5)
        state.p_learned = 0.7
        assert state.p_learned == 0.7


# ──────────────────────────────────────
# 3. Posterior update — correct answer
# ──────────────────────────────────────
class TestPosteriorCorrect:
    def test_basic(self) -> None:
        """P(L|correct) with P(L)=0.1, P(S)=0.1, P(G)=0.25"""
        result = _posterior_correct(0.10, 0.10, 0.25)
        # numerator = 0.1 * 0.9 = 0.09
        # denominator = 0.09 + 0.9 * 0.25 = 0.09 + 0.225 = 0.315
        # expected = 0.09 / 0.315 ≈ 0.285714
        assert math.isclose(result, 0.09 / 0.315, rel_tol=1e-9)

    def test_high_mastery(self) -> None:
        """When already mastered, correct answer keeps mastery high."""
        result = _posterior_correct(0.95, 0.10, 0.25)
        assert result > 0.95

    def test_zero_mastery(self) -> None:
        """P(L)=0 → entirely attributed to guessing → posterior stays 0."""
        result = _posterior_correct(0.0, 0.10, 0.25)
        assert result == 0.0

    def test_no_guessing(self) -> None:
        """P(G)=0 → correct answer PROVES knowledge → posterior = 1.0"""
        result = _posterior_correct(0.10, 0.10, 0.0)
        assert math.isclose(result, 1.0, rel_tol=1e-9)


# ──────────────────────────────────────
# 4. Posterior update — incorrect answer
# ──────────────────────────────────────
class TestPosteriorIncorrect:
    def test_basic(self) -> None:
        """P(L|incorrect) with P(L)=0.1, P(S)=0.1, P(G)=0.25"""
        result = _posterior_incorrect(0.10, 0.10, 0.25)
        # numerator = 0.1 * 0.1 = 0.01
        # denominator = 0.01 + 0.9 * 0.75 = 0.01 + 0.675 = 0.685
        # expected = 0.01 / 0.685 ≈ 0.014599
        assert math.isclose(result, 0.01 / 0.685, rel_tol=1e-9)

    def test_high_mastery(self) -> None:
        """Even with high mastery, wrong answer reduces estimate."""
        result = _posterior_incorrect(0.95, 0.10, 0.25)
        assert result < 0.95

    def test_no_slip(self) -> None:
        """P(S)=0 → wrong answer PROVES no knowledge → posterior = 0.0"""
        result = _posterior_incorrect(0.50, 0.0, 0.25)
        assert result == 0.0


# ──────────────────────────────────────
# 5. Learning transition
# ──────────────────────────────────────
class TestLearningTransition:
    def test_basic(self) -> None:
        """P(Lₙ₊₁) = posterior + (1 − posterior) · P(T)"""
        result = apply_learning_transition(0.3, 0.2)
        expected = 0.3 + 0.7 * 0.2  # 0.44
        assert math.isclose(result, expected, rel_tol=1e-9)

    def test_already_mastered(self) -> None:
        """posterior=1.0 → transition has no effect."""
        result = apply_learning_transition(1.0, 0.2)
        assert math.isclose(result, 1.0, rel_tol=1e-9)

    def test_zero_learn_rate(self) -> None:
        """P(T)=0 → no learning ever happens."""
        result = apply_learning_transition(0.3, 0.0)
        assert math.isclose(result, 0.3, rel_tol=1e-9)

    def test_never_decreases(self) -> None:
        """Transition can only increase or maintain mastery."""
        for posterior in [0.0, 0.1, 0.5, 0.9, 1.0]:
            result = apply_learning_transition(posterior, 0.2)
            assert result >= posterior


# ──────────────────────────────────────
# 6. Difficulty selection
# ──────────────────────────────────────
class TestDifficultySelection:
    def test_low(self) -> None:
        assert select_difficulty(0.0) == "low"
        assert select_difficulty(0.39) == "low"

    def test_mid(self) -> None:
        assert select_difficulty(0.4) == "mid"
        assert select_difficulty(0.69) == "mid"

    def test_high(self) -> None:
        assert select_difficulty(0.7) == "high"
        assert select_difficulty(1.0) == "high"

    def test_exact_boundaries(self) -> None:
        assert select_difficulty(THRESHOLD_LOW_MID) == "mid"
        assert select_difficulty(THRESHOLD_MID_HIGH) == "high"


# ──────────────────────────────────────
# 7. Full update_mastery cycle
# ──────────────────────────────────────
class TestUpdateMastery:
    def test_correct_increases_mastery(
        self, default_state: SkillState, default_params: SkillParams
    ) -> None:
        before = default_state.p_learned
        result = update_mastery(default_state, default_params, is_correct=True)
        assert result.p_learned_after > before
        assert result.is_correct is True
        assert default_state.p_learned == result.p_learned_after
        assert default_state.update_count == 1

    def test_incorrect_still_may_increase(
        self, default_state: SkillState, default_params: SkillParams
    ) -> None:
        """Even wrong answers trigger learning transition, so mastery may still rise."""
        before = default_state.p_learned
        result = update_mastery(default_state, default_params, is_correct=False)
        # With P(T)=0.2, the transition should push mastery up even after a wrong answer
        assert result.p_learned_after >= result.posterior_given_obs
        assert result.is_correct is False
        assert default_state.update_count == 1

    def test_three_correct_in_sequence(
        self, default_params: SkillParams
    ) -> None:
        """Simulate 3 correct answers — mastery should climb steadily."""
        state = SkillState.from_params(default_params)
        values = [state.p_learned]

        for _ in range(3):
            update_mastery(state, default_params, is_correct=True)
            values.append(state.p_learned)

        # Strictly increasing
        for i in range(1, len(values)):
            assert values[i] > values[i - 1], f"Mastery did not increase at step {i}"

        assert state.update_count == 3

    def test_three_incorrect_in_sequence(
        self, default_params: SkillParams
    ) -> None:
        """Even 3 wrong answers don't crash and mastery stays in [0, 1]."""
        state = SkillState.from_params(default_params)

        for _ in range(3):
            update_mastery(state, default_params, is_correct=False)

        assert 0.0 <= state.p_learned <= 1.0
        assert state.update_count == 3

    def test_result_contains_before_and_after(
        self, default_state: SkillState, default_params: SkillParams
    ) -> None:
        result = update_mastery(default_state, default_params, is_correct=True)
        assert result.p_learned_before == default_params.p_init
        assert isinstance(result.recommended_tier, str)
        assert result.recommended_tier in ("low", "mid", "high")

    def test_mastery_bounded_after_many_updates(
        self, default_params: SkillParams
    ) -> None:
        """After 50 correct answers mastery should be near 1.0 but never exceed it."""
        state = SkillState.from_params(default_params)
        for _ in range(50):
            update_mastery(state, default_params, is_correct=True)
        assert 0.0 <= state.p_learned <= 1.0
        assert state.p_learned > 0.99


# ──────────────────────────────────────
# 8. Mathematical consistency checks
# ──────────────────────────────────────
class TestMathConsistency:
    def test_correct_posterior_higher_than_incorrect(self) -> None:
        """For same prior, correct answer should yield higher posterior than incorrect."""
        p_l, p_s, p_g = 0.3, 0.1, 0.25
        post_correct = _posterior_correct(p_l, p_s, p_g)
        post_incorrect = _posterior_incorrect(p_l, p_s, p_g)
        assert post_correct > post_incorrect

    def test_posterior_between_0_and_1(self) -> None:
        """Posterior should always be a valid probability."""
        for p_l in [0.0, 0.1, 0.5, 0.9, 1.0]:
            for p_s in [0.0, 0.1, 0.3]:
                for p_g in [0.0, 0.1, 0.3]:
                    pc = _posterior_correct(p_l, p_s, p_g)
                    pi = _posterior_incorrect(p_l, p_s, p_g)
                    assert 0.0 <= pc <= 1.0, f"posterior_correct out of range: {pc}"
                    assert 0.0 <= pi <= 1.0, f"posterior_incorrect out of range: {pi}"

    def test_symmetry_when_guess_equals_slip(self) -> None:
        """When P(G) = P(S), the model treats correct/incorrect evidence symmetrically
        around the prior — but correct should still yield higher posterior."""
        p_l = 0.5
        p_s = p_g = 0.2
        pc = _posterior_correct(p_l, p_s, p_g)
        pi = _posterior_incorrect(p_l, p_s, p_g)
        # correct evidence should push UP, incorrect should push DOWN
        assert pc > p_l
        assert pi < p_l

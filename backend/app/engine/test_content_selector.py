"""
Silent Frequency — Content Selector Unit Tests

Run with:  python -m pytest backend/app/engine/test_content_selector.py -v
"""

import random
import pytest

from backend.app.engine.selector_types import PuzzleItem, SelectionResult
from backend.app.engine.content_selector import (
    select_difficulty_from_mastery,
    select_item,
    DEFAULT_HISTORY_SIZE,
    _weighted_choice,
    _update_history,
)


# ──────────────────────────────────────
# Fixtures — small item catalog
# ──────────────────────────────────────

def _make_catalog() -> list[PuzzleItem]:
    """Create a minimal catalog: 3 tiers × 2 items for vocabulary, 1 each for grammar."""
    return [
        # vocabulary — low
        PuzzleItem("v_low_1", "p1", "vocabulary", "low", weight=1.0),
        PuzzleItem("v_low_2", "p1", "vocabulary", "low", weight=1.0),
        # vocabulary — mid
        PuzzleItem("v_mid_1", "p2", "vocabulary", "mid", weight=1.0),
        PuzzleItem("v_mid_2", "p2", "vocabulary", "mid", weight=2.0),  # higher weight
        # vocabulary — high
        PuzzleItem("v_high_1", "p3", "vocabulary", "high", weight=1.0),
        PuzzleItem("v_high_2", "p3", "vocabulary", "high", weight=1.0),
        # grammar — one per tier
        PuzzleItem("g_low_1", "p4", "grammar", "low", weight=1.0),
        PuzzleItem("g_mid_1", "p5", "grammar", "mid", weight=1.0),
        PuzzleItem("g_high_1", "p6", "grammar", "high", weight=1.0),
    ]


@pytest.fixture
def catalog() -> list[PuzzleItem]:
    return _make_catalog()


@pytest.fixture
def seeded_rng() -> random.Random:
    return random.Random(42)


# ──────────────────────────────────────
# 1. select_difficulty_from_mastery()
# ──────────────────────────────────────
class TestSelectDifficulty:
    def test_low_range(self) -> None:
        assert select_difficulty_from_mastery(0.0) == "low"
        assert select_difficulty_from_mastery(0.1) == "low"
        assert select_difficulty_from_mastery(0.39) == "low"

    def test_mid_range(self) -> None:
        assert select_difficulty_from_mastery(0.4) == "mid"
        assert select_difficulty_from_mastery(0.5) == "mid"
        assert select_difficulty_from_mastery(0.69) == "mid"

    def test_high_range(self) -> None:
        assert select_difficulty_from_mastery(0.7) == "high"
        assert select_difficulty_from_mastery(0.85) == "high"
        assert select_difficulty_from_mastery(1.0) == "high"


# ──────────────────────────────────────
# 2. select_item() — basic selection
# ──────────────────────────────────────
class TestSelectItemBasic:
    def test_selects_correct_skill(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.3, rng=seeded_rng)
        assert result.selected.skill == "vocabulary"

    def test_selects_correct_tier_low(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.2, rng=seeded_rng)
        assert result.tier_used == "low"
        assert result.selected.difficulty == "low"

    def test_selects_correct_tier_mid(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.5, rng=seeded_rng)
        assert result.tier_used == "mid"
        assert result.selected.difficulty == "mid"

    def test_selects_correct_tier_high(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.8, rng=seeded_rng)
        assert result.tier_used == "high"
        assert result.selected.difficulty == "high"

    def test_returns_selection_result(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "grammar", mastery=0.5, rng=seeded_rng)
        assert isinstance(result, SelectionResult)
        assert result.pool_size >= 1
        assert result.fallback_used is False


# ──────────────────────────────────────
# 3. Repetition prevention
# ──────────────────────────────────────
class TestRepetitionPrevention:
    def test_excludes_recent_ids(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        """Block one of two low-vocab items → must pick the other."""
        recent: list[str] = ["v_low_1"]
        result = select_item(
            catalog, "vocabulary", mastery=0.2, recent_ids=recent, rng=seeded_rng
        )
        assert result.selected.item_id == "v_low_2"

    def test_no_immediate_repeat_in_sequence(
        self, catalog: list[PuzzleItem]
    ) -> None:
        """Run 10 selections — no two consecutive selections should be the same item."""
        rng = random.Random(123)
        recent: list[str] = []
        prev_id = None

        for _ in range(10):
            result = select_item(
                catalog, "vocabulary", mastery=0.2, recent_ids=recent, rng=rng
            )
            assert result.selected.item_id != prev_id, (
                f"Immediate repeat: {result.selected.item_id}"
            )
            prev_id = result.selected.item_id

    def test_history_is_trimmed(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        recent: list[str] = []
        for _ in range(DEFAULT_HISTORY_SIZE + 3):
            select_item(
                catalog, "vocabulary", mastery=0.2, recent_ids=recent, rng=seeded_rng
            )
        assert len(recent) <= DEFAULT_HISTORY_SIZE


# ──────────────────────────────────────
# 4. Fallback tiers
# ──────────────────────────────────────
class TestFallback:
    def test_fallback_when_tier_exhausted(self) -> None:
        """Catalog has only 'low' items for grammar → selecting at mid should fallback."""
        catalog = [
            PuzzleItem("g_low_only", "p1", "grammar", "low"),
        ]
        rng = random.Random(42)
        result = select_item(catalog, "grammar", mastery=0.5, rng=rng)

        assert result.selected.item_id == "g_low_only"
        assert result.fallback_used is True
        assert result.tier_used == "low"

    def test_fallback_when_all_blocked_by_history(self) -> None:
        """Only 1 item exists and it's in recent_ids → history resets and re-selects."""
        catalog = [
            PuzzleItem("only_one", "p1", "grammar", "mid"),
        ]
        rng = random.Random(42)
        recent: list[str] = ["only_one"]
        result = select_item(catalog, "grammar", mastery=0.5, recent_ids=recent, rng=rng)

        # Should still succeed — history was cleared to break the deadlock
        assert result.selected.item_id == "only_one"
        # History should now contain just this item (was cleared then re-added)
        assert recent == ["only_one"]


# ──────────────────────────────────────
# 5. Weighted selection
# ──────────────────────────────────────
class TestWeightedSelection:
    def test_higher_weight_selected_more_often(self) -> None:
        """v_mid_2 has weight=2.0 vs v_mid_1 at weight=1.0 → should appear ~2× more."""
        catalog = _make_catalog()
        rng = random.Random(99)
        counts: dict[str, int] = {"v_mid_1": 0, "v_mid_2": 0}

        for _ in range(300):
            result = select_item(
                catalog, "vocabulary", mastery=0.5, recent_ids=[], rng=rng
            )
            if result.selected.item_id in counts:
                counts[result.selected.item_id] += 1

        # With weight ratio 2:1, expect v_mid_2 to get roughly 200 out of 300
        # Allow wide tolerance for randomness: at least 1.3× more
        assert counts["v_mid_2"] > counts["v_mid_1"] * 1.3, (
            f"Expected v_mid_2 to dominate, got {counts}"
        )

    def test_zero_weight_items_can_still_be_selected(self) -> None:
        """If all items have weight=0, falls back to uniform random."""
        catalog = [
            PuzzleItem("z1", "p1", "vocabulary", "low", weight=0.0),
            PuzzleItem("z2", "p2", "vocabulary", "low", weight=0.0),
        ]
        rng = random.Random(42)
        result = select_item(catalog, "vocabulary", mastery=0.2, rng=rng)
        assert result.selected.item_id in ("z1", "z2")


# ──────────────────────────────────────
# 6. Edge cases
# ──────────────────────────────────────
class TestEdgeCases:
    def test_empty_catalog_raises(self) -> None:
        with pytest.raises(ValueError, match="No items in catalog"):
            select_item([], "vocabulary", mastery=0.5)

    def test_no_items_for_skill_raises(self, catalog: list[PuzzleItem]) -> None:
        with pytest.raises(ValueError, match="No items in catalog for skill 'listening'"):
            select_item(catalog, "listening", mastery=0.5)

    def test_mastery_zero(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.0, rng=seeded_rng)
        assert result.tier_used == "low"

    def test_mastery_one(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=1.0, rng=seeded_rng)
        assert result.tier_used == "high"

    def test_mastery_exact_threshold_low_mid(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.4, rng=seeded_rng)
        assert result.tier_used == "mid"

    def test_mastery_exact_threshold_mid_high(
        self, catalog: list[PuzzleItem], seeded_rng: random.Random
    ) -> None:
        result = select_item(catalog, "vocabulary", mastery=0.7, rng=seeded_rng)
        assert result.tier_used == "high"

    def test_single_item_pool(self) -> None:
        catalog = [PuzzleItem("solo", "p1", "vocabulary", "mid")]
        rng = random.Random(42)
        result = select_item(catalog, "vocabulary", mastery=0.5, rng=rng)
        assert result.selected.item_id == "solo"
        assert result.pool_size == 1


# ──────────────────────────────────────
# 7. Internal helpers
# ──────────────────────────────────────
class TestInternalHelpers:
    def test_update_history_appends(self) -> None:
        history: list[str] = ["a", "b"]
        _update_history(history, "c")
        assert history == ["a", "b", "c"]

    def test_update_history_trims(self) -> None:
        history: list[str] = list("abcde")  # exactly DEFAULT_HISTORY_SIZE
        _update_history(history, "f")
        assert len(history) == DEFAULT_HISTORY_SIZE
        assert history[0] == "b"  # oldest dropped
        assert history[-1] == "f"

    def test_weighted_choice_single_item(self) -> None:
        items = [PuzzleItem("x", "p", "vocabulary", "low")]
        rng = random.Random(42)
        assert _weighted_choice(items, rng).item_id == "x"

    def test_weighted_choice_respects_weights(self) -> None:
        items = [
            PuzzleItem("heavy", "p1", "vocabulary", "low", weight=100.0),
            PuzzleItem("light", "p2", "vocabulary", "low", weight=0.001),
        ]
        rng = random.Random(42)
        picks = [_weighted_choice(items, rng).item_id for _ in range(50)]
        # With 100:0.001 ratio, "heavy" should get essentially all picks
        assert picks.count("heavy") >= 48

    def test_negative_weight_rejected(self) -> None:
        with pytest.raises(ValueError, match="weight must be"):
            PuzzleItem("bad", "p", "vocabulary", "low", weight=-1.0)

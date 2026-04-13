"""
Silent Frequency — Puzzle Service

Handles:
  - Loading the puzzle catalog from DB
  - Selecting the next adaptive item (delegates to engine)
  - Scoring answers
  - Recording attempts + BKT updates
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db.models import Attempt, EventLog, GameSession, GameState, Puzzle, PuzzleVariant, Skill
from ..engine.bkt_core import select_difficulty, update_mastery

from . import mastery_service


LEVEL_SCRIPT: list[tuple[str, int]] = [
    ("vocabulary", 1),
    ("vocabulary", 2),
    ("vocabulary", 3),
    ("grammar", 1),
    ("grammar", 2),
    ("grammar", 3),
    ("listening", 1),
    ("listening", 2),
    ("listening", 3),
]

ROOM_ORDER = {
    "start_room": 0,
    "radio_room": 1,
    "lab_room": 2,
}

ROOM404_WARNING_SIGN_PUZZLE_ID = "p_warning_sign_translate"

ROOM404_CANONICAL_PUZZLE_BINDINGS: dict[str, dict[str, str | int]] = {
    ROOM404_WARNING_SIGN_PUZZLE_ID: {
        "skill": "vocabulary",
        "slot_order": 1,
        "difficulty_tier": "mid",
    }
}

ROOM404_WARNING_SIGN_ACCEPTED_ANSWERS = [
    "authorized personnel only",
    "authorized staff only",
    "chi nhan vien duoc phep",
    "chi nguoi duoc uy quyen",
]

_ADAPTIVE_TIER_ORDER = {"low", "mid", "high"}


def _extract_interaction_payload(variant: PuzzleVariant) -> dict | None:
    metadata = variant.metadata_ or {}
    interaction = metadata.get("interaction")
    if isinstance(interaction, dict):
        return interaction
    return None


def _derive_interaction_view(
    variant: PuzzleVariant | None,
) -> tuple[str, dict | None]:
    if variant is None:
        return "plain", None

    interaction = _extract_interaction_payload(variant)
    if interaction is None:
        return "plain", None
    return "scene_hotspot", interaction


def _level_info(level_index: int) -> tuple[str, int]:
    if level_index < 0 or level_index >= len(LEVEL_SCRIPT):
        raise ValueError(f"Invalid level index: {level_index}")
    return LEVEL_SCRIPT[level_index]


async def _resolve_level_puzzle(
    db: AsyncSession,
    skill_code: str,
    slot_order: int,
) -> Puzzle:
    """
    Resolve the level puzzle by deterministic skill progression order.

    For each skill, choose the slot_order-th puzzle in room progression:
    start_room -> radio_room -> lab_room.
    """
    room_rank = case(
        *[(Puzzle.room == room, rank) for room, rank in ROOM_ORDER.items()],
        else_=999,
    )

    result = await db.execute(
        select(Puzzle)
        .join(Skill, Puzzle.skill_id == Skill.id)
        .where(Skill.code == skill_code)
        .order_by(room_rank, Puzzle.id)
    )
    puzzles = result.scalars().all()

    target_index = slot_order - 1
    if target_index < 0 or target_index >= len(puzzles):
        raise ValueError(
            f"No puzzle found for skill={skill_code}, slot_order={slot_order}"
        )
    return puzzles[target_index]


async def _resolve_variant_for_tier(
    db: AsyncSession,
    puzzle_id: str,
    difficulty_tier: str,
) -> PuzzleVariant:
    result = await db.execute(
        select(PuzzleVariant)
        .where(
            PuzzleVariant.puzzle_id == puzzle_id,
            PuzzleVariant.difficulty_tier == difficulty_tier,
        )
    )
    variant = result.scalar_one_or_none()
    if variant is not None:
        return variant

    # Safe fallback for incomplete seed data.
    fallback_result = await db.execute(
        select(PuzzleVariant)
        .where(PuzzleVariant.puzzle_id == puzzle_id)
        .order_by(PuzzleVariant.id)
    )
    fallback = fallback_result.scalars().first()
    if fallback is None:
        raise ValueError(f"No variants found for puzzle_id={puzzle_id}")
    return fallback


async def _difficulty_for_level(
    db: AsyncSession,
    session: GameSession,
    skill_code: str,
    slot_order: int,
) -> str:
    # Slot 1 is always mid.
    if slot_order == 1:
        return "mid"

    # Static condition is always mid.
    if session.condition == "static":
        return "mid"

    # Adaptive condition follows BKT-driven tier.
    estimate = await mastery_service.get_skill_estimate(db, session.id, skill_code)
    if estimate is None:
        raise ValueError(f"No estimate for session={session.id}, skill={skill_code}")
    return select_difficulty(estimate.p_ln)


# ──────────────────────────────────────
# Next puzzle selection
# ──────────────────────────────────────

async def get_next_puzzle(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> dict:
    """
    Select the next puzzle from fixed 9-level progression.

    Returns a dict with variant details ready to be sent to the frontend.
    """
    session = await db.get(GameSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    if session.current_level_index >= len(LEVEL_SCRIPT):
        interaction_mode, interaction = _derive_interaction_view(None)
        return {
            "puzzle_id": "",
            "variant_id": "",
            "skill": "",
            "slot_order": 0,
            "difficulty_tier": "mid",
            "prompt_text": "",
            "audio_url": None,
            "time_limit_sec": None,
            "interaction_mode": interaction_mode,
            "interaction": interaction,
            "session_complete": True,
        }

    skill_code, slot_order = _level_info(session.current_level_index)
    puzzle = await _resolve_level_puzzle(db, skill_code, slot_order)
    difficulty_tier = await _difficulty_for_level(db, session, skill_code, slot_order)
    variant = await _resolve_variant_for_tier(db, puzzle.id, difficulty_tier)
    interaction_mode, interaction = _derive_interaction_view(variant)

    return {
        "puzzle_id": puzzle.id,
        "variant_id": variant.id,
        "skill": skill_code,
        "slot_order": slot_order,
        "difficulty_tier": variant.difficulty_tier,
        "prompt_text": variant.prompt_text,
        "audio_url": variant.audio_url,
        "time_limit_sec": variant.time_limit_sec,
        "interaction_mode": interaction_mode,
        "interaction": interaction,
        "session_complete": False,
    }


# ──────────────────────────────────────
# Answer scoring + BKT update
# ──────────────────────────────────────

def _score_answer(player_answer: str, correct_answers: list[str]) -> bool:
    """Case-insensitive, trimmed comparison against accepted answers."""
    normalised = player_answer.strip().lower()
    return any(normalised == ca.strip().lower() for ca in correct_answers)


def _merge_accepted_answers(base: list[str], extras: list[str]) -> list[str]:
    merged: list[str] = []
    for answer in [*base, *extras]:
        if answer not in merged:
            merged.append(answer)
    return merged


def _normalise_difficulty_tier(value: str | None) -> str:
    if value in _ADAPTIVE_TIER_ORDER:
        return value
    return "mid"


def _next_room404_difficulty_tier(current_tier: str, is_correct: bool) -> str:
    current = _normalise_difficulty_tier(current_tier)
    if is_correct:
        return current
    if current == "high":
        return "mid"
    if current == "mid":
        return "low"
    return "low"


async def _apply_room404_adaptive_update_after_attempt(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    canonical_puzzle_id: str,
    is_correct: bool,
    bump_version: bool,
) -> dict[str, str | int] | None:
    if canonical_puzzle_id != ROOM404_WARNING_SIGN_PUZZLE_ID:
        return None

    state = await db.get(GameState, session_id)
    if state is None:
        raise ValueError(f"Game state for session={session_id} not found")

    state_flags = copy.deepcopy(state.flags) if isinstance(state.flags, dict) else {}
    adaptive_state = state_flags.get("adaptive_state")
    if not isinstance(adaptive_state, dict):
        adaptive_state = {
            "difficulty_tier": "mid",
            "warm_start_source": "default",
        }

    before_tier = _normalise_difficulty_tier(str(adaptive_state.get("difficulty_tier")))
    after_tier = _next_room404_difficulty_tier(before_tier, is_correct)
    previous_count = adaptive_state.get("adaptive_update_count")
    if not isinstance(previous_count, int) or previous_count < 0:
        previous_count = 0

    adaptive_state["difficulty_tier"] = after_tier
    adaptive_state["last_attempt_outcome"] = "correct" if is_correct else "incorrect"
    adaptive_state["adaptive_update_count"] = previous_count + 1
    state_flags["adaptive_state"] = adaptive_state

    state.flags = state_flags
    if bump_version:
        state.game_state_version += 1
        state.updated_at = datetime.now(timezone.utc)

    return {
        "difficulty_tier_before": before_tier,
        "difficulty_tier_after": after_tier,
        "last_attempt_outcome": adaptive_state["last_attempt_outcome"],
        "adaptive_update_count": adaptive_state["adaptive_update_count"],
    }


async def _apply_room404_progression_on_success(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    canonical_puzzle_id: str,
    is_correct: bool,
) -> bool:
    if not is_correct:
        return False
    if canonical_puzzle_id != ROOM404_WARNING_SIGN_PUZZLE_ID:
        return False

    state = await db.get(GameState, session_id)
    if state is None:
        raise ValueError(f"Game state for session={session_id} not found")

    state_flags = copy.deepcopy(state.flags) if isinstance(state.flags, dict) else {}
    canonical_flags = state_flags.get("flags")
    if not isinstance(canonical_flags, dict):
        canonical_flags = {}

    canonical_flags["first_language_interaction_done"] = True
    canonical_flags["room404_exit_unlocked"] = True

    active_puzzles = state_flags.get("active_puzzles")
    if not isinstance(active_puzzles, list):
        active_puzzles = []
    active_puzzles = [p for p in active_puzzles if p != ROOM404_WARNING_SIGN_PUZZLE_ID]

    state_flags["flags"] = canonical_flags
    state_flags["active_puzzles"] = active_puzzles
    state.flags = state_flags
    state.game_state_version += 1
    state.updated_at = datetime.now(timezone.utc)

    return True


async def submit_attempt(
    db: AsyncSession,
    session_id: uuid.UUID,
    puzzle_id: str | None,
    variant_id: str,
    player_answer: str,
    response_time_ms: int,
    hint_count_used: int = 0,
    interaction_trace: list[dict] | None = None,
) -> dict:
    """
    Score answer → BKT update → log attempt → return feedback.

    Full pipeline for POST /api/sessions/{id}/attempts.
    """
    # 1. Load session first so gameplay_v2 can evaluate by canonical puzzle id.
    session = await db.get(GameSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    canonical_puzzle_id = puzzle_id

    # 2. Resolve variant by canonical puzzle id for gameplay_v2 when provided.
    if session.mode == "gameplay_v2" and puzzle_id is not None:
        binding = ROOM404_CANONICAL_PUZZLE_BINDINGS.get(puzzle_id)
        if binding is None:
            raise ValueError(f"Unsupported gameplay_v2 puzzle_id={puzzle_id}")

        puzzle = await _resolve_level_puzzle(
            db,
            str(binding["skill"]),
            int(binding["slot_order"]),
        )
        variant = await _resolve_variant_for_tier(
            db,
            puzzle.id,
            str(binding["difficulty_tier"]),
        )
    else:
        # Compatibility/default path: resolve directly from variant id.
        variant = await db.get(
            PuzzleVariant, variant_id, options=[joinedload(PuzzleVariant.puzzle)]
        )
        if variant is None:
            raise ValueError(f"Variant {variant_id} not found")

    puzzle = variant.puzzle
    if canonical_puzzle_id is None:
        canonical_puzzle_id = puzzle.id

    # 3. Load skill info
    skill = await db.get(Skill, puzzle.skill_id)
    if skill is None:
        raise ValueError(f"Skill {puzzle.skill_id} not found")

    # 4. Score the answer
    accepted_answers = variant.correct_answers
    if canonical_puzzle_id == ROOM404_WARNING_SIGN_PUZZLE_ID:
        accepted_answers = _merge_accepted_answers(
            variant.correct_answers,
            ROOM404_WARNING_SIGN_ACCEPTED_ANSWERS,
        )
    is_correct = _score_answer(player_answer, accepted_answers)

    # 5. Load BKT estimate
    estimate = await mastery_service.get_skill_estimate(db, session_id, skill.code)
    if estimate is None:
        raise ValueError(f"No estimate for session={session_id}, skill={skill.code}")

    # 6. Run BKT update via engine
    state, params = mastery_service.estimate_to_engine_objects(estimate)
    bkt_result = update_mastery(state, params, is_correct)

    # 7. Write updated estimate back to DB
    estimate.p_ln = state.p_learned
    estimate.update_count = state.update_count
    estimate.updated_at = datetime.now(timezone.utc)

    # 8. Count previous attempts on this puzzle in this session
    count_result = await db.execute(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.session_id == session_id,
            Attempt.puzzle_id == puzzle.id,
        )
    )
    attempt_number = (count_result.scalar() or 0) + 1

    # 9. Log the attempt
    attempt = Attempt(
        session_id=session_id,
        puzzle_id=puzzle.id,
        variant_id=variant.id,
        skill_id=skill.id,
        player_answer=player_answer,
        is_correct=is_correct,
        response_time_ms=response_time_ms,
        p_ln_before=bkt_result.p_learned_before,
        p_ln_after=bkt_result.p_learned_after,
        difficulty_tier=variant.difficulty_tier,
        hint_count_used=hint_count_used,
        attempt_number=attempt_number,
    )
    db.add(attempt)

    # 10. Log event
    db.add(EventLog(
        session_id=session_id,
        event_type="attempt_submitted",
        payload={
            "canonical_puzzle_id": canonical_puzzle_id,
            "puzzle_id": puzzle.id,
            "variant_id": variant.id,
            "skill": skill.code,
            "is_correct": is_correct,
            "p_ln_before": bkt_result.p_learned_before,
            "p_ln_after": bkt_result.p_learned_after,
            "response_time_ms": response_time_ms,
        },
    ))

    # Optional telemetry-only trace logging. This must not affect scoring,
    # BKT updates, progression, or completion decisions.
    if interaction_trace is not None:
        db.add(EventLog(
            session_id=session_id,
            event_type="puzzle_interaction_trace",
            payload={
                "version": 1,
                "type": "interaction_trace",
                "canonical_puzzle_id": canonical_puzzle_id,
                "puzzle_id": puzzle.id,
                "variant_id": variant.id,
                "skill": skill.code,
                "trace": interaction_trace,
                "response_time_ms": response_time_ms,
            },
        ))

    # 11. Advance session progression index
    session.current_level_index += 1
    session_complete = session.current_level_index >= len(LEVEL_SCRIPT)
    if session_complete:
        session.status = "completed"
        session.finished_at = datetime.now(timezone.utc)

    db.add(EventLog(
        session_id=session_id,
        event_type="session_progressed",
        payload={
            "current_level_index": session.current_level_index,
            "session_complete": session_complete,
        },
    ))

    progression_applied = await _apply_room404_progression_on_success(
        db,
        session_id=session_id,
        canonical_puzzle_id=canonical_puzzle_id,
        is_correct=is_correct,
    )
    if progression_applied:
        db.add(EventLog(
            session_id=session_id,
            event_type="room404_progression_applied",
            payload={
                "puzzle_id": canonical_puzzle_id,
                "first_language_interaction_done": True,
                "room404_exit_unlocked": True,
                "active_puzzles_cleared": True,
            },
        ))

    adaptive_update = await _apply_room404_adaptive_update_after_attempt(
        db,
        session_id=session_id,
        canonical_puzzle_id=canonical_puzzle_id,
        is_correct=is_correct,
        bump_version=not progression_applied,
    )
    if adaptive_update is not None:
        db.add(EventLog(
            session_id=session_id,
            event_type="room404_adaptive_state_updated",
            payload={
                "puzzle_id": canonical_puzzle_id,
                "is_correct": is_correct,
                "difficulty_tier_before": adaptive_update["difficulty_tier_before"],
                "difficulty_tier_after": adaptive_update["difficulty_tier_after"],
                "last_attempt_outcome": adaptive_update["last_attempt_outcome"],
                "adaptive_update_count": adaptive_update["adaptive_update_count"],
            },
        ))

    await db.commit()

    # 12. Get full mastery snapshot for response
    mastery_snap = await mastery_service.get_mastery_snapshot(db, session_id)

    return {
        "puzzle_id": canonical_puzzle_id,
        "is_correct": is_correct,
        "correct_answers": accepted_answers,
        "p_learned_before": bkt_result.p_learned_before,
        "p_learned_after": bkt_result.p_learned_after,
        "difficulty_tier": bkt_result.recommended_tier,
        "current_level_index": session.current_level_index,
        "session_complete": session_complete,
        "mastery": mastery_snap,
    }

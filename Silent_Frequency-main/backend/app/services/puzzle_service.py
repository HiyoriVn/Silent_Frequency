"""
Silent Frequency — Puzzle Service

Handles:
  - Loading the puzzle catalog from DB
  - Selecting the next adaptive item (delegates to engine)
  - Scoring answers
  - Recording attempts + BKT updates
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db.models import Attempt, EventLog, GameSession, Puzzle, PuzzleVariant, Skill
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
        return {
            "puzzle_id": "",
            "variant_id": "",
            "skill": "",
            "slot_order": 0,
            "difficulty_tier": "mid",
            "prompt_text": "",
            "audio_url": None,
            "time_limit_sec": None,
            "session_complete": True,
        }

    skill_code, slot_order = _level_info(session.current_level_index)
    puzzle = await _resolve_level_puzzle(db, skill_code, slot_order)
    difficulty_tier = await _difficulty_for_level(db, session, skill_code, slot_order)
    variant = await _resolve_variant_for_tier(db, puzzle.id, difficulty_tier)

    return {
        "puzzle_id": puzzle.id,
        "variant_id": variant.id,
        "skill": skill_code,
        "slot_order": slot_order,
        "difficulty_tier": variant.difficulty_tier,
        "prompt_text": variant.prompt_text,
        "audio_url": variant.audio_url,
        "time_limit_sec": variant.time_limit_sec,
        "session_complete": False,
    }


# ──────────────────────────────────────
# Answer scoring + BKT update
# ──────────────────────────────────────

def _score_answer(player_answer: str, correct_answers: list[str]) -> bool:
    """Case-insensitive, trimmed comparison against accepted answers."""
    normalised = player_answer.strip().lower()
    return any(normalised == ca.strip().lower() for ca in correct_answers)


async def submit_attempt(
    db: AsyncSession,
    session_id: uuid.UUID,
    variant_id: str,
    player_answer: str,
    response_time_ms: int,
    hint_count_used: int = 0,
) -> dict:
    """
    Score answer → BKT update → log attempt → return feedback.

    Full pipeline for POST /api/sessions/{id}/attempts.
    """
    # 1. Load the variant + parent puzzle
    variant = await db.get(
        PuzzleVariant, variant_id, options=[joinedload(PuzzleVariant.puzzle)]
    )
    if variant is None:
        raise ValueError(f"Variant {variant_id} not found")

    puzzle = variant.puzzle

    # 2. Load skill info
    skill = await db.get(Skill, puzzle.skill_id)
    if skill is None:
        raise ValueError(f"Skill {puzzle.skill_id} not found")

    # 3. Score the answer
    is_correct = _score_answer(player_answer, variant.correct_answers)

    # 4. Load BKT estimate
    estimate = await mastery_service.get_skill_estimate(db, session_id, skill.code)
    if estimate is None:
        raise ValueError(f"No estimate for session={session_id}, skill={skill.code}")

    # 5. Run BKT update via engine
    state, params = mastery_service.estimate_to_engine_objects(estimate)
    bkt_result = update_mastery(state, params, is_correct)

    # 6. Write updated estimate back to DB
    estimate.p_ln = state.p_learned
    estimate.update_count = state.update_count
    estimate.updated_at = datetime.now(timezone.utc)

    # 7. Count previous attempts on this puzzle in this session
    count_result = await db.execute(
        select(func.count())
        .select_from(Attempt)
        .where(
            Attempt.session_id == session_id,
            Attempt.puzzle_id == puzzle.id,
        )
    )
    attempt_number = (count_result.scalar() or 0) + 1

    # 8. Log the attempt
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

    # 9. Log event
    db.add(EventLog(
        session_id=session_id,
        event_type="attempt_submitted",
        payload={
            "puzzle_id": puzzle.id,
            "variant_id": variant.id,
            "skill": skill.code,
            "is_correct": is_correct,
            "p_ln_before": bkt_result.p_learned_before,
            "p_ln_after": bkt_result.p_learned_after,
            "response_time_ms": response_time_ms,
        },
    ))

    # 10. Advance session progression index
    session = await db.get(GameSession, session_id)
    if session is None:
        raise ValueError(f"Session {session_id} not found")

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

    await db.commit()

    # 11. Get full mastery snapshot for response
    mastery_snap = await mastery_service.get_mastery_snapshot(db, session_id)

    return {
        "is_correct": is_correct,
        "correct_answers": variant.correct_answers,
        "p_learned_before": bkt_result.p_learned_before,
        "p_learned_after": bkt_result.p_learned_after,
        "difficulty_tier": bkt_result.recommended_tier,
        "current_level_index": session.current_level_index,
        "session_complete": session_complete,
        "mastery": mastery_snap,
    }

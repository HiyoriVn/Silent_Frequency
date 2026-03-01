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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db.models import Attempt, EventLog, Puzzle, PuzzleVariant, Skill, SkillEstimate
from ..engine.bkt_core import update_mastery
from ..engine.content_selector import select_item
from ..engine.selector_types import PuzzleItem

from . import mastery_service


# ──────────────────────────────────────
# Catalog loading
# ──────────────────────────────────────

async def load_catalog(db: AsyncSession) -> list[PuzzleItem]:
    """
    Load all puzzle variants from DB and convert to engine PuzzleItem list.

    This is the bridge between the relational model and the stateless
    content selector engine.
    """
    result = await db.execute(
        select(PuzzleVariant)
        .options(joinedload(PuzzleVariant.puzzle).joinedload(Puzzle.skill))
    )
    rows = result.scalars().all()

    return [
        PuzzleItem(
            item_id=v.id,
            puzzle_id=v.puzzle_id,
            skill=v.puzzle.skill.code,
            difficulty=v.difficulty_tier,  # type: ignore[arg-type]
            weight=1.0,
        )
        for v in rows
    ]


# ──────────────────────────────────────
# Next-item selection
# ──────────────────────────────────────

async def get_next_item(
    db: AsyncSession,
    session_id: uuid.UUID,
    skill_code: str,
    recent_ids: list[str] | None = None,
) -> dict:
    """
    Select the next puzzle variant adaptively.

    Returns a dict with variant details ready to be sent to the frontend.
    """
    # 1. Load current mastery for the skill
    estimate = await mastery_service.get_skill_estimate(db, session_id, skill_code)
    if estimate is None:
        raise ValueError(f"No skill estimate found for session={session_id}, skill={skill_code}")

    # 2. Load full catalog
    catalog = await load_catalog(db)

    # 3. Run content selector engine
    selection = select_item(
        catalog=catalog,
        skill=skill_code,
        mastery=estimate.p_ln,
        recent_ids=recent_ids if recent_ids is not None else [],
    )

    # 4. Fetch variant details from DB
    variant = await db.get(PuzzleVariant, selection.selected.item_id)
    if variant is None:
        raise ValueError(f"Variant {selection.selected.item_id} not found in DB")

    return {
        "puzzle_id": variant.puzzle_id,
        "variant_id": variant.id,
        "skill": skill_code,
        "difficulty_tier": variant.difficulty_tier,
        "prompt_text": variant.prompt_text,
        "audio_url": variant.audio_url,
        "time_limit_sec": variant.time_limit_sec,
        "fallback_used": selection.fallback_used,
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

    await db.commit()

    # 10. Get full mastery snapshot for response
    mastery_snap = await mastery_service.get_mastery_snapshot(db, session_id)

    return {
        "is_correct": is_correct,
        "correct_answers": variant.correct_answers,
        "p_learned_before": bkt_result.p_learned_before,
        "p_learned_after": bkt_result.p_learned_after,
        "difficulty_tier": bkt_result.recommended_tier,
        "mastery": mastery_snap,
    }

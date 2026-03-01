"""
Silent Frequency — Mastery Service

Reads BKT state from DB, delegates math to the engine, writes back.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..db.models import SkillEstimate, Skill
from ..engine.bkt_core import select_difficulty
from ..engine.bkt_params import SkillParams, SkillState


async def get_mastery_for_session(
    db: AsyncSession, session_id: uuid.UUID
) -> list[dict]:
    """
    Return mastery state for all skills in a session.

    Returns list of dicts:
        [{"skill": "vocabulary", "p_learned": 0.32, "update_count": 3,
          "difficulty_tier": "low"}, ...]
    """
    result = await db.execute(
        select(SkillEstimate)
        .options(joinedload(SkillEstimate.skill))
        .where(SkillEstimate.session_id == session_id)
        .order_by(SkillEstimate.skill_id)
    )
    estimates = result.scalars().all()

    return [
        {
            "skill": est.skill.code,
            "p_learned": est.p_ln,
            "update_count": est.update_count,
            "difficulty_tier": select_difficulty(est.p_ln),
        }
        for est in estimates
    ]


async def get_mastery_snapshot(
    db: AsyncSession, session_id: uuid.UUID
) -> dict[str, float]:
    """
    Return {skill_code: p_ln} map — used for API response `mastery` field.
    """
    rows = await get_mastery_for_session(db, session_id)
    return {r["skill"]: r["p_learned"] for r in rows}


async def get_skill_estimate(
    db: AsyncSession, session_id: uuid.UUID, skill_code: str
) -> SkillEstimate | None:
    """Load a single SkillEstimate by session + skill code."""
    result = await db.execute(
        select(SkillEstimate)
        .join(Skill, SkillEstimate.skill_id == Skill.id)
        .where(
            SkillEstimate.session_id == session_id,
            Skill.code == skill_code,
        )
    )
    return result.scalar_one_or_none()


def estimate_to_engine_objects(
    est: SkillEstimate,
) -> tuple[SkillState, SkillParams]:
    """Convert a DB SkillEstimate row into engine-level dataclasses."""
    params = SkillParams(
        p_init=est.p_ln,   # not used during update, but required by dataclass
        p_learn=est.p_t,
        p_guess=est.p_g,
        p_slip=est.p_s,
    )
    state = SkillState(
        p_learned=est.p_ln,
        update_count=est.update_count,
    )
    return state, params

"""
Silent Frequency — Session Service

Handles session creation, player creation, and BKT state initialisation.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    GameSession,
    GameState,
    Player,
    Skill,
    SkillEstimate,
    EventLog,
)


async def create_session(db: AsyncSession, display_name: str) -> dict:
    """
    Create a new player + game session + initial BKT estimates + game state.

    Returns a dict ready to be wrapped in the API response.
    """
    # 1. Create player
    player = Player(
        display_name=display_name,
        session_token=secrets.token_urlsafe(48),
    )
    db.add(player)
    await db.flush()  # assigns player.id

    # 2. Create game session
    session = GameSession(
        player_id=player.id,
        current_room="start_room",
    )
    db.add(session)
    await db.flush()

    # 3. Load skill definitions and create initial BKT estimates
    result = await db.execute(select(Skill).order_by(Skill.id))
    skills = result.scalars().all()

    mastery = {}
    for skill in skills:
        estimate = SkillEstimate(
            session_id=session.id,
            skill_id=skill.id,
            p_ln=skill.bkt_p_l0,
            p_t=skill.bkt_p_t,
            p_g=skill.bkt_p_g,
            p_s=skill.bkt_p_s,
        )
        db.add(estimate)
        mastery[skill.code] = skill.bkt_p_l0

    # 4. Create initial game state
    game_state = GameState(session_id=session.id)
    db.add(game_state)

    # 5. Log session creation
    db.add(EventLog(
        session_id=session.id,
        event_type="session_created",
        payload={"display_name": display_name, "map_id": session.map_id},
    ))

    await db.commit()

    return {
        "session_id": session.id,
        "player_id": player.id,
        "session_token": player.session_token,
        "mastery": mastery,
        "current_room": session.current_room,
    }


async def get_session_or_none(
    db: AsyncSession, session_id: uuid.UUID
) -> GameSession | None:
    """Fetch a game session by ID, or None."""
    result = await db.execute(
        select(GameSession).where(GameSession.id == session_id)
    )
    return result.scalar_one_or_none()

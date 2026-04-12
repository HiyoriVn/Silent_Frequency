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


_ROOM404_DEFAULT_FLAGS = {
    "first_language_interaction_done": False,
    "bedside_note_collected": False,
    "room404_exit_unlocked": False,
}


def _initial_gameplay_flags(self_assessed_level: str | None) -> dict:
    flags = dict(_ROOM404_DEFAULT_FLAGS)
    if self_assessed_level is not None:
        flags["self_assessed_level"] = self_assessed_level

    return {
        "chapter_id": "chapter_1",
        "zone_id": "patient_room_404",
        "view_id": "patient_room_404__bg_01_bed_wall",
        "sub_view_id": None,
        "fsm_state": "room404_idle",
        "flags": flags,
        "journal_entries": [],
    }


async def create_session(
    db: AsyncSession,
    display_name: str,
    condition: str = "adaptive",
    mode: str = "phase3",
    self_assessed_level: str | None = None,
) -> dict:
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
        condition=condition,
        mode=mode,
        current_level_index=0,
        current_room="patient_room_404" if mode == "gameplay_v2" else "start_room",
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
    game_state_flags = (
        _initial_gameplay_flags(self_assessed_level)
        if mode == "gameplay_v2"
        else ({"self_assessed_level": self_assessed_level} if self_assessed_level else {})
    )
    game_state = GameState(
        session_id=session.id,
        flags=game_state_flags,
        inventory=[],
    )
    db.add(game_state)

    # 5. Log session creation
    db.add(EventLog(
        session_id=session.id,
        event_type="session_created",
        payload={
            "display_name": display_name,
            "map_id": session.map_id,
            "condition": session.condition,
            "mode": session.mode,
            "self_assessed_level": self_assessed_level,
            "current_level_index": session.current_level_index,
        },
    ))

    await db.commit()

    return {
        "session_id": session.id,
        "player_id": player.id,
        "session_token": player.session_token,
        "condition": session.condition,
        "mode": session.mode,
        "self_assessed_level": self_assessed_level,
        "current_level_index": session.current_level_index,
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

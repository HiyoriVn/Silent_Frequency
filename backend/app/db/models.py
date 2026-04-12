"""
Silent Frequency — SQLAlchemy ORM Models

Maps exactly to the approved database schema design.
All tables use the public schema.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from .database import Base


# ──────────────────────────────────────
# Helper
# ──────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────
# 1. players
# ──────────────────────────────────────
class Player(Base):
    __tablename__ = "players"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    session_token: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # relationships
    sessions: Mapped[list["GameSession"]] = relationship(back_populates="player")


# ──────────────────────────────────────
# 1b. user_accounts (minimal auth)
# ──────────────────────────────────────
class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    real_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    auth_token: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ──────────────────────────────────────
# 2. skills
# ──────────────────────────────────────
class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    bkt_p_l0: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)
    bkt_p_t: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    bkt_p_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.25)
    bkt_p_s: Mapped[float] = mapped_column(Float, nullable=False, default=0.1)


# ──────────────────────────────────────
# 3. game_sessions
# ──────────────────────────────────────
class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("players.id"), nullable=False
    )
    map_id: Mapped[str] = mapped_column(
        String(32), nullable=False, default="demo_map_v1"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active"
    )
    condition: Mapped[str] = mapped_column(
        String(16), nullable=False, default="adaptive"
    )
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default="phase3"
    )
    current_level_index: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    current_room: Mapped[str] = mapped_column(
        String(32), nullable=False, default="start_room"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationships
    player: Mapped["Player"] = relationship(back_populates="sessions")
    skill_estimates: Mapped[list["SkillEstimate"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    game_state: Mapped["GameState | None"] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    event_logs: Mapped[list["EventLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_game_sessions_player_status", "player_id", "status"),
    )

    @validates("mode")
    def _validate_mode_immutable(self, key: str, value: str) -> str:
        allowed = {"phase3", "gameplay_v2"}
        if value not in allowed:
            raise ValueError("mode must be one of: phase3, gameplay_v2")

        state = inspect(self)
        if state.persistent and state.attrs.mode.value is not None and state.attrs.mode.value != value:
            raise ValueError("session.mode is immutable")
        return value


# ──────────────────────────────────────
# 4. skill_estimates  (BKT state)
# ──────────────────────────────────────
class SkillEstimate(Base):
    __tablename__ = "skill_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"), nullable=False
    )
    p_ln: Mapped[float] = mapped_column(Float, nullable=False)
    p_t: Mapped[float] = mapped_column(Float, nullable=False)
    p_g: Mapped[float] = mapped_column(Float, nullable=False)
    p_s: Mapped[float] = mapped_column(Float, nullable=False)
    update_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # relationships
    session: Mapped["GameSession"] = relationship(back_populates="skill_estimates")
    skill: Mapped["Skill"] = relationship()

    __table_args__ = (
        UniqueConstraint("session_id", "skill_id", name="uq_session_skill"),
    )


# ──────────────────────────────────────
# 5. puzzles
# ──────────────────────────────────────
class Puzzle(Base):
    __tablename__ = "puzzles"

    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False)
    room: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    base_difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_hints: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2)
    order_in_room: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # relationships
    skill: Mapped["Skill"] = relationship()
    variants: Mapped[list["PuzzleVariant"]] = relationship(
        back_populates="puzzle", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_puzzles_room_order", "room", "order_in_room"),
    )


# ──────────────────────────────────────
# 6. puzzle_variants
# ──────────────────────────────────────
class PuzzleVariant(Base):
    __tablename__ = "puzzle_variants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    puzzle_id: Mapped[str] = mapped_column(
        ForeignKey("puzzles.id"), nullable=False
    )
    difficulty_tier: Mapped[str] = mapped_column(String(8), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answers: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    time_limit_sec: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    # relationships
    puzzle: Mapped["Puzzle"] = relationship(back_populates="variants")

    __table_args__ = (
        UniqueConstraint("puzzle_id", "difficulty_tier", name="uq_puzzle_tier"),
    )


# ──────────────────────────────────────
# 7. attempts
# ──────────────────────────────────────
class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=False
    )
    puzzle_id: Mapped[str] = mapped_column(
        ForeignKey("puzzles.id"), nullable=False
    )
    variant_id: Mapped[str] = mapped_column(
        ForeignKey("puzzle_variants.id"), nullable=False
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id"), nullable=False
    )
    player_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    p_ln_before: Mapped[float] = mapped_column(Float, nullable=False)
    p_ln_after: Mapped[float] = mapped_column(Float, nullable=False)
    difficulty_tier: Mapped[str] = mapped_column(String(8), nullable=False)
    hint_count_used: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0
    )
    attempt_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # relationships
    session: Mapped["GameSession"] = relationship(back_populates="attempts")

    __table_args__ = (
        Index("ix_attempts_session_puzzle", "session_id", "puzzle_id"),
        Index("ix_attempts_session", "session_id"),
        Index("ix_attempts_skill", "skill_id"),
        Index("ix_attempts_created", "created_at"),
    )


# ──────────────────────────────────────
# 8. game_state
# ──────────────────────────────────────
class GameState(Base):
    __tablename__ = "game_state"

    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id"), primary_key=True
    )
    inventory: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    unlocked_rooms: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: ["start_room"]
    )
    solved_puzzles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    flags: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    hints_remaining: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=5
    )
    game_state_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # relationships
    session: Mapped["GameSession"] = relationship(back_populates="game_state")


# ──────────────────────────────────────
# 9. event_log
# ──────────────────────────────────────
class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # relationships
    session: Mapped["GameSession"] = relationship(back_populates="event_logs")

    __table_args__ = (
        Index("ix_event_log_session", "session_id"),
        Index("ix_event_log_type", "event_type"),
        Index("ix_event_log_created", "created_at"),
    )


# ──────────────────────────────────────
# 10. room_templates (gameplay v2 seed content)
# ──────────────────────────────────────
class RoomTemplate(Base):
    __tablename__ = "room_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


# ──────────────────────────────────────
# 11. action_dedupe (gameplay v2 idempotency)
# ──────────────────────────────────────
class ActionDedupe(Base):
    __tablename__ = "action_dedupe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("game_sessions.id"), nullable=False
    )
    client_action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    response_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("session_id", "client_action_id", name="uq_action_dedupe_session_client"),
        Index("ix_action_dedupe_session", "session_id"),
    )

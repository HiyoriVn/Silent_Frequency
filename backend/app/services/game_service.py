"""
Silent Frequency — Gameplay v2 Service

Backend-owned room action stubs for Batch 4.0.
This module is additive and does not alter Phase-3 scoring/progression flows.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import ActionDedupe, EventLog, GameSession, GameState, RoomTemplate


class GameplayServiceError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.extra = extra or {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _default_room_state() -> list[dict[str, Any]]:
    return [
        {
            "id": "old_radio",
            "type": "interactable",
            "state": "locked",
            "properties": {
                "locked": True,
                "revealed": True,
                "asset_key": "lab1-desk",
                "hotspot": {
                    "x": 0.12,
                    "y": 0.28,
                    "w": 0.22,
                    "h": 0.28,
                    "label": "Old Radio",
                    "default_action": "inspect",
                },
            },
        },
        {
            "id": "drawer",
            "type": "container",
            "state": "locked",
            "properties": {
                "locked": True,
                "revealed": True,
                "hotspot": {
                    "x": 0.62,
                    "y": 0.48,
                    "w": 0.2,
                    "h": 0.24,
                    "label": "Drawer",
                    "default_action": "take_item",
                },
            },
        },
        {
            "id": "note",
            "type": "clue",
            "state": "revealed",
            "properties": {
                "revealed": True,
                "hotspot": {
                    "x": 0.38,
                    "y": 0.22,
                    "w": 0.18,
                    "h": 0.18,
                    "label": "Note",
                    "default_action": "inspect",
                },
            },
        },
    ]


def _default_template_payload() -> dict[str, Any]:
    return {
        "interaction_schema_version": 2,
        "room_id": "lab1",
        "background_asset_key": "lab1-desk",
        "objects": _default_room_state(),
        "items": {
            "bent_key": {
                "id": "bent_key",
                "display_name": "Bent Key",
                "category": "tool",
                "consumed": False,
                "properties": {},
            }
        },
        "effects": {
            "use_item:old_radio:bent_key": [
                {"type": "unlock", "target_id": "old_radio"},
                {"type": "open_puzzle", "puzzle_id": "start_listen_code"},
            ],
            "inspect:note": [
                {
                    "type": "show_dialogue",
                    "dialogue_id": "note_read_01",
                    "target_id": "note",
                    "dialogue_text": "The note says: tune the old radio and listen for the code.",
                }
            ],
            "take_item:drawer": [
                {"type": "add_item", "item_id": "bent_key", "target_id": "bent_key"}
            ],
        },
        "hint_policy": {"idle_seconds": 45, "failed_attempts_threshold": 2},
    }


def _ensure_mode_gate(session: GameSession) -> None:
    settings = get_settings()
    if not settings.gameplay_v2_enabled:
        raise GameplayServiceError(
            status_code=403,
            code="MODE_DISABLED",
            message="Gameplay v2 endpoints are disabled by GAMEPLAY_V2_ENABLED.",
        )
    if session.mode != "gameplay_v2":
        raise GameplayServiceError(
            status_code=403,
            code="MODE_MISMATCH",
            message="Session mode is not gameplay_v2.",
        )


async def _get_room_template(db: AsyncSession, room_id: str) -> dict[str, Any]:
    result = await db.execute(
        select(RoomTemplate).where(RoomTemplate.room_id == room_id)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return _default_template_payload()
    return row.payload


async def _get_session_and_state_for_update(
    db: AsyncSession, session_id: uuid.UUID
) -> tuple[GameSession, GameState]:
    session_result = await db.execute(
        select(GameSession)
        .where(GameSession.id == session_id)
        .with_for_update()
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise GameplayServiceError(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Session {session_id} not found.",
        )

    state_result = await db.execute(
        select(GameState)
        .where(GameState.session_id == session_id)
        .with_for_update()
    )
    state = state_result.scalar_one_or_none()
    if state is None:
        raise GameplayServiceError(
            status_code=404,
            code="GAME_STATE_NOT_FOUND",
            message=f"Game state for session {session_id} not found.",
        )

    return session, state


def _build_snapshot(
    *,
    session: GameSession,
    state: GameState,
    template_payload: dict[str, Any],
) -> dict[str, Any]:
    room_state = state.flags.get("room_state") if isinstance(state.flags, dict) else None
    active_puzzles = state.flags.get("active_puzzles") if isinstance(state.flags, dict) else None

    if room_state is None:
        room_state = template_payload.get("objects", _default_room_state())
    if active_puzzles is None:
        active_puzzles = []

    inventory = state.inventory if isinstance(state.inventory, list) else []

    return {
        "interaction_schema_version": 2,
        "session_id": session.id,
        "game_state_version": state.game_state_version,
        "updated_at": state.updated_at,
        "room_id": template_payload.get("room_id", session.current_room),
        "room_state": room_state,
        "inventory": inventory,
        "active_puzzles": active_puzzles,
        "hint_policy": template_payload.get("hint_policy"),
    }


async def get_game_state(db: AsyncSession, session_id: uuid.UUID) -> dict[str, Any]:
    session = await db.get(GameSession, session_id)
    if session is None:
        raise GameplayServiceError(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Session {session_id} not found.",
        )
    _ensure_mode_gate(session)

    state = await db.get(GameState, session_id)
    if state is None:
        raise GameplayServiceError(
            status_code=404,
            code="GAME_STATE_NOT_FOUND",
            message=f"Game state for session {session_id} not found.",
        )

    room_id = session.current_room if session.current_room else "lab1"
    template_payload = await _get_room_template(db, room_id)

    # Read-only endpoint: no mutations.
    return _build_snapshot(session=session, state=state, template_payload=template_payload)


def _minimal_effects_for_telemetry(effects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed = []
    for effect in effects[:50]:
        trimmed.append(
            {
                "type": effect.get("type"),
                "target_id": effect.get("target_id") or effect.get("item_id") or effect.get("puzzle_id"),
            }
        )
    return trimmed


def _resolve_effects(
    *,
    action: str,
    target_id: str,
    item_id: str | None,
    template_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    effects_map = {
        str(k): list(v)
        for k, v in dict(template_payload.get("effects", {})).items()
    }
    key_with_item = f"{action}:{target_id}:{item_id}" if item_id else None
    key_no_item = f"{action}:{target_id}"

    if key_with_item and key_with_item in effects_map:
        return list(effects_map[key_with_item])
    if key_no_item in effects_map:
        return list(effects_map[key_no_item])

    raise GameplayServiceError(
        status_code=400,
        code="INVALID_ACTION",
        message=f"Unsupported action for target_id={target_id}.",
    )


def _apply_effects(
    *,
    effects: list[dict[str, Any]],
    state: GameState,
    template_payload: dict[str, Any],
) -> None:
    flags = state.flags if isinstance(state.flags, dict) else {}
    room_state = flags.get("room_state")
    if room_state is None:
        room_state = list(template_payload.get("objects", _default_room_state()))

    inventory = state.inventory if isinstance(state.inventory, list) else []
    active_puzzles = flags.get("active_puzzles") or []
    items_catalog = template_payload.get("items", {})

    for effect in effects:
        effect_type = effect.get("type")
        if effect_type == "unlock":
            target = effect.get("target_id")
            for obj in room_state:
                if obj.get("id") == target:
                    obj["state"] = "unlocked"
                    props = obj.get("properties", {})
                    props["locked"] = False
                    obj["properties"] = props
                    break
        elif effect_type == "add_item":
            item_id = effect.get("item_id")
            if item_id and all(i.get("id") != item_id for i in inventory):
                item_payload = items_catalog.get(item_id) or {
                    "id": item_id,
                    "display_name": item_id.replace("_", " ").title(),
                    "category": "tool",
                    "consumed": False,
                    "properties": {},
                }
                inventory.append(item_payload)
        elif effect_type == "open_puzzle":
            puzzle_id = effect.get("puzzle_id")
            if puzzle_id and puzzle_id not in active_puzzles:
                active_puzzles.append(puzzle_id)
        elif effect_type == "show_dialogue":
            # Declarative-only for Batch 4.0; no canonical mutation needed.
            continue

    flags["room_state"] = room_state
    flags["active_puzzles"] = active_puzzles
    state.flags = flags
    state.inventory = inventory


async def apply_action(
    db: AsyncSession,
    session_id: uuid.UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if payload.get("interaction_schema_version") != 2:
        raise GameplayServiceError(
            status_code=400,
            code="INVALID_SCHEMA_VERSION",
            message="interaction_schema_version must be 2.",
        )

    client_action_id = payload.get("client_action_id")

    async with db.begin():
        session, state = await _get_session_and_state_for_update(db, session_id)
        _ensure_mode_gate(session)

        if client_action_id is not None:
            dedupe_result = await db.execute(
                select(ActionDedupe).where(
                    ActionDedupe.session_id == session_id,
                    ActionDedupe.client_action_id == client_action_id,
                )
            )
            dedupe_row = dedupe_result.scalar_one_or_none()
            if dedupe_row is not None:
                return dedupe_row.response_json

        client_version = payload.get("game_state_version")
        room_id = session.current_room if session.current_room else "lab1"
        template_payload = await _get_room_template(db, room_id)

        if client_version is not None and int(client_version) != state.game_state_version:
            snapshot = _build_snapshot(session=session, state=state, template_payload=template_payload)
            raise GameplayServiceError(
                status_code=409,
                code="STATE_MISMATCH",
                message="client state stale",
                extra={
                    "meta": {
                        "interaction_schema_version": 2,
                        "game_state_version": state.game_state_version,
                    },
                    "data_snapshot": snapshot,
                },
            )

        effects = _resolve_effects(
            action=payload["action"],
            target_id=payload["target_id"],
            item_id=payload.get("item_id"),
            template_payload=template_payload,
        )

        _apply_effects(effects=effects, state=state, template_payload=template_payload)

        state.game_state_version += 1
        state.updated_at = _utcnow()

        snapshot = _build_snapshot(session=session, state=state, template_payload=template_payload)
        response_payload: dict[str, Any] = {
            "ok": True,
            "data": {
                "effects": effects,
                "game_state": snapshot,
            },
            "error": None,
            "meta": {
                "interaction_schema_version": 2,
                "game_state_version": state.game_state_version,
            },
        }
        encoded_response_payload = jsonable_encoder(response_payload)

        telemetry_payload = {
            "version": 1,
            "session_id": str(session_id),
            "action": payload["action"],
            "target_id": payload["target_id"],
            "item_id": payload.get("item_id"),
            "client_action_id": str(client_action_id) if client_action_id else None,
            "timestamp": _utcnow().isoformat(),
            "resulting_effects": _minimal_effects_for_telemetry(effects),
        }

        if len(json.dumps(telemetry_payload)) > 10_000:
            telemetry_payload["resulting_effects"] = telemetry_payload["resulting_effects"][:10]

        db.add(
            EventLog(
                session_id=session_id,
                event_type="game_action",
                payload=telemetry_payload,
            )
        )

        if client_action_id is not None:
            db.add(
                ActionDedupe(
                    session_id=session_id,
                    client_action_id=client_action_id,
                    response_json=encoded_response_payload,
                )
            )

    return encoded_response_payload

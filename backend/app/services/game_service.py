"""
Silent Frequency — Gameplay v2 Service

Backend-owned room action stubs for Batch 4.0+.
This module is additive and does not alter Phase-3 scoring/progression flows.
"""

from __future__ import annotations

import logging
import copy

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..db.models import ActionDedupe, EventLog, GameSession, GameState, RoomTemplate
from .. import metrics

logger = logging.getLogger(__name__)

MAX_TRACE_EVENTS = 20
MAX_TRACE_EVENT_BYTES = 10_000

# Temporary Room 404 bridge while frontend migrates to canonical-only gameplay payloads.
# Keep this backend-only and retire once all legacy target/action usage is removed.
_ROOM404_COMPAT_CANONICAL_TO_LEGACY_TARGET = {
    "bedside_table": "drawer",
    "folded_note": "note",
    "warning_sign": "old_radio",
}

_ROOM404_COMPAT_LEGACY_TO_CANONICAL_TARGET = {
    legacy_id: canonical_id
    for canonical_id, legacy_id in _ROOM404_COMPAT_CANONICAL_TO_LEGACY_TARGET.items()
}

_ROOM404_COMPAT_CANONICAL_OBJECT_IDS = {
    "folded_note": ("folded_note", "note"),
}

_ROOM404_COMPAT_CANONICAL_TO_LEGACY_ACTION = {
    "collect": "inspect",
    "navigation": "open_object",
    "open_sub_view": "open_object",
}

_CANONICAL_HOTSPOT_PARENT_VIEW_DEFAULTS = {
    "bedside_table": "patient_room_404__bg_01_bed_wall",
    "folded_note": "patient_room_404__sub_bedside_drawer",
    "warning_sign": "patient_room_404__bg_04_door_side",
    "main_door": "patient_room_404__bg_04_door_side",
}

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


def _room404_canonical_target_id(target_id: str) -> str:
    return _ROOM404_COMPAT_LEGACY_TO_CANONICAL_TARGET.get(target_id, target_id)


def _room404_legacy_target_id(target_id: str) -> str:
    return _ROOM404_COMPAT_CANONICAL_TO_LEGACY_TARGET.get(target_id, target_id)


def _room404_legacy_action(action: str) -> str:
    return _ROOM404_COMPAT_CANONICAL_TO_LEGACY_ACTION.get(action, action)


def _room404_object_ids_for_canonical_target(target_id: str) -> tuple[str, ...]:
    return _ROOM404_COMPAT_CANONICAL_OBJECT_IDS.get(target_id, (target_id,))


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


def _resolve_current_background_view_id(
    *,
    view_id: str,
    template_payload: dict[str, Any],
) -> str:
    if view_id.startswith("patient_room_404__bg_"):
        return view_id

    background_ref = template_payload.get("background_asset_key")
    if isinstance(background_ref, str) and background_ref.startswith("patient_room_404__bg_"):
        return background_ref

    return "patient_room_404__bg_01_bed_wall"


def _compute_hotspot_visible(
    *,
    parent_view_id: str,
    visibility_intent: str,
    active_view_id: str,
    sub_view_id: str | None,
) -> bool:
    if parent_view_id != active_view_id:
        return False
    if visibility_intent == "hidden":
        return False
    if visibility_intent == "hidden_until_sub_view_open":
        return sub_view_id == parent_view_id
    return True


def _compute_hotspot_clickable(
    *,
    visible: bool,
    clickability_intent: str,
    canonical_flags: dict[str, Any],
) -> bool:
    if not visible:
        return False
    if clickability_intent == "disabled":
        return False
    if clickability_intent == "enabled_when_unlocked":
        return bool(canonical_flags.get("room404_exit_unlocked"))
    return True


def _canonical_hotspots_from_template(
    *,
    template_payload: dict[str, Any],
    view_id: str,
    sub_view_id: str | None,
    canonical_flags: dict[str, Any],
) -> list[dict[str, Any]]:
    hotspots_data = template_payload.get("hotspots")
    if not isinstance(hotspots_data, list):
        return []

    active_view_id = sub_view_id or view_id
    hotspots: list[dict[str, Any]] = []

    for entry in hotspots_data:
        if not isinstance(entry, dict):
            continue
        hotspot_id = entry.get("id")
        if not isinstance(hotspot_id, str) or not hotspot_id:
            continue

        parent_view_id = entry.get("parent_view_id")
        if not isinstance(parent_view_id, str) or not parent_view_id:
            parent_view_id = view_id

        visibility_intent = str(entry.get("visibility_intent") or "visible")
        clickability_intent = str(entry.get("clickability_intent") or "enabled_when_visible")

        visible = _compute_hotspot_visible(
            parent_view_id=parent_view_id,
            visibility_intent=visibility_intent,
            active_view_id=active_view_id,
            sub_view_id=sub_view_id,
        )
        clickable = _compute_hotspot_clickable(
            visible=visible,
            clickability_intent=clickability_intent,
            canonical_flags=canonical_flags,
        )

        target_view_id = entry.get("target_view_id")
        if not isinstance(target_view_id, str):
            target_view_id = None

        action_hint = entry.get("target_action")
        if not isinstance(action_hint, str):
            action_hint = None

        hotspots.append(
            {
                "id": hotspot_id,
                "type": str(entry.get("type") or "interactable"),
                "parent_view_id": parent_view_id,
                "visible": visible,
                "clickable": clickable,
                "target_view_id": target_view_id,
                "action_hint": action_hint,
            }
        )

    return hotspots


def _canonical_hotspots_from_legacy_state(
    *,
    room_state: list[dict[str, Any]],
    view_id: str,
    sub_view_id: str | None,
    canonical_flags: dict[str, Any],
) -> list[dict[str, Any]]:
    active_view_id = sub_view_id or view_id
    hotspots: list[dict[str, Any]] = []
    seen: set[str] = set()

    for obj in room_state:
        if not isinstance(obj, dict):
            continue
        properties = obj.get("properties")
        if not isinstance(properties, dict):
            continue
        hotspot_props = properties.get("hotspot")
        if not isinstance(hotspot_props, dict):
            continue

        legacy_id = obj.get("id")
        if not isinstance(legacy_id, str) or not legacy_id:
            continue

        canonical_id = _room404_canonical_target_id(legacy_id)
        if canonical_id in seen:
            continue
        seen.add(canonical_id)

        parent_view_id = _CANONICAL_HOTSPOT_PARENT_VIEW_DEFAULTS.get(
            canonical_id,
            active_view_id,
        )
        visibility_intent = (
            "hidden_until_sub_view_open"
            if canonical_id == "folded_note"
            else "visible"
        )
        clickability_intent = (
            "enabled_when_unlocked"
            if canonical_id == "main_door"
            else "enabled_when_visible"
        )

        visible = _compute_hotspot_visible(
            parent_view_id=parent_view_id,
            visibility_intent=visibility_intent,
            active_view_id=active_view_id,
            sub_view_id=sub_view_id,
        )
        clickable = _compute_hotspot_clickable(
            visible=visible,
            clickability_intent=clickability_intent,
            canonical_flags=canonical_flags,
        )

        default_action = hotspot_props.get("default_action")
        action_hint = default_action if isinstance(default_action, str) else None

        target_view_id = (
            "patient_room_404__sub_bedside_drawer"
            if canonical_id == "bedside_table"
            else None
        )

        hotspots.append(
            {
                "id": canonical_id,
                "type": str(obj.get("type") or "interactable"),
                "parent_view_id": parent_view_id,
                "visible": visible,
                "clickable": clickable,
                "target_view_id": target_view_id,
                "action_hint": action_hint,
            }
        )

    return hotspots


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
    state_flags = state.flags if isinstance(state.flags, dict) else {}
    room_state = state_flags.get("room_state") if isinstance(state_flags, dict) else None
    active_puzzles = state_flags.get("active_puzzles") if isinstance(state_flags, dict) else None

    canonical_flags = state_flags.get("flags") if isinstance(state_flags.get("flags"), dict) else {}
    if not canonical_flags and state_flags.get("self_assessed_level") is not None:
        canonical_flags = {"self_assessed_level": state_flags.get("self_assessed_level")}
    journal_entries = state_flags.get("journal_entries") if isinstance(state_flags.get("journal_entries"), list) else []

    chapter_id = state_flags.get("chapter_id") or "chapter_1"
    zone_id = state_flags.get("zone_id") or "patient_room_404"
    view_id = state_flags.get("view_id") or "patient_room_404__bg_01_bed_wall"
    sub_view_id = state_flags.get("sub_view_id")
    fsm_state = state_flags.get("fsm_state") or "room404_idle"
    current_background_view_id = _resolve_current_background_view_id(
        view_id=view_id,
        template_payload=template_payload,
    )

    if room_state is None:
        room_state = template_payload.get("objects", _default_room_state())
    if active_puzzles is None:
        active_puzzles = []

    hotspots = _canonical_hotspots_from_template(
        template_payload=template_payload,
        view_id=view_id,
        sub_view_id=sub_view_id,
        canonical_flags=canonical_flags,
    )
    if not hotspots:
        hotspots = _canonical_hotspots_from_legacy_state(
            room_state=room_state,
            view_id=view_id,
            sub_view_id=sub_view_id,
            canonical_flags=canonical_flags,
        )

    inventory = state.inventory if isinstance(state.inventory, list) else []

    return {
        "interaction_schema_version": 2,
        "session_id": session.id,
        "chapter_id": chapter_id,
        "zone_id": zone_id,
        "view_id": view_id,
        "current_background_view_id": current_background_view_id,
        "sub_view_id": sub_view_id,
        "fsm_state": fsm_state,
        "flags": canonical_flags,
        "journal_entries": journal_entries,
        "hotspots": hotspots,
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


def _canonical_state_flags_container(state: GameState) -> dict[str, Any]:
    base = state.flags if isinstance(state.flags, dict) else {}
    if not isinstance(base.get("flags"), dict):
        base["flags"] = {}
    if not isinstance(base.get("journal_entries"), list):
        base["journal_entries"] = []
    return base


def _canonical_flags(state_flags: dict[str, Any]) -> dict[str, Any]:
    raw = state_flags.get("flags")
    return raw if isinstance(raw, dict) else {}


def _room_state_for_mutation(
    *,
    state_flags: dict[str, Any],
    template_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    room_state = state_flags.get("room_state")
    if isinstance(room_state, list):
        return room_state
    seeded = template_payload.get("objects", _default_room_state())
    if isinstance(seeded, list):
        return copy.deepcopy(seeded)
    return _default_room_state()


def _set_room_object_state(
    room_state: list[dict[str, Any]],
    *,
    object_id: str,
    state_value: str,
    revealed: bool | None = None,
) -> None:
    for obj in room_state:
        if obj.get("id") != object_id:
            continue
        obj["state"] = state_value
        props = obj.get("properties") if isinstance(obj.get("properties"), dict) else {}
        if revealed is not None:
            props["revealed"] = revealed
        obj["properties"] = props
        return


def _resolve_legacy_payload_action(
    *,
    action: str,
    target_id: str,
) -> tuple[str, str]:
    mapped_target = _room404_legacy_target_id(target_id)
    mapped_action = _room404_legacy_action(action)
    return mapped_action, mapped_target


def _apply_room404_canonical_action(
    *,
    action: str,
    target_id: str,
    state: GameState,
    template_payload: dict[str, Any],
) -> list[dict[str, Any]] | None:
    if action not in {"inspect", "open_sub_view", "collect", "navigation"}:
        return None

    state_flags = _canonical_state_flags_container(state)
    canonical_flags = _canonical_flags(state_flags)
    room_state = _room_state_for_mutation(state_flags=state_flags, template_payload=template_payload)
    inventory = state.inventory if isinstance(state.inventory, list) else []
    effects: list[dict[str, Any]] = []

    current_view_id = state_flags.get("view_id") or "patient_room_404__bg_01_bed_wall"

    if action == "open_sub_view" and target_id == "bedside_table":
        state_flags["sub_view_id"] = "patient_room_404__sub_bedside_drawer"
        state_flags["fsm_state"] = "room404_sub_view_open"
        effects.append(
            {
                "type": "show_dialogue",
                "target_id": "bedside_table",
                "dialogue_id": "room404_drawer_opened",
            }
        )

    elif action == "collect" and target_id == "folded_note":
        already_collected = bool(canonical_flags.get("bedside_note_collected"))
        if not already_collected:
            canonical_flags["bedside_note_collected"] = True
            if all(item.get("id") != "folded_note" for item in inventory if isinstance(item, dict)):
                inventory.append(
                    {
                        "id": "folded_note",
                        "display_name": "Folded Note",
                        "category": "clue",
                        "consumed": False,
                        "properties": {"source": "patient_room_404"},
                    }
                )
            for object_id in _room404_object_ids_for_canonical_target("folded_note"):
                _set_room_object_state(
                    room_state,
                    object_id=object_id,
                    state_value="collected",
                    revealed=False,
                )
            effects.append(
                {
                    "type": "add_item",
                    "item_id": "folded_note",
                    "target_id": "folded_note",
                }
            )
        else:
            effects.append(
                {
                    "type": "show_dialogue",
                    "target_id": "folded_note",
                    "dialogue_id": "room404_note_already_collected",
                }
            )

    elif action == "inspect" and target_id == "warning_sign":
        canonical_flags["first_language_interaction_done"] = True
        effects.append(
            {
                "type": "open_puzzle",
                "puzzle_id": "p_warning_sign_translate",
                "target_id": "warning_sign",
            }
        )

    elif action == "navigation" and target_id == "main_door":
        if bool(canonical_flags.get("room404_exit_unlocked")):
            effects.append(
                {
                    "type": "show_dialogue",
                    "target_id": "main_door",
                    "dialogue_id": "room404_door_unlocked",
                }
            )
        else:
            effects.append(
                {
                    "type": "show_dialogue",
                    "target_id": "main_door",
                    "dialogue_id": "room404_door_locked",
                }
            )

    elif action == "navigation" and target_id in {
        "patient_room_404__bg_01_bed_wall",
        "patient_room_404__bg_04_door_side",
        "return_to_main",
    }:
        state_flags["sub_view_id"] = None
        state_flags["view_id"] = (
            target_id
            if target_id.startswith("patient_room_404__bg_")
            else current_view_id
        )
        state_flags["fsm_state"] = "room404_idle"
        effects.append(
            {
                "type": "show_dialogue",
                "target_id": "navigation",
                "dialogue_id": "room404_returned_to_main_view",
            }
        )

    else:
        return None

    state_flags["flags"] = canonical_flags
    state_flags["room_state"] = room_state
    state.flags = state_flags
    state.inventory = inventory

    return effects


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


def _build_trace_payload(trace_data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trim interaction trace and mark payload with _truncated when needed."""
    if trace_data is None:
        return None

    events = trace_data.get("trace") or []
    if not isinstance(events, list):
        events = []

    event_count_truncated = len(events) > MAX_TRACE_EVENTS
    trimmed_events: list[dict[str, Any]] = []
    oversized_event_trimmed = False

    for event in events[:MAX_TRACE_EVENTS]:
        if not isinstance(event, dict):
            trimmed_events.append(
                {"event_type": "unknown", "elapsed_ms": 0, "_oversized": True}
            )
            oversized_event_trimmed = True
            continue

        serialized = json.dumps(event)
        if len(serialized) <= MAX_TRACE_EVENT_BYTES:
            trimmed_events.append(event)
            continue

        oversized_event_trimmed = True
        trimmed_events.append(
            {
                "event_type": event.get("event_type", "unknown"),
                "elapsed_ms": event.get("elapsed_ms", 0),
                "_oversized": True,
            }
        )

    truncated = event_count_truncated or oversized_event_trimmed
    if truncated:
        metrics.increment("telemetry.trace.truncated")
    if oversized_event_trimmed:
        metrics.increment("telemetry.trace.too_large")

    payload: dict[str, Any] = {
        "version": trace_data.get("version", 1),
        "type": "interaction_trace",
        "puzzle_id": trace_data.get("puzzle_id"),
        "variant_id": trace_data.get("variant_id"),
        "trace": trimmed_events,
        "response_time_ms": trace_data.get("response_time_ms", 0),
    }
    if truncated:
        payload["_truncated"] = True

    # Guard against a large full trace payload by further trimming events from the tail.
    while len(json.dumps(payload)) > MAX_TRACE_EVENT_BYTES and payload["trace"]:
        payload["trace"] = payload["trace"][:-1]
        payload["_truncated"] = True
        metrics.increment("telemetry.trace.too_large")
        metrics.increment("telemetry.trace.truncated")

    return payload


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

        effects = _apply_room404_canonical_action(
            action=payload["action"],
            target_id=payload["target_id"],
            state=state,
            template_payload=template_payload,
        )

        if effects is None:
            resolved_action, resolved_target_id = _resolve_legacy_payload_action(
                action=payload["action"],
                target_id=payload["target_id"],
            )
            effects = _resolve_effects(
                action=resolved_action,
                target_id=resolved_target_id,
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

        # ── game_action telemetry ──
        telemetry_payload: dict[str, Any] = {
            "version": 1,
            "type": "game_action",
            "session_id": str(session_id),
            "action": payload["action"],
            "target_id": payload["target_id"],
            "item_id": payload.get("item_id"),
            "client_action_id": str(client_action_id) if client_action_id else None,
            "timestamp": _utcnow().isoformat(),
            "resulting_effects": _minimal_effects_for_telemetry(effects),
        }

        serialized_size = len(json.dumps(telemetry_payload))
        if serialized_size > 10_000:
            logger.warning(
                "game_action telemetry payload exceeds 10KB (%d bytes), trimming effects for session %s",
                serialized_size,
                session_id,
            )
            telemetry_payload["resulting_effects"] = telemetry_payload["resulting_effects"][:10]

        db.add(
            EventLog(
                session_id=session_id,
                event_type="game_action",
                payload=telemetry_payload,
            )
        )
        metrics.increment("telemetry.game_action.count")

        # ── puzzle_interaction_trace observational logging ──
        raw_trace = payload.get("interaction_trace")
        if raw_trace is not None:
            trace_payload = _build_trace_payload(raw_trace)
            if trace_payload is not None:
                trace_serialized = json.dumps(trace_payload)
                if len(trace_serialized) > 10_000:
                    logger.warning(
                        "puzzle_interaction_trace payload exceeds 10KB (%d bytes) for session %s, trimming trace",
                        len(trace_serialized),
                        session_id,
                    )
                    trace_payload["trace"] = trace_payload["trace"][:10]
                    trace_payload["_truncated"] = True
                db.add(
                    EventLog(
                        session_id=session_id,
                        event_type="puzzle_interaction_trace",
                        payload=trace_payload,
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

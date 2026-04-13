from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.api.schemas import ActionRequest, GameStateSnapshot


def test_action_request_accepts_schema_v2() -> None:
    payload = {
        "interaction_schema_version": 2,
        "action": "use_item",
        "target_id": "old_radio",
        "item_id": "bent_key",
        "client_action_id": str(uuid.uuid4()),
        "game_state_version": 0,
    }
    model = ActionRequest(**payload)
    assert model.interaction_schema_version == 2
    assert model.action == "use_item"


def test_action_request_accepts_non_v2_for_service_validation() -> None:
    payload = {
        "interaction_schema_version": 1,
        "action": "inspect",
        "target_id": "note",
    }
    model = ActionRequest(**payload)
    assert model.interaction_schema_version == 1


def test_action_request_forbids_unknown_keys() -> None:
    payload = {
        "interaction_schema_version": 2,
        "action": "inspect",
        "target_id": "note",
        "unexpected": True,
    }
    with pytest.raises(ValidationError):
        ActionRequest(**payload)


def test_game_state_snapshot_minimal_valid() -> None:
    snapshot = GameStateSnapshot(
        interaction_schema_version=2,
        session_id=uuid.uuid4(),
        game_state_version=0,
        updated_at=datetime.now(timezone.utc),
        room_id="lab1",
        room_state=[],
        inventory=[],
        active_puzzles=[],
        adaptive_output={"difficulty_tier": "mid"},
    )
    assert snapshot.room_id == "lab1"
    assert snapshot.game_state_version == 0
    assert snapshot.adaptive_output.difficulty_tier == "mid"

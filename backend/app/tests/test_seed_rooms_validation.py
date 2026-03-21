from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from backend.app.seed import PUZZLES, _validate_room_doc


def _load_sample_room() -> dict:
    path = Path("backend/app/content/rooms/sample_room_01.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["__source_file"] = path.name
    return data


def test_room_validator_accepts_sample_room() -> None:
    room = _load_sample_room()
    puzzle_ids = {p["id"] for p in PUZZLES}
    _validate_room_doc(room, valid_puzzle_ids=puzzle_ids)


def test_room_validator_rejects_unknown_puzzle_reference() -> None:
    room = _load_sample_room()
    broken = copy.deepcopy(room)
    broken["effects"]["use_item:old_radio:bent_key"][1]["puzzle_id"] = "missing_puzzle"
    puzzle_ids = {p["id"] for p in PUZZLES}

    with pytest.raises(ValueError):
        _validate_room_doc(broken, valid_puzzle_ids=puzzle_ids)

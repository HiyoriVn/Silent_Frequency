"""
Silent Frequency — Database Seed Script

Loads puzzle content JSON files and seeds skills, puzzles, and variants.
Run with:  python -m backend.app.seed
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select

from backend.app.db.database import engine, async_session_factory, Base
from backend.app.db.models import Skill, Puzzle, PuzzleVariant


# ──────────────────────────────────────
# Seed data
# ──────────────────────────────────────

SKILLS = [
    {"id": 1, "code": "vocabulary", "label": "Vocabulary", "bkt_p_l0": 0.10, "bkt_p_t": 0.20, "bkt_p_g": 0.25, "bkt_p_s": 0.10},
    {"id": 2, "code": "grammar",    "label": "Grammar",    "bkt_p_l0": 0.10, "bkt_p_t": 0.20, "bkt_p_g": 0.25, "bkt_p_s": 0.10},
    {"id": 3, "code": "listening",  "label": "Listening",  "bkt_p_l0": 0.10, "bkt_p_t": 0.20, "bkt_p_g": 0.25, "bkt_p_s": 0.10},
]

REQUIRED_TIERS = ("low", "mid", "high")
ALLOWED_SKILLS = {"vocabulary", "grammar", "listening"}
ALLOWED_ROOMS = {"start_room", "radio_room", "lab_room"}
_CONTENT_DIR = Path(__file__).resolve().parent / "content" / "puzzles"


def _load_puzzle_docs() -> list[dict[str, Any]]:
    if not _CONTENT_DIR.exists():
        raise ValueError(f"Puzzle content directory not found: {_CONTENT_DIR}")

    docs: list[dict[str, Any]] = []
    for path in sorted(_CONTENT_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8") as f:
            doc = json.load(f)
        doc["__source_file"] = path.name
        docs.append(doc)

    if not docs:
        raise ValueError(f"No puzzle JSON files found in {_CONTENT_DIR}")

    return docs


def _validate_puzzle_doc(doc: dict[str, Any]) -> None:
    source = doc.get("__source_file", "<unknown>")

    required = {
        "puzzle_id",
        "skill",
        "slot_order",
        "title",
        "room",
        "mechanic",
        "max_hints",
        "variants",
    }
    missing = required - set(doc.keys())
    if missing:
        raise ValueError(f"{source}: missing required keys: {sorted(missing)}")

    if doc["skill"] not in ALLOWED_SKILLS:
        raise ValueError(f"{source}: invalid skill '{doc['skill']}'")
    if doc["room"] not in ALLOWED_ROOMS:
        raise ValueError(f"{source}: invalid room '{doc['room']}'")
    if not isinstance(doc["slot_order"], int) or doc["slot_order"] < 1:
        raise ValueError(f"{source}: slot_order must be a positive integer")

    variants = doc["variants"]
    if not isinstance(variants, dict):
        raise ValueError(f"{source}: variants must be an object")
    if set(variants.keys()) != set(REQUIRED_TIERS):
        raise ValueError(
            f"{source}: variants must include exactly {list(REQUIRED_TIERS)}"
        )

    for tier in REQUIRED_TIERS:
        variant = variants[tier]
        v_required = {
            "prompt_text",
            "answer_type",
            "correct_answers",
            "audio_url",
            "time_limit_sec",
            "hints",
        }
        v_missing = v_required - set(variant.keys())
        if v_missing:
            raise ValueError(
                f"{source}: tier '{tier}' missing keys: {sorted(v_missing)}"
            )

        answers = variant["correct_answers"]
        if not isinstance(answers, list) or not answers:
            raise ValueError(
                f"{source}: tier '{tier}' correct_answers must be a non-empty list"
            )
        if any(not isinstance(ans, str) or not ans.strip() for ans in answers):
            raise ValueError(
                f"{source}: tier '{tier}' correct_answers must contain non-empty strings"
            )

        hints = variant["hints"]
        if not isinstance(hints, list):
            raise ValueError(f"{source}: tier '{tier}' hints must be a list")
        if len(hints) > int(doc["max_hints"]):
            raise ValueError(
                f"{source}: tier '{tier}' has more hints than max_hints"
            )


def _build_seed_payload() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    docs = _load_puzzle_docs()

    seen_puzzle_ids: set[str] = set()
    seen_skill_slot: set[tuple[str, int]] = set()

    skill_id_by_code = {row["code"]: row["id"] for row in SKILLS}
    puzzles: list[dict[str, Any]] = []
    variants: list[dict[str, Any]] = []

    for doc in docs:
        _validate_puzzle_doc(doc)

        puzzle_id = doc["puzzle_id"]
        skill_code = doc["skill"]
        slot_order = doc["slot_order"]

        if puzzle_id in seen_puzzle_ids:
            raise ValueError(f"Duplicate puzzle_id found: {puzzle_id}")
        seen_puzzle_ids.add(puzzle_id)

        skill_slot_key = (skill_code, slot_order)
        if skill_slot_key in seen_skill_slot:
            raise ValueError(
                f"Duplicate slot assignment for skill={skill_code}, slot={slot_order}"
            )
        seen_skill_slot.add(skill_slot_key)

        puzzles.append(
            {
                "id": puzzle_id,
                "skill_id": skill_id_by_code[skill_code],
                "room": doc["room"],
                "title": doc["title"],
                "base_difficulty": slot_order,
                "max_hints": doc["max_hints"],
                "order_in_room": slot_order,
                "is_required": True,
            }
        )

        for tier in REQUIRED_TIERS:
            variant = doc["variants"][tier]
            variants.append(
                {
                    "id": f"{puzzle_id}__{tier}",
                    "puzzle_id": puzzle_id,
                    "difficulty_tier": tier,
                    "prompt_text": variant["prompt_text"],
                    "correct_answers": variant["correct_answers"],
                    "audio_url": variant["audio_url"],
                    "time_limit_sec": variant["time_limit_sec"],
                    "metadata": {
                        "answer_type": variant["answer_type"],
                        "hints": variant["hints"],
                        "mechanic": doc["mechanic"],
                        "source_file": doc["__source_file"],
                    },
                }
            )

    # Ensure each skill has continuous slot coverage for progression logic.
    for skill in ALLOWED_SKILLS:
        slots = sorted(slot for s, slot in seen_skill_slot if s == skill)
        if slots != [1, 2, 3]:
            raise ValueError(
                f"Skill '{skill}' must define exactly slot_order 1,2,3. Found: {slots}"
            )

    return puzzles, variants


PUZZLES, VARIANTS = _build_seed_payload()


async def _seed_skills() -> tuple[int, int]:
    inserted = 0
    updated = 0

    async with async_session_factory() as db:
        existing_result = await db.execute(select(Skill))
        by_code = {row.code: row for row in existing_result.scalars().all()}

        for payload in SKILLS:
            existing = by_code.get(payload["code"])
            if existing is None:
                db.add(Skill(**payload))
                inserted += 1
                continue

            existing.label = payload["label"]
            existing.bkt_p_l0 = payload["bkt_p_l0"]
            existing.bkt_p_t = payload["bkt_p_t"]
            existing.bkt_p_g = payload["bkt_p_g"]
            existing.bkt_p_s = payload["bkt_p_s"]
            updated += 1

        await db.commit()

    return inserted, updated


async def _seed_puzzles_and_variants() -> tuple[int, int, int, int]:
    puzzle_inserted = 0
    puzzle_updated = 0
    variant_inserted = 0
    variant_updated = 0

    async with async_session_factory() as db:
        existing_puzzles_result = await db.execute(select(Puzzle))
        existing_puzzles = {row.id: row for row in existing_puzzles_result.scalars().all()}

        for payload in PUZZLES:
            existing = existing_puzzles.get(payload["id"])
            if existing is None:
                db.add(Puzzle(**payload))
                puzzle_inserted += 1
                continue

            existing.skill_id = payload["skill_id"]
            existing.room = payload["room"]
            existing.title = payload["title"]
            existing.base_difficulty = payload["base_difficulty"]
            existing.max_hints = payload["max_hints"]
            existing.order_in_room = payload["order_in_room"]
            existing.is_required = payload["is_required"]
            puzzle_updated += 1

        await db.flush()

        existing_variants_result = await db.execute(select(PuzzleVariant))
        existing_variants = {
            row.id: row for row in existing_variants_result.scalars().all()
        }

        for payload in VARIANTS:
            existing = existing_variants.get(payload["id"])
            if existing is None:
                db.add(
                    PuzzleVariant(
                        id=payload["id"],
                        puzzle_id=payload["puzzle_id"],
                        difficulty_tier=payload["difficulty_tier"],
                        prompt_text=payload["prompt_text"],
                        correct_answers=payload["correct_answers"],
                        audio_url=payload["audio_url"],
                        time_limit_sec=payload["time_limit_sec"],
                        metadata_=payload["metadata"],
                    )
                )
                variant_inserted += 1
                continue

            existing.puzzle_id = payload["puzzle_id"]
            existing.difficulty_tier = payload["difficulty_tier"]
            existing.prompt_text = payload["prompt_text"]
            existing.correct_answers = payload["correct_answers"]
            existing.audio_url = payload["audio_url"]
            existing.time_limit_sec = payload["time_limit_sec"]
            existing.metadata_ = payload["metadata"]
            variant_updated += 1

        await db.commit()

    return puzzle_inserted, puzzle_updated, variant_inserted, variant_updated


# ──────────────────────────────────────
# Seed runner
# ──────────────────────────────────────

async def seed() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    skill_inserted, skill_updated = await _seed_skills()
    (
        puzzle_inserted,
        puzzle_updated,
        variant_inserted,
        variant_updated,
    ) = await _seed_puzzles_and_variants()

    print(
        "Seed complete: "
        f"skills inserted={skill_inserted}, updated={skill_updated}; "
        f"puzzles inserted={puzzle_inserted}, updated={puzzle_updated}; "
        f"variants inserted={variant_inserted}, updated={variant_updated}."
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

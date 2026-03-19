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

        interaction = variant.get("interaction")
        if interaction is not None:
            _validate_interaction_metadata(
                interaction=interaction,
                source=source,
                tier=tier,
            )


def _require_keys(
    data: dict[str, Any],
    *,
    required: set[str],
    source: str,
    context: str,
) -> None:
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"{source}: {context} missing keys: {sorted(missing)}")


def _reject_unknown_keys(
    data: dict[str, Any],
    *,
    allowed: set[str],
    source: str,
    context: str,
) -> None:
    extras = set(data.keys()) - allowed
    if extras:
        raise ValueError(f"{source}: {context} has unsupported keys: {sorted(extras)}")


def _validate_norm_number(
    value: Any,
    *,
    source: str,
    context: str,
    allow_zero: bool,
) -> None:
    if not isinstance(value, (int, float)):
        raise ValueError(f"{source}: {context} must be a number")
    if value < 0 or value > 1:
        raise ValueError(f"{source}: {context} must be in [0, 1]")
    if not allow_zero and value == 0:
        raise ValueError(f"{source}: {context} must be > 0")


def _validate_interaction_metadata(
    *,
    interaction: Any,
    source: str,
    tier: str,
) -> None:
    ctx = f"tier '{tier}' interaction"

    if not isinstance(interaction, dict):
        raise ValueError(f"{source}: {ctx} must be an object")

    allowed_top = {
        "interaction_version",
        "scene",
        "hotspots",
        "prompts",
        "ui_hints",
    }
    _require_keys(
        interaction,
        required={"interaction_version", "scene", "hotspots", "prompts"},
        source=source,
        context=ctx,
    )
    _reject_unknown_keys(
        interaction,
        allowed=allowed_top,
        source=source,
        context=ctx,
    )

    if interaction["interaction_version"] != 1:
        raise ValueError(f"{source}: {ctx} interaction_version must be 1")

    scene = interaction["scene"]
    if not isinstance(scene, dict):
        raise ValueError(f"{source}: {ctx}.scene must be an object")
    _require_keys(
        scene,
        required={"scene_id", "asset_key"},
        source=source,
        context=f"{ctx}.scene",
    )
    _reject_unknown_keys(
        scene,
        allowed={"scene_id", "asset_key", "instruction_text"},
        source=source,
        context=f"{ctx}.scene",
    )
    if not isinstance(scene["scene_id"], str) or not scene["scene_id"].strip():
        raise ValueError(f"{source}: {ctx}.scene.scene_id must be a non-empty string")
    if not isinstance(scene["asset_key"], str) or not scene["asset_key"].strip():
        raise ValueError(f"{source}: {ctx}.scene.asset_key must be a non-empty string")

    hotspots = interaction["hotspots"]
    if not isinstance(hotspots, list):
        raise ValueError(f"{source}: {ctx}.hotspots must be a list")
    prompt_hotspot_refs: list[str] = []
    for idx, hotspot in enumerate(hotspots):
        hotspot_ctx = f"{ctx}.hotspots[{idx}]"
        if not isinstance(hotspot, dict):
            raise ValueError(f"{source}: {hotspot_ctx} must be an object")
        _require_keys(
            hotspot,
            required={"hotspot_id", "shape_type", "shape", "trigger"},
            source=source,
            context=hotspot_ctx,
        )
        _reject_unknown_keys(
            hotspot,
            allowed={"hotspot_id", "label", "shape_type", "shape", "trigger"},
            source=source,
            context=hotspot_ctx,
        )
        if not isinstance(hotspot["hotspot_id"], str) or not hotspot["hotspot_id"].strip():
            raise ValueError(f"{source}: {hotspot_ctx}.hotspot_id must be a non-empty string")

        if hotspot["shape_type"] != "rect":
            raise ValueError(f"{source}: {hotspot_ctx}.shape_type must be 'rect'")

        shape = hotspot["shape"]
        if not isinstance(shape, dict):
            raise ValueError(f"{source}: {hotspot_ctx}.shape must be an object")
        _require_keys(
            shape,
            required={"x", "y", "width", "height"},
            source=source,
            context=f"{hotspot_ctx}.shape",
        )
        _reject_unknown_keys(
            shape,
            allowed={"x", "y", "width", "height"},
            source=source,
            context=f"{hotspot_ctx}.shape",
        )
        _validate_norm_number(shape["x"], source=source, context=f"{hotspot_ctx}.shape.x", allow_zero=True)
        _validate_norm_number(shape["y"], source=source, context=f"{hotspot_ctx}.shape.y", allow_zero=True)
        _validate_norm_number(shape["width"], source=source, context=f"{hotspot_ctx}.shape.width", allow_zero=False)
        _validate_norm_number(shape["height"], source=source, context=f"{hotspot_ctx}.shape.height", allow_zero=False)

        trigger = hotspot["trigger"]
        if not isinstance(trigger, dict):
            raise ValueError(f"{source}: {hotspot_ctx}.trigger must be an object")
        _require_keys(
            trigger,
            required={"trigger_type"},
            source=source,
            context=f"{hotspot_ctx}.trigger",
        )
        _reject_unknown_keys(
            trigger,
            allowed={"trigger_type", "prompt_ref"},
            source=source,
            context=f"{hotspot_ctx}.trigger",
        )
        if trigger["trigger_type"] != "click":
            raise ValueError(f"{source}: {hotspot_ctx}.trigger.trigger_type must be 'click'")

        if "prompt_ref" in trigger and trigger["prompt_ref"] is not None:
            prompt_ref = trigger["prompt_ref"]
            if not isinstance(prompt_ref, str) or not prompt_ref.strip():
                raise ValueError(f"{source}: {hotspot_ctx}.trigger.prompt_ref must be a non-empty string when provided")
            prompt_hotspot_refs.append(prompt_ref)

    prompts = interaction["prompts"]
    if not isinstance(prompts, dict):
        raise ValueError(f"{source}: {ctx}.prompts must be an object")
    if not prompts:
        raise ValueError(f"{source}: {ctx}.prompts must not be empty")

    if len(prompt_hotspot_refs) != 1:
        raise ValueError(f"{source}: {ctx} must have exactly one hotspot with trigger.prompt_ref")

    for prompt_ref in prompt_hotspot_refs:
        if prompt_ref not in prompts:
            raise ValueError(f"{source}: {ctx}.prompts missing key referenced by prompt_ref='{prompt_ref}'")

    for prompt_ref, prompt in prompts.items():
        prompt_ctx = f"{ctx}.prompts['{prompt_ref}']"
        if not isinstance(prompt, dict):
            raise ValueError(f"{source}: {prompt_ctx} must be an object")
        _require_keys(
            prompt,
            required={"prompt_text", "answer_type", "correct_answers"},
            source=source,
            context=prompt_ctx,
        )
        _reject_unknown_keys(
            prompt,
            allowed={"prompt_text", "answer_type", "correct_answers", "max_attempt_chars"},
            source=source,
            context=prompt_ctx,
        )
        if prompt["answer_type"] != "text":
            raise ValueError(f"{source}: {prompt_ctx}.answer_type must be 'text'")
        if not isinstance(prompt["prompt_text"], str) or not prompt["prompt_text"].strip():
            raise ValueError(f"{source}: {prompt_ctx}.prompt_text must be a non-empty string")
        prompt_answers = prompt["correct_answers"]
        if not isinstance(prompt_answers, list) or not prompt_answers:
            raise ValueError(f"{source}: {prompt_ctx}.correct_answers must be a non-empty list")
        if any(not isinstance(ans, str) or not ans.strip() for ans in prompt_answers):
            raise ValueError(f"{source}: {prompt_ctx}.correct_answers must contain non-empty strings")

    forbidden_keys = {
        "script",
        "scripts",
        "condition",
        "conditions",
        "state_machine",
        "states",
        "transitions",
        "rules",
        "actions",
    }

    def _scan_forbidden(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in forbidden_keys:
                    raise ValueError(f"{source}: {ctx} contains forbidden key '{key}' at {path}")
                _scan_forbidden(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                _scan_forbidden(child, f"{path}[{idx}]")

    _scan_forbidden(interaction, f"{ctx}")


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
            interaction = variant.pop("interaction", None)
            variant_metadata = {
                "answer_type": variant["answer_type"],
                "hints": variant["hints"],
                "mechanic": doc["mechanic"],
                "source_file": doc["__source_file"],
            }
            if interaction is not None:
                variant_metadata["interaction"] = interaction

            variants.append(
                {
                    "id": f"{puzzle_id}__{tier}",
                    "puzzle_id": puzzle_id,
                    "difficulty_tier": tier,
                    "prompt_text": variant["prompt_text"],
                    "correct_answers": variant["correct_answers"],
                    "audio_url": variant["audio_url"],
                    "time_limit_sec": variant["time_limit_sec"],
                    "metadata": variant_metadata,
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

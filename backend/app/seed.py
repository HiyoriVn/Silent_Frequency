"""
Silent Frequency — Database Seed Script

Populates skills, puzzles, and puzzle_variants with demo content.
Run with:  python -m backend.app.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

PUZZLES = [
    # Room 1 — start_room
    {"id": "start_vocab_sign",     "skill_id": 1, "room": "start_room",  "title": "Translate the warning sign",         "base_difficulty": 1, "max_hints": 2, "order_in_room": 1, "is_required": True},
    {"id": "start_grammar_door",   "skill_id": 2, "room": "start_room",  "title": "Fix the sentence to unlock door",    "base_difficulty": 2, "max_hints": 2, "order_in_room": 2, "is_required": True},
    {"id": "start_listen_code",    "skill_id": 3, "room": "start_room",  "title": "Listen and enter the access code",   "base_difficulty": 1, "max_hints": 2, "order_in_room": 3, "is_required": True},
    # Room 2 — radio_room
    {"id": "radio_vocab_decode",   "skill_id": 1, "room": "radio_room",  "title": "Decode the radio frequency label",   "base_difficulty": 2, "max_hints": 2, "order_in_room": 1, "is_required": True},
    {"id": "radio_grammar_msg",    "skill_id": 2, "room": "radio_room",  "title": "Reconstruct the intercepted message","base_difficulty": 2, "max_hints": 2, "order_in_room": 2, "is_required": True},
    {"id": "radio_listen_freq",    "skill_id": 3, "room": "radio_room",  "title": "Identify the correct frequency",     "base_difficulty": 2, "max_hints": 2, "order_in_room": 3, "is_required": True},
    # Room 3 — lab_room
    {"id": "lab_vocab_chemical",   "skill_id": 1, "room": "lab_room",    "title": "Name the chemical compounds",        "base_difficulty": 3, "max_hints": 2, "order_in_room": 1, "is_required": True},
    {"id": "lab_grammar_report",   "skill_id": 2, "room": "lab_room",    "title": "Complete the research report",       "base_difficulty": 3, "max_hints": 2, "order_in_room": 2, "is_required": True},
    {"id": "lab_listen_alarm",     "skill_id": 3, "room": "lab_room",    "title": "Interpret the alarm announcement",   "base_difficulty": 3, "max_hints": 2, "order_in_room": 3, "is_required": True},
]

# Generate 3 variants (low/mid/high) per puzzle
VARIANTS = []

_VARIANT_TEMPLATES = {
    # ── start_vocab_sign ──
    "start_vocab_sign": {
        "low":  {"prompt": "What does 'Danger' mean in Vietnamese?",                                "answers": ["nguy hiểm"]},
        "mid":  {"prompt": "Translate: 'Authorized personnel only'",                                "answers": ["chỉ nhân viên được phép", "chỉ người được ủy quyền"]},
        "high": {"prompt": "Translate: 'Caution: biohazard material beyond this point'",            "answers": ["cẩn thận: vật liệu nguy hiểm sinh học phía trước"]},
    },
    "start_grammar_door": {
        "low":  {"prompt": "Choose the correct word: 'She ___ (go/goes) to the lab every day.'",    "answers": ["goes"]},
        "mid":  {"prompt": "Fix the sentence: 'The researchers has found a new signal.'",           "answers": ["the researchers have found a new signal"]},
        "high": {"prompt": "Fix: 'Neither the signal nor the frequency were been identified yet.'", "answers": ["neither the signal nor the frequency has been identified yet"]},
    },
    "start_listen_code": {
        "low":  {"prompt": "Listen and type the 3-digit code you hear.",                            "answers": ["472"]},
        "mid":  {"prompt": "Listen and type the 5-digit code you hear.",                            "answers": ["47239"]},
        "high": {"prompt": "Listen to the sequence and type it in reverse order.",                  "answers": ["93274"]},
    },
    "radio_vocab_decode": {
        "low":  {"prompt": "What does 'fréquence' mean?",                                          "answers": ["frequency"]},
        "mid":  {"prompt": "Translate: 'Réglez la fréquence silencieuse'",                          "answers": ["tune the silent frequency", "set the silent frequency"]},
        "high": {"prompt": "Translate: 'La fréquence silencieuse ne répond plus depuis minuit'",    "answers": ["the silent frequency has not responded since midnight"]},
    },
    "radio_grammar_msg": {
        "low":  {"prompt": "Choose: 'The message ___ (was/were) intercepted.'",                     "answers": ["was"]},
        "mid":  {"prompt": "Reorder: 'intercepted / was / last night / the transmission'",          "answers": ["the transmission was intercepted last night"]},
        "high": {"prompt": "Fix: 'The signal, along with its echoes, have been lost for hours.'",   "answers": ["the signal, along with its echoes, has been lost for hours"]},
    },
    "radio_listen_freq": {
        "low":  {"prompt": "Listen: what frequency number is mentioned?",                           "answers": ["91.7"]},
        "mid":  {"prompt": "Listen: what frequency and time are mentioned?",                        "answers": ["91.7 at midnight", "91.7, midnight"]},
        "high": {"prompt": "Listen and summarise the full broadcast instruction.",                   "answers": ["tune to 91.7 at midnight and wait for the silent frequency"]},
    },
    "lab_vocab_chemical": {
        "low":  {"prompt": "What is H2O?",                                                          "answers": ["water"]},
        "mid":  {"prompt": "Translate the label: 'sodium chloride solution'",                       "answers": ["dung dịch natri clorua", "dung dịch muối"]},
        "high": {"prompt": "Translate: 'diluted hydrochloric acid reagent grade'",                  "answers": ["axit clohidric loãng cấp thuốc thử"]},
    },
    "lab_grammar_report": {
        "low":  {"prompt": "Choose: 'The sample ___ (is/are) contaminated.'",                       "answers": ["is"]},
        "mid":  {"prompt": "Fix: 'Each of the samples have been tested twice.'",                    "answers": ["each of the samples has been tested twice"]},
        "high": {"prompt": "Fix: 'The data suggests that neither compound are stable under heat.'", "answers": ["the data suggest that neither compound is stable under heat"]},
    },
    "lab_listen_alarm": {
        "low":  {"prompt": "Listen: which room number is announced?",                               "answers": ["room 7", "7"]},
        "mid":  {"prompt": "Listen: what is the evacuation instruction?",                           "answers": ["evacuate room 7 immediately"]},
        "high": {"prompt": "Listen and write the full emergency protocol announcement.",             "answers": ["attention all personnel: evacuate room 7 immediately due to chemical spill, proceed to assembly point b"]},
    },
}

for puzzle_id, tiers in _VARIANT_TEMPLATES.items():
    for tier, content in tiers.items():
        VARIANTS.append({
            "id": f"{puzzle_id}__{tier}",
            "puzzle_id": puzzle_id,
            "difficulty_tier": tier,
            "prompt_text": content["prompt"],
            "correct_answers": content["answers"],
            "audio_url": None,
            "time_limit_sec": None,
            "metadata": {},
        })


# ──────────────────────────────────────
# Seed runner
# ──────────────────────────────────────

async def seed() -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        # Skip if already seeded
        result = await db.execute(select(Skill))
        if result.scalars().first() is not None:
            print("Database already seeded — skipping.")
            return

        # Skills
        for s in SKILLS:
            db.add(Skill(**s))
        await db.flush()

        # Puzzles
        for p in PUZZLES:
            db.add(Puzzle(**p))
        await db.flush()

        # Variants
        for v in VARIANTS:
            db.add(PuzzleVariant(
                id=v["id"],
                puzzle_id=v["puzzle_id"],
                difficulty_tier=v["difficulty_tier"],
                prompt_text=v["prompt_text"],
                correct_answers=v["correct_answers"],
                audio_url=v["audio_url"],
                time_limit_sec=v["time_limit_sec"],
            ))

        await db.commit()
        print(f"Seeded: {len(SKILLS)} skills, {len(PUZZLES)} puzzles, {len(VARIANTS)} variants.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())

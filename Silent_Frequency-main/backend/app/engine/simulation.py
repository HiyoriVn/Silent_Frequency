"""
Silent Frequency — BKT Simulation Demo

Runs a 3-attempt scenario for each skill to show how mastery evolves.
Execute directly:  python -m backend.app.engine.simulation
"""

from backend.app.engine.bkt_params import SkillParams, SkillState
from backend.app.engine.bkt_core import update_mastery


# ── Default parameters (match the schema design) ──
SKILLS = {
    "vocabulary": SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.25, p_slip=0.10),
    "grammar":    SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.25, p_slip=0.10),
    "listening":  SkillParams(p_init=0.10, p_learn=0.20, p_guess=0.25, p_slip=0.10),
}

# ── Simulated attempt sequences ──
#   True = correct, False = incorrect
SCENARIOS: dict[str, list[bool]] = {
    "vocabulary": [True, True, True],       # strong learner
    "grammar":    [False, True, True],      # slow start then learns
    "listening":  [False, False, True],     # struggles then gets it
}


def run_simulation() -> None:
    print("=" * 72)
    print("  BKT Simulation — 3 attempts per skill")
    print("=" * 72)

    for skill_name, responses in SCENARIOS.items():
        params = SKILLS[skill_name]
        state = SkillState.from_params(params)

        print(f"\n── {skill_name.upper()} ──")
        print(f"  Initial P(L₀) = {state.p_learned:.4f}")
        print(f"  Params: P(T)={params.p_learn}, P(G)={params.p_guess}, P(S)={params.p_slip}")
        print()

        for i, correct in enumerate(responses, start=1):
            result = update_mastery(state, params, is_correct=correct)

            print(f"  Attempt {i}: {'✓ correct' if correct else '✗ incorrect'}")
            print(f"    P(Lₙ) before     = {result.p_learned_before:.4f}")
            print(f"    P(Lₙ|obs)        = {result.posterior_given_obs:.4f}")
            print(f"    P(Lₙ₊₁) after    = {result.p_learned_after:.4f}")
            print(f"    Recommended tier  = {result.recommended_tier}")
            print()

        print(f"  Final mastery: {state.p_learned:.4f}  (updates: {state.update_count})")

    print("=" * 72)


if __name__ == "__main__":
    run_simulation()

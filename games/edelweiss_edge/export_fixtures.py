"""Exports a few rounds of every bet mode into one JSON file for the game repo's demo and tests.

    env/bin/python games/edelweiss_edge/export_fixtures.py ../edelweiss-edge/fixtures/books.json

First pass: the rounds are simulated here (PER_KIND losses and wins per mode), not read from run.py's
published files, and each kind's share is its exact odds (the stop weights, climb.py).
"""

import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from climb import BASE_METRES, CLIMBS, MAX_CLIMB, METRES_PER_STEP, RESCUED, STOP_WEIGHTS, TOP, win_odds
from game_config import GameConfig
from gamestate import GameState
from src.wins.win_manager import WinManager

PER_KIND = 3
CONFIG = GameConfig()
CAP = round(CONFIG.wincap * 100)


def simulate(mode: str, criteria: str, sims: int, first: int = 0) -> list[dict]:
    """Books for one bet mode and outcome group, the way the SDK's run_sims makes them (seeded by sim
    number: `first` gives each mode its own sims, so modes don't all show the same climbs)."""
    state = GameState(CONFIG)
    state.win_manager = WinManager(CONFIG.basegame_type, CONFIG.freegame_type, CONFIG.wincap)
    state.library, state.recorded_events = {}, {}
    state.betmode, state.criteria = mode, criteria
    for sim in range(first, first + sims):
        state.run_spin(sim)
    return list(state.library.values())


def kinds(mode: dict) -> dict:
    """Each kind of round's share of the mode (its exact odds)."""
    wins = win_odds(mode["window"], mode["pay"], CONFIG.rules, CONFIG.wincap)
    shares = {"loss": wins[0], "win": sum(p for w, p in wins.items() if 0 < w < CAP), "max win": wins[CAP]}
    return {k: v for k, v in shares.items() if v > 0}


def version() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "uncommitted"


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "books.json"
    rules = CONFIG.rules
    data = {
        "source": {"repo": "mawint/edelweiss-edge-math", "version": version(), "exported": datetime.date.today().isoformat()},
        "rules": {
            "top": TOP, "climbs": CLIMBS, "maxClimb": MAX_CLIMB, "baseMetres": BASE_METRES, "metresPerStep": METRES_PER_STEP,
            "stopWeights": {str(k): w for k, w in STOP_WEIGHTS.items()}, "rescued": RESCUED,
            "bloomBonus": rules.bloom_bonus, "goldenMult": rules.golden_mult, "maxWin": CONFIG.wincap,
        },
        "modes": {},
        "books": [],
    }
    for number, (name, mode) in enumerate(CONFIG.windows.items()):
        shares = kinds(mode)
        data["modes"][name] = {
            "cost": 1.0, "rtp": CONFIG.rtp, "maxWin": CONFIG.wincap, "difficulty": mode["difficulty"],
            "window": mode["window"] if mode["window"] == "edge" else list(mode["window"]), "pay": mode["pay"],
            "kinds": shares,
        }
        books = [(kind, book) for kind, criteria in (("loss", "0"), ("win", "win")) for book in simulate(name, criteria, PER_KIND, number * PER_KIND)]
        # (each group's sims are numbered from 1: renumbered so a mode's ids are unique, for replays)
        for book_id, (kind, book) in enumerate(books, start=1):
            data["books"].append({"id": book_id, "mode": name, "kind": kind, "payoutMultiplier": book["payoutMultiplier"], "events": book["events"]})
    with open(out, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")
    print(f"wrote {len(data['books'])} books for {len(data['modes'])} modes to {out}")

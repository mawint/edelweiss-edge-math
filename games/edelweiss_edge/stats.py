"""Per-mode numbers from the exact odds (no run needed): what each window pays, how often it wins, the RTP
its quoted pay returns before the optimizer and its biggest win; and how often each feature comes up.

    env/bin/python games/edelweiss_edge/stats.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from climb import RESCUED, STOP_WEIGHTS, mean_multiplier, win_odds
from game_config import GameConfig

CONFIG = GameConfig()


def mode_stats(name: str) -> dict:
    mode = CONFIG.windows[name]
    wins = win_odds(mode["window"], mode["pay"], CONFIG.rules, CONFIG.wincap)
    return {
        "pay": mode["pay"],
        "hit": 1 - wins[0],
        "rtp": sum(w / 100 * p for w, p in wins.items()),
        "max": max(w for w, p in wins.items() if p > 0) / 100,
    }


if __name__ == "__main__":
    stories = CONFIG.stories
    falls = STOP_WEIGHTS["edge"] + RESCUED
    print("features, 1 in N rounds:", ", ".join(f"{k} {1 / v:.2f}" for k, v in stories.frequency.items()),
          f"| falls shown 1 in {100_000 / falls:.1f}, rescued 1 in {falls / RESCUED:.1f} of them")
    print("draw rates:", ", ".join(f"{k} {v:.4f}" for k, v in stories.rates.items()), f"| E[multiplier] {mean_multiplier(CONFIG.rules)}")
    print(f"{len(CONFIG.windows)} modes\n{'mode':<12} {'pay':>7} {'1 in':>8} {'RTP':>8} {'max':>8}")
    for name in CONFIG.windows:
        s = mode_stats(name)
        print(f"{name:<12} {s['pay']:>7.1f} {1 / s['hit']:>8.1f} {s['rtp']:>8.2%} {s['max']:>8.1f}")

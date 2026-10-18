"""Every book must be internally consistent: the game plays its events back and pays finalWin, so what it
shows on the way has to add up to exactly that. Books are generated in-process, a few per mode and outcome
group, so the tests don't depend on a previous run.py."""

import random
from collections import Counter

import pytest

from climb import stop_odds

from game_config import GameConfig
from gamestate import GameState
from src.wins.win_manager import WinManager

SIMS_PER_GROUP = 8
CONFIG = GameConfig()
CAP = round(CONFIG.wincap * 100)


def simulate(mode: str, criteria: str, sims: int = SIMS_PER_GROUP) -> list[dict]:
    """Books for one bet mode and outcome group, the way the SDK's run_sims makes them."""
    state = GameState(CONFIG)
    state.win_manager = WinManager(CONFIG.basegame_type, CONFIG.freegame_type, CONFIG.wincap)
    state.library, state.recorded_events = {}, {}
    state.betmode, state.criteria = mode, criteria
    for sim in range(sims):
        state.run_spin(sim)
    return list(state.library.values())


GROUPS = [(m.get_name(), d.get_criteria()) for m in CONFIG.bet_modes for d in m.get_distributions()]


@pytest.mark.parametrize("mode,criteria", GROUPS)
def test_books_add_up(mode, criteria):
    window = CONFIG.windows[mode]["window"]
    for book in simulate(mode, criteria):
        events = book["events"]
        assert [e["index"] for e in events] == list(range(len(events)))
        reveal, final = events[0], events[-1]
        (settle,) = [e for e in events if e["type"] == "settle"]
        assert reveal["type"] == "reveal" and final["type"] == "finalWin"
        assert reveal["pay"] == round(CONFIG.windows[mode]["pay"] * 100)

        # three climbs of 0-9 from base camp; every move lands where the next starts; blooms only on steps reached
        pos, high, climbs, fell, rescued, mult, path = 0, 0, 0, None, False, 100, []
        for e in events[1 : events.index(settle)]:
            if e["type"] == "climb":
                climbs += 1
                assert e["n"] == climbs and 0 <= e["steps"] <= 9 and e["to"] == pos + e["steps"]
                pos = e["to"]
            elif e["type"] == "feature" and e["kind"] == "rescue":
                assert fell is not None and e["to"] == 25
                pos, rescued = 25, True
            elif e["type"] == "feature":
                assert fell is None and e["kind"] in ("gondola", "avalanche", "echo", "foehn")
                pos = e["to"]
            elif e["type"] == "bloom":
                assert 0 <= e["step"] <= high and e["multiplier"] > mult
                mult = e["multiplier"]
            else:
                assert e["type"] == "fall" and e["step"] == pos > 25
                fell = pos
            if e["type"] in ("climb", "feature") and not rescued:
                path.append(pos)
            assert pos >= 0
            high = max(high, min(pos, 25))
        assert climbs == 3
        # on the ridge he never passes 25; a fall crosses it on the story's last move
        assert max(path[:-1]) <= 25 and (path[-1] > 25) == (fell is not None)
        assert settle["step"] == pos and settle["multiplier"] == mult
        assert all(e["step"] <= (25 if fell else pos) for e in events if e["type"] == "bloom")  # on the way to his stop

        won = (fell is not None and not rescued) if window == "edge" else (fell is None or rescued) and window[0] <= pos <= window[1]
        assert settle["inWindow"] == won
        expected = min(int(reveal["pay"] * settle["multiplier"] / 100 // 10 * 10), CAP) if won else 0
        assert settle["win"] == expected == final["amount"] == book["payoutMultiplier"]
        assert {"0": expected == 0, "win": 0 < expected < CAP, "wincap": expected == CAP}[criteria]


def test_dealt_rounds_match_the_odds():
    """Rounds dealt from every stop in its true proportion: features, falls, rescues and blooms come up
    at their rates."""
    random.seed(7)
    state = GameState(CONFIG)
    state.betmode, state.criteria = "edge", "0"
    stops = stop_odds()
    n = 40_000
    seen, stops_seen, blooms, golden, yodels = Counter(), Counter(), 0, 0, 0
    for _ in range(n):
        stop = random.choices(list(stops), weights=list(stops.values()))[0]
        plan = state.deal(stop)
        stops_seen[stop] += 1
        seen.update({e.get("kind", e["type"]) for e in plan["events"] if e["type"] in ("feature", "fall")})
        blooms += sum(not b["golden"] for b in plan["blooms"])
        golden += any(b["golden"] for b in plan["blooms"])
        zeros = sum(e["type"] == "climb" and e["steps"] == 0 for e in plan["events"])
        assert zeros <= 1  # one yodel a round at most
        yodels += zeros
    for feature, rate in {"gondola": 1 / 9, "avalanche": 1 / 10, "echo": 1 / 14, "foehn": 1 / 7}.items():
        assert seen[feature] / n == pytest.approx(rate, rel=0.08), feature
    assert seen["rescue"] / seen["fall"] == pytest.approx(1 / 5, abs=0.05)
    assert blooms / n == pytest.approx(0.5, rel=0.05)  # 1/6 one bloom + 1/6 two
    assert golden / n == pytest.approx(1 / 400, rel=0.4)
    assert yodels / n == pytest.approx(1 - 0.9**3, rel=0.05)

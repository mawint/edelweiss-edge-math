"""Deals a round: where Ueli stops (drawn first, from the stop weights), the story that reaches it (three
climbs and the features), the blooms on the way, and what it pays. Pure planning: nothing is paid here
(gamestate.py plays the plan into book events and pays it).

All randomness goes through `random`, which the SDK seeds per simulation, so every book is reproducible.
"""

import random

from climb import EDGE, RESCUE, TOP, hit, stop_odds, win_hundredths
from src.executables.executables import Executables


def weighted(table: dict):
    """A key of `table`, picked in proportion to its weight."""
    return random.choices(list(table), weights=list(table.values()))[0]


class GameCalculations(Executables):
    """Round planning for the current bet mode and criteria."""

    @property
    def mode(self) -> dict:
        """The current bet mode's difficulty, window and pay (game_config.windows)."""
        return self.config.windows[self.betmode]

    def plan_round(self) -> dict:
        """A round that fits the current criteria: a loss ("0"), a win under the cap ("win") or the cap.
        The stop is drawn among the stops that lose or win (in their true proportions; the optimizer sets
        how often each group comes up). The cap's rounds start with the golden bloom and two others."""
        cap = round(self.config.wincap * 100)
        wins = not self.in_criteria("0")
        stops = {s: p for s, p in stop_odds().items() if hit(s, self.mode["window"]) == wins}
        while True:
            plan = self.deal(weighted(stops), force_blooms=self.in_criteria("wincap"))
            if not wins or (plan["win"] == cap) == self.in_criteria("wincap"):
                return plan

    def deal(self, stop, force_blooms: bool = False) -> dict:
        """The round for a drawn stop: its story, the blooms collected on the way, and what it pays."""
        story = self.story(stop)
        blooms = self.place_blooms(TOP if stop in (EDGE, RESCUE) else stop, force_blooms)
        events = self.with_blooms(story, blooms)
        if stop in (EDGE, RESCUE):
            events.append({"type": "fall", "step": story[-1][2]})
        if stop == RESCUE:
            events.append({"type": "feature", "kind": "rescue", "to": TOP})
        rules = self.config.rules
        mult = 1 + rules.bloom_bonus * sum(not b["golden"] for b in blooms)
        if any(b["golden"] for b in blooms):
            mult *= rules.golden_mult
        won = hit(stop, self.mode["window"])
        win = win_hundredths(self.mode["pay"], mult, self.config.wincap) if won else 0
        step = story[-1][2] if stop == EDGE else (TOP if stop == RESCUE else stop)
        return {"stop": stop, "step": step, "events": events, "blooms": blooms, "mult": mult, "won": won, "win": win}

    def story(self, stop) -> tuple:
        """How the round reaches `stop`: a feature set (by its calibrated odds for this stop), then one of
        its stories, evenly. Each move is (kind, steps, to)."""
        stories = self.config.stories
        feature_set = weighted(stories.odds[stop])
        return random.choice(stories.candidates(feature_set, stop))

    def place_blooms(self, top: int, force: bool) -> list[dict]:
        """The round's blooms, each on a step 0..`top` he passes (two may share a step); the golden one,
        when there is one, is listed last."""
        rules = self.config.rules
        normal = max(rules.blooms) if force else weighted(rules.blooms)
        golden = force or random.random() < rules.golden
        return [{"step": random.randint(0, top), "golden": golden and i == normal} for i in range(normal + golden)]

    def with_blooms(self, story: tuple, blooms: list[dict]) -> list[dict]:
        """The story's moves as events, each bloom collected (a bloom event) the first time he reaches its
        step: a bloom on base camp as he sets off, the others after the move that gets him there."""
        rules = self.config.rules
        events, left = [], sorted(blooms, key=lambda b: b["step"])
        normal, golden = 0, False

        def collect(reached: int) -> None:
            nonlocal left, normal, golden
            for b in [b for b in left if b["step"] <= reached]:
                golden = golden or b["golden"]
                normal += not b["golden"]
                mult = (1 + rules.bloom_bonus * normal) * (rules.golden_mult if golden else 1)
                events.append({"type": "bloom", "step": b["step"], "golden": b["golden"], "multiplier": round(mult * 100)})
            left = [b for b in left if b["step"] > reached]

        collect(0)
        climbs, high = 0, 0
        for kind, steps, to in story:
            if kind == "climb":
                climbs += 1
                events.append({"type": "climb", "n": climbs, "steps": steps, "to": to})
            else:
                events.append({"type": "feature", "kind": kind, "to": to})
            high = max(high, to)
            collect(high)
        return events

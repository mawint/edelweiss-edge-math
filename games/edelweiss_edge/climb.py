"""The climb and its exact odds, with no SDK in it: game_config.py prices every bet mode from these, the
tests check them, and game_calculations.py deals rounds from them.

A round is decided first and acted out second:

1. Where Ueli stops is drawn from fixed integer weights out of 100,000 (STOP_WEIGHTS): step k (0..25) has
   7134 - 264k, so the higher the step the rarer, and over the edge has 316. Of step 25's weight, RESCUED
   is told as a fall and Barry's Rescue (1 in 5 of the falls shown).
2. A story reaches that stop: three climbs of 0-9 steps (at most one of them 0: one yodel a round) and
   the features (Stories). Features never change the odds; they're only how the round is shown. Low
   stops are told as "climbed, then knocked back" (an avalanche, or the wind at the end).
3. Edelweiss blooms are independent of the stop: 0, 1 or 2 blooms (+0.5x each) and, 1 round in 400, a
   Golden Edelweiss (x10), placed on steps he passes on the way to his stop and all collected. So every
   round's multiplier has the same distribution, E = 1.25 x 1.0225 = 1.278125.

A window pays RTP / (P(window) x E[multiplier]), quoted down to a 0.10x step.
"""

import math
import random
from collections import Counter
from dataclasses import dataclass

import numpy as np

TOP = 25  # the top station; past it he goes over the edge
BASE_METRES = 2200
METRES_PER_STEP = 32
CLIMBS = 3
MAX_CLIMB = 9
EDGE = "edge"  # a stop: over the edge, and not rescued
RESCUE = "rescue"  # a stop on step 25, told as a fall and Barry's Rescue
TOTAL_WEIGHT = 100_000
STOP_WEIGHTS = {k: 7134 - 264 * k for k in range(TOP + 1)} | {EDGE: 316}
RESCUED = STOP_WEIGHTS[EDGE] // 4  # of step 25's weight: 1 in 5 shown falls is rescued
FEATURES = ("gondola", "avalanche", "echo", "foehn")
# How often a round has a yodel (a climb of 0), as with three fair 0-9 climbs: 1 - 0.9^3
YODEL_SHARE = 1 - 0.9**3


@dataclass(frozen=True)
class Rules:
    """Feature rates are target frequencies per round; bloom odds per round."""

    gondola: float  # +lift after climb 1 or 2 (half each)
    gondola_lift: tuple[int, int]
    avalanche: float  # -drop after climb 2 or 3 (half each), only when he's above `avalanche_above`
    avalanche_above: int
    avalanche_min_drop: int  # it drops him this far at least, and up to all the way back to base camp
    echo: float  # the last climb again
    foehn: float  # a drift either way, last
    foehn_drift: tuple[int, int]
    blooms: dict  # normal blooms placed -> probability
    bloom_bonus: float
    golden: float
    golden_mult: int


def stop_odds() -> dict:
    """Each stop (0..25, RESCUE, EDGE) -> its probability. A rescue ends on step 25."""
    odds = {stop: weight / TOTAL_WEIGHT for stop, weight in STOP_WEIGHTS.items()}
    odds[TOP] -= RESCUED / TOTAL_WEIGHT
    odds[RESCUE] = RESCUED / TOTAL_WEIGHT
    return odds


def final_step(stop):
    """Where a stop leaves him for the bet: step 25 after a rescue, EDGE after a real fall."""
    return TOP if stop == RESCUE else stop


def hit(stop, window) -> bool:
    """Whether a stop wins a bet on `window` ((lo, hi) steps, or EDGE)."""
    final = final_step(stop)
    if window == EDGE:
        return final == EDGE
    return final != EDGE and window[0] <= final <= window[1]


def window_odds(window) -> float:
    """P(a bet on `window` wins)."""
    if window == EDGE:
        return STOP_WEIGHTS[EDGE] / TOTAL_WEIGHT
    return sum(STOP_WEIGHTS[k] for k in range(window[0], window[1] + 1)) / TOTAL_WEIGHT


def multiplier_odds(rules: Rules) -> dict[float, float]:
    """The win multiplier's distribution (the same in every round): +bloom_bonus per bloom, x golden_mult
    with the golden one. Every placed bloom is collected."""
    odds: Counter = Counter()
    for normal, p in rules.blooms.items():
        odds[1 + rules.bloom_bonus * normal] += p * (1 - rules.golden)
        odds[(1 + rules.bloom_bonus * normal) * rules.golden_mult] += p * rules.golden
    return dict(odds)


def mean_multiplier(rules: Rules) -> float:
    return sum(m * p for m, p in multiplier_odds(rules).items())


def quoted_pay(window, rules: Rules, rtp: float) -> float:
    """What a window pays (x bet) before the multiplier: RTP / (P(window) x E[multiplier]), down to a
    0.10x step (the tiny nudge keeps a pay that is exactly a tenth from dropping a step on float error)."""
    fair = rtp / (window_odds(window) * mean_multiplier(rules))
    return math.floor(fair * 10 + 1e-9) / 10


def win_hundredths(pay: float, mult: float, wincap: float) -> int:
    """A win in hundredths of the bet: pay x multiplier, down to a 0.10x step, capped."""
    raw = round(pay * mult * 100, 6)
    return min(int(raw // 10 * 10), round(wincap * 100))


def win_odds(window, pay: float, rules: Rules, wincap: float) -> Counter:
    """Every win a bet can pay (hundredths) -> its probability (0: a loss)."""
    p_win = window_odds(window)
    wins: Counter = Counter({0: 1 - p_win})
    for mult, q in multiplier_odds(rules).items():
        wins[win_hundredths(pay, mult, wincap)] += p_win * q
    return wins


# ---------- stories: how a round reaches its stop ----------

# A feature set: (gondola, avalanche, echo, foehn). gondola: 0 none / 1 after climb 1 / 2 after climb 2;
# avalanche: 0 none / 1 after climb 2 / 2 after climb 3 (and its echo); echo and foehn: 0 / 1.
FEATURE_SETS = [(g, a, e, f) for g in (0, 1, 2) for a in (0, 1, 2) for e in (0, 1) for f in (0, 1)]
EDGE_CODE = TOP + 1  # (the stop EDGE in the story arrays)


def story_moves(feature_set: tuple, params, rules: Rules) -> list[tuple] | None:
    """A story's moves as (kind, steps, to), kind 'climb' or a feature, from its parameters (climb 1, 2,
    3, lift, drop, drift); None when it breaks a rule:
      - at most one climb of 0 steps (one yodel a round);
      - the avalanche strikes only above `avalanche_above`, and drops him `avalanche_min_drop` steps or
        more, at most back to base camp;
      - the echo repeats a climb of 1 step or more;
      - he is never below step 0.
    The order: climb 1, [gondola], climb 2, [gondola], [avalanche], climb 3, [echo], [avalanche], [foehn]."""
    gondola, avalanche, echo, foehn = feature_set
    c1, c2, c3, lift, drop, drift = (int(v) for v in params)
    if (c1, c2, c3).count(0) > 1:
        return None
    pos, out = 0, []

    def move(kind: str, steps: int) -> None:
        nonlocal pos
        pos += steps
        out.append((kind, steps, pos))

    def knock_back() -> bool:
        if pos <= rules.avalanche_above or not rules.avalanche_min_drop <= drop <= pos:
            return False
        move("avalanche", -drop)
        return True

    move("climb", c1)
    if gondola == 1:
        move("gondola", lift)
    move("climb", c2)
    if gondola == 2:
        move("gondola", lift)
    if avalanche == 1 and not knock_back():
        return None
    move("climb", c3)
    if echo:
        if c3 == 0:
            return None
        move("echo", c3)
    if avalanche == 2 and not knock_back():
        return None
    if foehn:
        move("foehn", drift)
    return None if pos < 0 else out


def ending(story: list[tuple]):
    """The stop a story reaches (0..25 or EDGE), or None when it breaks the edge rules: a story that stays
    on the ridge never goes past 25; one that falls crosses 25 on its very last move."""
    if any(to > TOP for _, _, to in story[:-1]):
        return None
    last = story[-1][2]
    return last if last <= TOP else EDGE


def enumerate_stories(fs: tuple, rules: Rules) -> tuple[np.ndarray, np.ndarray]:
    """Every story with feature set `fs`, as (params, stops): params rows (climb 1, 2, 3, lift, drop,
    drift), stops their stop (EDGE_CODE for a fall). The same rules as story_moves, vectorized over every
    combination (about 2 million stories in all)."""
    gondola, avalanche, echo, foehn = fs
    climbs = np.array([(a, b, c) for a in range(MAX_CLIMB + 1) for b in range(MAX_CLIMB + 1) for c in range(MAX_CLIMB + 1)
                       if (a, b, c).count(0) <= 1])
    lifts = np.arange(rules.gondola_lift[0], rules.gondola_lift[1] + 1) if gondola else np.zeros(1, int)
    most = 2 * MAX_CLIMB + rules.gondola_lift[1] + 2 * MAX_CLIMB  # (the highest he can be when it strikes)
    drops = np.arange(rules.avalanche_min_drop, most + 1) if avalanche else np.zeros(1, int)
    lo, hi = rules.foehn_drift
    drifts = np.array([d for d in range(-hi, hi + 1) if abs(d) >= lo]) if foehn else np.zeros(1, int)
    i = np.indices((len(climbs), len(lifts), len(drops), len(drifts))).reshape(4, -1)
    c, lift, drop, drift = climbs[i[0]], lifts[i[1]], drops[i[2]], drifts[i[3]]
    ok = np.ones(len(lift), bool)
    path = []
    pos = np.zeros(len(lift), int)

    def move(steps):
        nonlocal pos
        pos = pos + steps
        path.append(pos)

    def knock_back():
        nonlocal ok
        ok &= (pos > rules.avalanche_above) & (drop <= pos)
        move(-drop)

    move(c[:, 0])
    if gondola == 1:
        move(lift)
    move(c[:, 1])
    if gondola == 2:
        move(lift)
    if avalanche == 1:
        knock_back()
    move(c[:, 2])
    if echo:
        ok &= c[:, 2] > 0
        move(c[:, 2])
    if avalanche == 2:
        knock_back()
    if foehn:
        move(drift)
    ok &= pos >= 0
    if len(path) > 1:
        ok &= np.max(np.stack(path[:-1]), axis=0) <= TOP
    stops = np.minimum(pos, EDGE_CODE)
    params = np.column_stack([c, lift, drop, drift])[ok].astype(np.int8)
    return params, stops[ok]


class Stories:
    """Every story, by feature set and stop, and how likely each feature set is for each stop.

    A round's feature set is drawn at per-feature rates and redrawn until some story fits its stop, so
    P(set | stop) is p(set) renormalized over the sets that fit. Low stops can't be reached by three climbs
    alone (two of them would have to be 0), so they always come with an avalanche or the wind; the rates are
    calibrated so each feature still comes up at its target across all rounds (as closely as the stops
    allow). A story is then picked among those with its feature set and stop: with a yodel or without
    (weighted so a yodel comes up in YODEL_SHARE of rounds overall: low stops have mostly yodel stories),
    then evenly.
    """

    def __init__(self, rules: Rules):
        self.rules = rules
        # feature set -> (params sorted by stop, then yodel-free first; stop -> (start, first yodel, end) rows)
        self.table: dict[tuple, tuple[np.ndarray, dict]] = {}
        for fs in FEATURE_SETS:
            params, stops = enumerate_stories(fs, rules)
            yodel = (params[:, :3] == 0).any(axis=1)
            order = np.lexsort((yodel, stops))
            params, stops, yodel = params[order], stops[order], yodel[order]
            bounds = {}
            for code in np.unique(stops):
                lo, hi = int(np.searchsorted(stops, code, "left")), int(np.searchsorted(stops, code, "right"))
                bounds[EDGE if code == EDGE_CODE else int(code)] = (lo, lo + int((~yodel[lo:hi]).sum()), hi)
            self.table[fs] = (params, bounds)
        self.rates = self._calibrate()
        self.odds = {stop: self.set_odds(self.rates, stop) for stop in stop_odds()}
        self.frequency = self.feature_frequency(self.rates)
        self.yodel_weight = self._calibrate_yodels()
        self.yodel_share = self.yodels(self.yodel_weight)

    def count(self, fs: tuple, stop) -> int:
        """How many stories with feature set `fs` reach `stop` (a rescue's story is a fall's)."""
        lo, _, hi = self.table[fs][1].get(EDGE if stop == RESCUE else stop, (0, 0, 0))
        return hi - lo

    def story(self, fs: tuple, stop, index: int) -> list[tuple]:
        """Story number `index` (0..count-1) with feature set `fs` reaching `stop`, as moves."""
        params, bounds = self.table[fs]
        lo, _, _ = bounds[EDGE if stop == RESCUE else stop]
        return story_moves(fs, params[lo + index], self.rules)

    def yodel_odds(self, fs: tuple, stop, weight: float) -> float:
        """P(the story has a yodel | feature set, stop): its yodel stories count `weight` times."""
        lo, mid, hi = self.table[fs][1][EDGE if stop == RESCUE else stop]
        with_yodel, without = (hi - mid) * weight, mid - lo
        return with_yodel / (with_yodel + without)

    def pick(self, stop) -> list[tuple]:
        """A story for `stop`: a feature set by its odds for this stop, a yodel or not, then one of those
        stories, evenly."""
        sets = self.odds[stop]
        fs = random.choices(list(sets), weights=list(sets.values()))[0]
        lo, mid, hi = self.table[fs][1][EDGE if stop == RESCUE else stop]
        first, end = (mid, hi) if random.random() < self.yodel_odds(fs, stop, self.yodel_weight) else (lo, mid)
        return self.story(fs, stop, random.randrange(first, end) - lo)

    def yodels(self, weight: float) -> float:
        """How often a round has a yodel, with yodel stories weighted `weight`."""
        return sum(p_stop * p * self.yodel_odds(fs, stop, weight)
                   for stop, p_stop in stop_odds().items() for fs, p in self.odds[stop].items())

    def _calibrate_yodels(self) -> float:
        """The weight on yodel stories that makes a yodel come up in YODEL_SHARE of rounds (bisection: the
        share rises with the weight)."""
        low, high = 1e-6, 1e6
        for _ in range(100):
            mid = (low * high) ** 0.5
            low, high = (mid, high) if self.yodels(mid) < YODEL_SHARE else (low, mid)
        return (low * high) ** 0.5

    def set_odds(self, rates: dict, stop) -> dict[tuple, float]:
        """P(feature set | stop) at per-feature draw `rates`."""
        def p(fs):
            g, a, e, f = fs
            out = 1 - rates["gondola"] if g == 0 else rates["gondola"] / 2
            out *= 1 - rates["avalanche"] if a == 0 else rates["avalanche"] / 2
            out *= rates["echo"] if e else 1 - rates["echo"]
            return out * (rates["foehn"] if f else 1 - rates["foehn"])
        weights = {fs: p(fs) for fs in FEATURE_SETS if self.count(fs, stop)}
        total = sum(weights.values())
        return {fs: w / total for fs, w in weights.items()}

    def feature_frequency(self, rates: dict) -> dict[str, float]:
        """How often each feature comes up across all rounds at per-feature draw `rates`."""
        freq: Counter = Counter({name: 0.0 for name in FEATURES})
        for stop, p_stop in stop_odds().items():
            for fs, p in self.set_odds(rates, stop).items():
                for name, on in zip(FEATURES, fs):
                    freq[name] += p_stop * p * bool(on)
        return dict(freq)

    def targets(self) -> dict[str, float]:
        return {name: getattr(self.rules, name) for name in FEATURES}

    def _calibrate(self, rounds: int = 200) -> dict[str, float]:
        targets = self.targets()
        rates = dict(targets)
        for _ in range(rounds):
            freq = self.feature_frequency(rates)
            rates = {k: min(0.95, rates[k] * targets[k] / freq[k]) for k in rates}
        return rates

"""The climb and its exact odds, with no SDK in it: game_config.py prices every bet mode from these, the
tests check them, and game_calculations.py deals rounds from them.

A round is decided first and acted out second:

1. Where Ueli stops is drawn from fixed integer weights out of 100,000 (STOP_WEIGHTS): step k (0..25) has
   7134 - 264k, so the higher the step the rarer, and over the edge has 316. Of step 25's weight, RESCUED
   is told as a fall and Barry's Rescue (1 in 5 of the falls shown).
2. A story reaches that stop: three climbs of 0-9 steps and the features (Stories). Features never change
   the odds; they're only how the round is shown.
3. Edelweiss blooms are independent of the stop: 0, 1 or 2 blooms (+0.5x each) and, 1 round in 400, a
   Golden Edelweiss (x10), placed on steps he passes on the way to his stop and all collected. So every
   round's multiplier has the same distribution, E = 1.25 x 1.0225 = 1.278125.

A window pays RTP / (P(window) x E[multiplier]), quoted down to a 0.10x step.
"""

import itertools
import math
from collections import Counter
from dataclasses import dataclass

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


@dataclass(frozen=True)
class Rules:
    """Feature rates are target frequencies per round; bloom odds per round."""

    gondola: float  # +lift after climb 1 or 2 (half each)
    gondola_lift: tuple[int, int]
    avalanche: float  # -drop after climb 2, only when he's above `avalanche_above`
    avalanche_above: int
    avalanche_drop: tuple[int, int]
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

# A feature set: (gondola: 0 none / 1 after climb 1 / 2 after climb 2, avalanche, echo, foehn), each 0/1
FEATURE_SETS = [(g, a, e, f) for g in (0, 1, 2) for a in (0, 1) for e in (0, 1) for f in (0, 1)]


def story_moves(feature_set: tuple, climbs: tuple, lift: int, drop: int, drift: int, rules: Rules) -> list[tuple] | None:
    """A story's moves as (kind, steps, to), kind 'climb' or a feature; None when it breaks a rule: the
    avalanche only strikes above `avalanche_above`, the echo repeats a climb of 1 step or more, and he is
    never below step 0."""
    gondola, avalanche, echo, foehn = feature_set
    pos, out = 0, []

    def move(kind: str, steps: int) -> None:
        nonlocal pos
        pos += steps
        out.append((kind, steps, pos))

    move("climb", climbs[0])
    if gondola == 1:
        move("gondola", lift)
    move("climb", climbs[1])
    if gondola == 2:
        move("gondola", lift)
    if avalanche:
        if pos <= rules.avalanche_above:
            return None
        move("avalanche", -drop)
    move("climb", climbs[2])
    if echo:
        if climbs[2] == 0:
            return None
        move("echo", climbs[2])
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


class Stories:
    """Every story, by feature set and stop, and how likely each feature set is for each stop.

    A round's feature set is drawn at per-feature rates and redrawn until some story fits its stop (the
    empty set always fits: three climbs reach every stop, 0..27), so P(set | stop) is p(set) renormalized
    over the sets that fit. Where a feature can't fit a stop it drops out, so the rates are calibrated
    upward until each feature comes up at its target across all rounds (as closely as the stops allow).
    """

    def __init__(self, rules: Rules):
        self.rules = rules
        self.table: dict[tuple, dict[object, list[tuple]]] = {}
        lifts = range(rules.gondola_lift[0], rules.gondola_lift[1] + 1)
        drops = range(rules.avalanche_drop[0], rules.avalanche_drop[1] + 1)
        lo, hi = rules.foehn_drift
        drifts = [d for d in range(-hi, hi + 1) if abs(d) >= lo]
        for fs in FEATURE_SETS:
            by_stop: dict[object, list[tuple]] = {}
            options = itertools.product(
                itertools.product(range(MAX_CLIMB + 1), repeat=CLIMBS),
                lifts if fs[0] else [0], drops if fs[1] else [0], drifts if fs[3] else [0],
            )
            for climbs, lift, drop, drift in options:
                story = story_moves(fs, climbs, lift, drop, drift, rules)
                stop = None if story is None else ending(story)
                if stop is not None:
                    by_stop.setdefault(stop, []).append(tuple(story))
            self.table[fs] = by_stop
        self.rates = self._calibrate()
        self.odds = {stop: self.set_odds(self.rates, stop) for stop in stop_odds()}
        self.frequency = self.feature_frequency(self.rates)

    def candidates(self, fs: tuple, stop) -> list[tuple]:
        """The stories with feature set `fs` that reach `stop` (a rescue's story is a fall's)."""
        return self.table[fs].get(EDGE if stop == RESCUE else stop, [])

    def set_odds(self, rates: dict, stop) -> dict[tuple, float]:
        """P(feature set | stop) at per-feature draw `rates`."""
        def p(fs):
            g, *rest = fs
            out = 1 - rates["gondola"] if g == 0 else rates["gondola"] / 2
            for name, on in zip(FEATURES[1:], rest):
                out *= rates[name] if on else 1 - rates[name]
            return out
        weights = {fs: p(fs) for fs in FEATURE_SETS if self.candidates(fs, stop)}
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

    def _calibrate(self, rounds: int = 50) -> dict[str, float]:
        targets = self.targets()
        rates = dict(targets)
        for _ in range(rounds):
            freq = self.feature_frequency(rates)
            rates = {k: min(0.95, rates[k] * targets[k] / freq[k]) for k in rates}
        return rates

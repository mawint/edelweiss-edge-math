"""Edelweiss Edge: Ueli the yodeler climbs a 25-step ridge in three climbs; the player bets on where he stops
(a window of steps), or that he goes over the edge.

Every payout value lives here, as a multiple of the bet. A bet mode is one window: a difficulty (its width)
at one start step, or Over the Edge. The stop is drawn from fixed weights (climb.STOP_WEIGHTS: the higher,
the rarer); each window pays RTP / (P(window) x E[multiplier]) down to a 0.10x step, and the optimizer then
lands each mode on the RTP exactly. The design is in docs/GAME_DESIGN.md.
"""

from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode

from climb import EDGE, TOP, Rules, Stories, quoted_pay

RTP = 0.965
WINCAP = 5000.0
# A window is offered only when its pay stays at or under this (with the stop weights, every one does)
MAX_PAY = 500.0

# Difficulty -> window width (steps)
DIFFICULTIES = {"easy": 8, "medium": 5, "hard": 3, "pinpoint": 1}

# Feature rates are target frequencies per round. They don't change the odds (the stop is drawn first);
# climb.Stories calibrates how often each is drawn so it comes up at its target across all rounds.
RULES = Rules(
    gondola=1 / 9,  # +2..4 steps after climb 1 or 2 (half each)
    gondola_lift=(2, 4),
    avalanche=1 / 10,  # -2..5 steps after climb 2, only when he's above step 6
    avalanche_above=6,
    avalanche_drop=(2, 5),
    echo=1 / 14,  # the alphorn echoes the last climb: its steps again
    foehn=1 / 7,  # the wind drifts him 1..3 steps either way at the end
    foehn_drift=(1, 3),
    blooms={0: 2 / 3, 1: 1 / 6, 2: 1 / 6},  # normal blooms placed (and collected) per round
    bloom_bonus=0.5,  # +0.5x to the win multiplier per bloom
    golden=1 / 400,  # a Golden Edelweiss as well
    golden_mult=10,  # x10 on the win multiplier
)


def windows() -> list[tuple[str, str, object]]:
    """(mode name, difficulty, window) for every bet offered: each difficulty at each start step whose
    window fits on steps 0..25 and whose pay is at most MAX_PAY, then Over the Edge."""
    offered = []
    for difficulty, width in DIFFICULTIES.items():
        for lo in range(TOP - width + 2):
            window = (lo, lo + width - 1)
            if quoted_pay(window, RULES, RTP) <= MAX_PAY:
                offered.append((f"{difficulty}_{lo}", difficulty, window))
    offered.append((EDGE, EDGE, EDGE))
    return offered


class GameConfig(Config):
    """Edelweiss Edge rules, payouts and bet modes."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "edelweiss_edge"
        self.game_name = "edelweiss_edge"
        self.provider_numer = 0
        self.working_name = "Edelweiss Edge"
        self.win_type = "other"
        self.rtp = RTP
        self.construct_paths()

        # No reels: a round is a list of events, not a board
        self.num_reels = 0
        self.num_rows = []
        self.paytable = {}
        self.include_padding = False
        self.special_symbols = {"wild": [], "scatter": [], "multiplier": []}
        self.freespin_triggers = {self.basegame_type: {}, self.freegame_type: {}}
        self.anticipation_triggers = {self.basegame_type: 0, self.freegame_type: 0}

        self.wincap = WINCAP
        self.rules = RULES
        self.stories = Stories(RULES)
        # mode name -> {"difficulty", "window" ((lo, hi) or "edge"), "pay" (x bet)}
        self.windows = {
            name: {"difficulty": difficulty, "window": window, "pay": quoted_pay(window, RULES, RTP)}
            for name, difficulty, window in windows()
        }
        best_mult = (1 + RULES.bloom_bonus * max(RULES.blooms)) * RULES.golden_mult

        shared = dict(cost=1.0, auto_close_disabled=False, is_feature=False, is_buybonus=False, max_win=self.wincap, rtp=self.rtp)
        self.bet_modes = []
        for name, mode in self.windows.items():
            # Simulated books: half losses, half wins (the optimizer sets how often each comes up). A window
            # reaches the cap only if it pays 250x or more (x20: two blooms and the golden one); none does now.
            cap_quota = 0.001 if mode["pay"] * best_mult >= self.wincap else 0
            groups = [
                Distribution(criteria="0", quota=0.5, win_criteria=0.0, conditions={"reel_weights": {}}),
                Distribution(criteria="win", quota=0.5 - cap_quota, conditions={"reel_weights": {}}),
            ]
            if cap_quota:
                groups.insert(0, Distribution(criteria="wincap", quota=cap_quota, win_criteria=self.wincap,
                                              conditions={"reel_weights": {}, "force_wincap": True}))
            self.bet_modes.append(BetMode(name=name, distributions=groups, **shared))

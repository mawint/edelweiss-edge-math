"""The exact odds and the pays: the stop weights, the multiplier, the pay rule, the bet modes on offer and
the stories that act each stop out."""

import pytest

from climb import (EDGE, RESCUE, RESCUED, STOP_WEIGHTS, TOP, TOTAL_WEIGHT, ending, mean_multiplier,
                   quoted_pay, stop_odds, win_odds, window_odds)
from game_config import DIFFICULTIES, RTP, RULES, GameConfig

CONFIG = GameConfig()
STORIES = CONFIG.stories


def test_stop_weights():
    assert sum(STOP_WEIGHTS.values()) == TOTAL_WEIGHT == 100_000
    assert STOP_WEIGHTS[0] == 7134 and STOP_WEIGHTS[TOP] == 534
    assert all(STOP_WEIGHTS[k] - STOP_WEIGHTS[k + 1] == 264 for k in range(TOP))
    assert window_odds(EDGE) == 0.00316
    # 1 in 5 falls shown is rescued: 79 of step 25's weight
    assert RESCUED == 79 and RESCUED / (RESCUED + STOP_WEIGHTS[EDGE]) == pytest.approx(1 / 5, abs=0.001)
    assert sum(stop_odds().values()) == pytest.approx(1, abs=1e-12)


def test_multiplier_is_the_same_in_every_round():
    assert mean_multiplier(RULES) == pytest.approx(1.25 * 1.0225, rel=1e-12) == pytest.approx(1.278125)


@pytest.mark.parametrize("window,pay", [((0, 7), 1.5), ((18, 25), 6.4), ((0, 0), 10.5), ((25, 25), 141.3), (EDGE, 238.9)])
def test_pay_is_rtp_over_window_odds_and_multiplier(window, pay):
    fair = RTP / (window_odds(window) * 1.278125)
    assert quoted_pay(window, RULES, RTP) == pay
    assert pay <= fair < pay + 0.1


def test_every_placement_is_offered():
    counts = {d: sum(m["difficulty"] == d for m in CONFIG.windows.values()) for d in [*DIFFICULTIES, EDGE]}
    assert counts == {"easy": 19, "medium": 22, "hard": 24, "pinpoint": 26, EDGE: 1}
    assert len(CONFIG.bet_modes) == 92
    assert max(m["pay"] for m in CONFIG.windows.values()) < 500


@pytest.mark.parametrize("difficulty", list(DIFFICULTIES))
def test_pay_rises_toward_the_edge(difficulty):
    modes = [m for m in CONFIG.windows.values() if m["difficulty"] == difficulty]
    fair = [RTP / (window_odds(m["window"]) * 1.278125) for m in modes]
    assert all(a < b for a, b in zip(fair, fair[1:]))
    # (quoted down to 0.10x, two neighbours can quote the same: easy_0 and easy_1 both 1.5x)
    quoted = [m["pay"] for m in modes]
    assert all(a <= b for a, b in zip(quoted, quoted[1:]))
    assert CONFIG.windows[EDGE]["pay"] > quoted[-1]


@pytest.mark.parametrize("name", list(CONFIG.windows))
def test_every_mode_returns_just_under_the_rtp_before_the_optimizer(name):
    mode = CONFIG.windows[name]
    wins = win_odds(mode["window"], mode["pay"], RULES, CONFIG.wincap)
    rtp = sum(w / 100 * p for w, p in wins.items())
    # (pays and wins are quoted down to 0.10x: a 1.5x Easy window can fall ~6% short; the optimizer closes it)
    assert RTP - 0.06 < rtp <= RTP
    assert max(w for w, p in wins.items() if p > 0) < CONFIG.wincap * 100


def check_story(story, stop):
    """A story's moves chain from base camp and keep every rule, and it reaches `stop`."""
    pos = 0
    for kind, steps, to in story:
        assert to == pos + steps and to >= 0
        if kind == "climb":
            assert 0 <= steps <= 9
        elif kind == "avalanche":
            assert pos > 4 and 2 <= -steps <= pos  # above step 4; 2 steps or more, at most to base camp
        pos = to
    climbs = [steps for kind, steps, _ in story if kind == "climb"]
    assert len(climbs) == 3 and climbs.count(0) <= 1
    assert ending(story) == stop
    tos = [to for _, _, to in story]
    if stop == EDGE:
        assert max(tos[:-1]) <= TOP < tos[-1]  # crosses 25 on its last move
    else:
        assert max(tos) <= TOP and tos[-1] == stop


def test_no_story_has_two_zero_climbs():
    for params, _ in STORIES.table.values():
        assert ((params[:, :3] == 0).sum(axis=1) <= 1).all()


def test_stories_land_on_their_stop_and_keep_the_rules():
    # (about 2 million stories: a spread of each feature set's stories for each stop)
    for fs, (_, bounds) in STORIES.table.items():
        for stop, (lo, _, hi) in bounds.items():
            for index in sorted({(hi - lo - 1) * k // 24 for k in range(25)}):
                check_story(STORIES.story(fs, stop, index), stop)


def test_a_yodel_comes_as_often_as_with_three_fair_climbs():
    assert STORIES.yodel_share == pytest.approx(1 - 0.9**3, abs=1e-6)


def test_every_stop_has_stories():
    for stop in stop_odds():
        assert STORIES.odds[stop] and all(STORIES.count(fs, stop) for fs in STORIES.odds[stop])


def test_stop_0_can_be_an_avalanche_back_to_base_camp():
    found = []
    for fs in STORIES.odds[0]:
        if fs[1]:
            story = STORIES.story(fs, 0, 0)
            found += [m for m in story if m[0] == "avalanche" and m[2] == 0]
    assert found


def test_features_come_up_at_their_targets():
    targets = {"gondola": 1 / 9, "avalanche": 1 / 10, "echo": 1 / 14, "foehn": 1 / 7}
    for feature, rate in targets.items():
        assert STORIES.frequency[feature] == pytest.approx(rate, rel=1e-6)

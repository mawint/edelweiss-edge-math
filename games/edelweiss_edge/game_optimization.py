"""Optimizer targets, one bet mode at a time, straight from the exact odds (climb.py).

The SDK's optimizer takes, per outcome group, (rtp, hr): its share of the mode's RTP and how often it comes
up (1 in hr rounds). Here every group's hit rate is the true one (the stop weights), so the optimizer keeps
how often a window wins exactly; the only thing it adjusts is the mix of wins inside the "win" group (how
often the edelweiss multiplier comes with them), to make up the gap between the RTP and what the window's
pay, quoted down to a 0.10x step, returns. stats.py reports that gap per mode.
"""

from climb import win_odds
from optimization_program.optimization_config import (
    ConstructConditions,
    ConstructParameters,
    ConstructScaling,
    verify_optimization_input,
)


def parameters(test_spins: list[int]) -> dict:
    return ConstructParameters(
        num_show=5000,
        num_per_fence=10000,
        min_m2m=1,
        max_m2m=8,
        pmb_rtp=1.0,
        sim_trials=5000,
        test_spins=test_spins,
        test_weights=[0.3, 0.4, 0.3],
        score_type="rtp",
        max_trial_dist=15,
    ).return_dict()


def conditions(config, mode: dict, has_cap: bool) -> dict:
    """The groups of one mode: the cap (when it can be reached), losses, and every other win."""
    cap = round(config.wincap * 100)
    wins = win_odds(mode["window"], mode["pay"], config.rules, config.wincap)
    cap_rtp = wins[cap] * config.wincap if has_cap else 0.0
    win_rate = sum(p for w, p in wins.items() if 0 < w < cap or (w == cap and not has_cap))
    built = {}
    if has_cap:
        built["wincap"] = ConstructConditions(rtp=cap_rtp, av_win=config.wincap, search_conditions=config.wincap).return_dict()
    built["0"] = ConstructConditions(rtp=0, av_win=0, search_conditions=0).return_dict()
    built["win"] = ConstructConditions(rtp=config.rtp - cap_rtp, hr=1 / win_rate).return_dict()
    return built


class OptimizationSetup:
    """Per-mode optimizer targets."""

    def __init__(self, game_config):
        self.game_config = game_config
        self.game_config.opt_params = {}
        for bet_mode in game_config.bet_modes:
            name = bet_mode.get_name()
            has_cap = any(d.get_criteria() == "wincap" for d in bet_mode.get_distributions())
            self.game_config.opt_params[name] = {
                "conditions": conditions(game_config, game_config.windows[name], has_cap),
                "scaling": ConstructScaling([]).return_dict(),
                "parameters": parameters([50, 100, 200]),
            }
        verify_optimization_input(self.game_config, self.game_config.opt_params)

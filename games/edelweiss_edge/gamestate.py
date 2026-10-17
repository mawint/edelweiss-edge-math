"""Plays one simulated round: the reveal, the climbs, features and blooms as dealt, the settle and its pay."""

from game_override import GameStateOverride
from game_events import bloom_event, climb_event, fall_event, feature_event, reveal_event, settle_event
from src.events.events import wincap_event


class GameState(GameStateOverride):
    """Gamestate for a single round."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.play_round(self.plan_round())
            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def play_round(self, plan: dict) -> None:
        mode = self.mode
        reveal_event(self, mode["difficulty"], mode["window"], round(mode["pay"] * 100))
        for e in plan["events"]:
            if e["type"] == "climb":
                climb_event(self, e["n"], e["steps"], e["to"])
            elif e["type"] == "feature":
                feature_event(self, e["kind"], e["to"])
            elif e["type"] == "bloom":
                bloom_event(self, e["step"], e["golden"], e["multiplier"])
            else:
                fall_event(self, e["step"])
        settle_event(self, plan["step"], plan["won"], len(plan["blooms"]), round(plan["mult"] * 100), plan["win"])
        self.pay(plan["win"])
        if plan["win"] >= round(self.config.wincap * 100):
            self.wincap_triggered = True
            wincap_event(self)
        self.record({"outcome": "win" if plan["won"] else "loss", "stop": plan["stop"]})

    def run_freespin(self):
        """Required by the SDK; a round has no free spins."""
        raise NotImplementedError

    def pay(self, amount: int) -> None:
        """Credit a win (in hundredths of the bet)."""
        self.win_manager.reset_spin_win()
        self.win_manager.update_spinwin(amount / 100)
        self.win_manager.update_gametype_wins(self.gametype)

"""Edelweiss Edge book events. The game plays these back (src/book.ts in the game repo reads them; the
table is in docs/GAME_DESIGN.md, Book events).

Like the SDK's own events, each has its `index` in the book and a camelCase `type`; every amount is an
integer in hundredths of the bet (250 = 2.50x). Steps run 0 (base camp) to 25 (the top station); a step
past 25 is over the edge. The SDK adds `wincap` (when the cap is hit) and `finalWin` (what the book pays).
"""


def add_event(gamestate, event_type: str, **fields) -> None:
    gamestate.book.add_event({"index": len(gamestate.book.events), "type": event_type, **fields})


def reveal_event(gamestate, difficulty: str, window, pay: int) -> None:
    """The round begins: the bet's difficulty, its window ({"from", "to"} steps, or "edge" for Over the
    Edge) and what it pays before the multiplier (`pay`). Blooms stay hidden until he reaches them."""
    shown = window if window == "edge" else {"from": window[0], "to": window[1]}
    add_event(gamestate, "reveal", difficulty=difficulty, window=shown, pay=pay)


def climb_event(gamestate, n: int, steps: int, to: int) -> None:
    """Climb `n` of 3: Ueli climbs `steps` (0: he stops to yodel) and stands on step `to`."""
    add_event(gamestate, "climb", n=n, steps=steps, to=to)


def feature_event(gamestate, kind: str, to: int) -> None:
    """A feature moves him to step `to`: gondola (up 2-4), avalanche (down 2 or more, as far as base camp), echo (the last climb
    again), foehn (1-3 either way) or rescue (Barry carries him back to step 25 after a fall)."""
    add_event(gamestate, "feature", kind=kind, to=to)


def bloom_event(gamestate, step: int, golden: bool, multiplier: int) -> None:
    """He reaches an edelweiss on `step` (golden: the x10 one) and picks it: the win multiplier is now
    `multiplier` (hundredths: 150 = x1.5)."""
    add_event(gamestate, "bloom", step=step, golden=golden, multiplier=multiplier)


def fall_event(gamestate, step: int) -> None:
    """Past step 25: he goes over the edge from `step` (26 or more). A rescue event may follow."""
    add_event(gamestate, "fall", step=step)


def settle_event(gamestate, step: int, in_window: bool, blooms: int, multiplier: int, win: int) -> None:
    """Where he ends (`step`: past 25 is over the edge), whether the bet won, the blooms he picked, the win
    multiplier (hundredths) and the win (hundredths, pay x multiplier to a 0.10x step, capped)."""
    add_event(gamestate, "settle", step=step, inWindow=in_window, blooms=blooms, multiplier=multiplier, win=win)

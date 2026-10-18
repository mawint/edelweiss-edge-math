# Edelweiss Edge: game design

An alpine climbing game for Stake Engine. Ueli, a yodeler with an alphorn, climbs a ridge in three climbs. Before he sets off, the player places a window on the ridge, and wins if he stops inside it. The higher up the ridge, the rarer the stop and the more it pays: the risk is falling.

This file lives in both repos (the game, `mawint/edelweiss-edge`, and the math, `mawint/edelweiss-edge-math`). Change both together.

## The ridge

- 26 steps: **step 0** is base camp (2,200 m), **step 25** the top station (3,000 m), 32 m a step.
- Past step 25 he goes **over the edge**.

## How a round is decided

A round is decided first and acted out second.

1. **The stop is drawn** from fixed integer weights out of 100,000:
   - step k (0 to 25) weighs **7134 − 264k**, from 7,134 on step 0 down to 534 on step 25;
   - **over the edge** weighs **316** (0.316%);
   - all together they sum to 100,000.
2. **A story acts it out:** three climbs and the features (below). The features never change the odds. They're only how the round is shown.
3. **Barry's Rescue:** 79 of step 25's 534 are told as a fall and a rescue. That is a quarter of the edge weight, so 1 in 5 of the falls shown (395 per 100,000) ends with Barry carrying Ueli back to step 25. A rescued round ends on step 25, so it wins a window covering step 25 and loses Over the Edge, which **wins only on a real fall**.

## The bet

1. Pick a **difficulty**. It sets the window's width:

| difficulty | window |
|---|---|
| Easy | 8 steps |
| Medium | 5 steps |
| Hard | 3 steps |
| Pinpoint | 1 step |

2. The player **drags the window** along the mountain to any start on steps 0 to 25. Arrow buttons (and the arrow keys) move it a step at a time as a backup.
3. Ueli climbs. If he stops inside the window, the bet wins.

**Pay = RTP / (P(window) × 1.278125)**, quoted down to a 0.10× step. 1.278125 is the average edelweiss multiplier, the same in every round (see Edelweiss). Every window pays under 500×, so every placement is offered.

The fifth option is **Over the Edge**. It wins only on a real fall: a rare long shot at **238.9×**, 1 in 316.5.

Pays rise toward the edge for every difficulty. Quoted to 0.10×, two neighbours can quote the same pay (Easy on steps 0-7 and 1-8 both pay 1.5×), but the exact pay always rises. The full table is in the math repo's `stats.py`.

| bet | pay | wins 1 in |
|---|---|---|
| Easy, steps 0-7 | 1.5× | 2.0 |
| Easy, steps 18-25 | 6.4× | 8.6 |
| Medium, steps 0-4 | 2.2× | 3.0 |
| Medium, steps 21-25 | 14.2× | 18.8 |
| Hard, steps 0-2 | 3.6× | 4.9 |
| Hard, steps 23-25 | 31.5× | 41.8 |
| Pinpoint, step 0 | 10.5× | 14.0 |
| Pinpoint, step 13 | 20.3× | 27.0 |
| Pinpoint, step 25 | 141.3× | 187.3 |
| Over the Edge | 238.9× | 316.5 |

## The story: climbs and features

A story is **three climbs** ("Climb 1 of 3" on screen) of **0 to 9 steps** each. A 0 means he stops to yodel, and **at most one climb a round is a 0**: one yodel at most, never two zeros and never 0, 0, 0. The features come in between:

| feature | when | what | how often |
|---|---|---|---|
| Gondola Lift | after climb 1 or 2 (half each) | +2 to +4 steps | 1 in 9 rounds |
| Avalanche | after climb 2 or after climb 3 (half each; at most one a round), only when he's above step 4 | knocks him back 2 steps or more, as far as base camp (step 0) | 1 in 10 rounds |
| Alphorn Echo | right after climb 3 | the last climb's steps again (never a 0) | 1 in 14 rounds |
| Föhn Wind | at the end | 1 to 3 steps either way | 1 in 7 rounds |
| Barry's Rescue | after a fall | back on step 25 | 1 in 5 falls shown |

The order in a round: climb 1, [gondola], climb 2, [gondola], [avalanche], climb 3, [echo], [avalanche], [föhn].

Every story follows these rules:

- He is never below step 0.
- A story that stops on the ridge never goes past step 25 along the way, and ends exactly on its stop.
- A story that falls crosses step 25 on its **last move**, then the `fall` event follows (and, for a rescue, the rescue).

**Low stops are told as "climbed, then knocked back".** With one yodel at most, three climbs alone can't end below step 2, so stops 0 and 1 always come with an avalanche or the wind. For example, 3, 4, 2, then an avalanche back to base camp after climb 3; or 0, 1, 2, then the föhn blowing him down 3. Low stops are common (step 0 alone is 7.1% of rounds), so 6.7% of all rounds have an avalanche at stops 0 to 3. That is most of the avalanche's 1 in 10; the rest strike higher up.

**How a story is picked.**

1. Each feature is drawn at a calibrated rate, and the draw is redone until some story with those features reaches the round's stop.
2. A story with a yodel or without is chosen. Low stops have mostly yodel stories, so yodel stories are weighted down (×0.21) until a yodel comes up in 27.1% of rounds, as often as with three fair 0-9 climbs (1 − 0.9³).
3. One of those stories is picked evenly.

Some stops can't take some features. For example, a fall can't have an echo after the climb that crossed the edge, and stops 0 and 1 need an avalanche or the wind. So the draw rates are calibrated until each feature comes up at its target across all rounds.

| feature | target | draw rate | achieved (exact) | dealt, 400k rounds |
|---|---|---|---|---|
| Gondola Lift | 1 in 9 | 0.1321 | 1 in 9.00 | 1 in 9.00 |
| Avalanche | 1 in 10 | 0.0457 | 1 in 10.00 | 1 in 9.97 |
| Alphorn Echo | 1 in 14 | 0.0790 | 1 in 14.00 | 1 in 14.04 |
| Föhn Wind | 1 in 7 | 0.0664 | 1 in 7.00 | 1 in 7.00 |
| Barry's Rescue | 1 in 5 falls | (fixed by the weights) | 1 in 5.00 | 1 in 5 (sampling noise: 0.18-0.21) |
| one yodel | 27.1% of rounds | (yodel weight 0.21) | 27.10% | 27.18% |

The avalanche and föhn draw rates are low because the low stops already need them so often.

## Edelweiss

- The blooms are **independent of the stop**:
  - no blooms in 2/3 of rounds, one bloom in 1/6, two blooms in 1/6;
  - each bloom adds **+0.5×** to the win multiplier, which starts at ×1;
  - independently, a **Golden Edelweiss** appears in 1 round in 400 and multiplies the multiplier by **×10**.
- Blooms are **hidden until Ueli reaches them**. They sit only on steps he passes on the way to his stop: any step from 0 to the stop, or 0 to 25 for a fall. Two blooms may share a step. Every bloom placed is collected (a `bloom` event when he first reaches its step).
- So every round's multiplier is ×1, ×1.5 or ×2 (×10, ×15 or ×20 with the golden one), and **E[multiplier] = 1.25 × 1.0225 = 1.278125**.
- **Win = pay × multiplier**, rounded down to a 0.10× step and capped at **5,000×**. No window reaches the cap now: the biggest win is Over the Edge × 20 = 4,778×.

## Bet modes

- One bet mode per (difficulty, start step), plus one for Over the Edge: 19 Easy + 22 Medium + 24 Hard + 26 Pinpoint + 1 = **92 modes**. The names are `easy_0` … `easy_18`, `medium_0` … `medium_21`, `hard_0` … `hard_23`, `pinpoint_0` … `pinpoint_25` and `edge`. The window starts at the step in the name.
- Every mode costs 1× and targets **96.5% RTP**, the same as Thunder Push, High Noon Push and Sweet Push. Max win is **5,000×**.
- Each mode's books are simulated in two groups, losses and wins (plus the cap if a window could ever reach it). The optimizer is given each group's exact hit rate from the stop weights, so it keeps how often a window wins exactly. It only adjusts the mix inside the win group (how often wins come with blooms) to close the gap left by quoting pays down to 0.10×.
- Before the optimizer, the modes return **90.8% to 96.5%**. The cheapest Easy windows are short by the most, because 0.10× is a big share of a 1.5× pay.

## Book events

The format follows the existing math repos: each event has its `index` in the book and a camelCase `type`. Amounts are integers in hundredths of the bet (250 = 2.50×). Steps run 0 to 25, and a step past 25 is over the edge.

| event | fields | meaning |
|---|---|---|
| `reveal` | `difficulty` (easy, medium, hard, pinpoint, edge), `window` (`{from, to}` or `"edge"`), `pay` | The bet and what it pays before the multiplier. Blooms stay hidden. |
| `climb` | `n` (1-3), `steps` (0-9), `to` | Climb `n` of 3. `steps` 0 means he stops to yodel. |
| `feature` | `kind` (gondola, avalanche, echo, foehn, rescue), `to` | A feature moves him to step `to`. |
| `bloom` | `step`, `golden`, `multiplier` | He reaches a bloom and picks it; `multiplier` is the multiplier so far (150 = ×1.5). |
| `fall` | `step` | He goes over the edge from `step` (26 or more). A `feature` rescue may follow. |
| `settle` | `step`, `inWindow`, `blooms`, `multiplier`, `win` | Where he ends, whether the bet won, the blooms picked, the multiplier and the win. |
| `wincap` | `amount` | The SDK's event: the win hit the cap. |
| `finalWin` | `amount` | The SDK's event: what the round pays (the multiplier × 100). |

In a book, the `to` of every move is where the next move starts. `settle.win` equals `finalWin.amount`, which equals the book's `payoutMultiplier`. The climb event was called `pitch` in the first pass and is now `climb`, matching the on-screen "Climb 1 of 3".

## Open questions

- **Can Stake Engine take 92 bet modes in one game?** Each mode is its own lookup table and books file. If it can't, the fallback is to snap the window to every other start step, which roughly halves the window modes (about 47).
- **0.10× payout steps.** The other games assume the RGS only accepts payouts in 0.10× steps, so pays are quoted down to 0.10× and the optimizer closes a gap of up to ~6% on the cheapest Easy windows. It does that by giving their wins blooms more often than 1 in 3. If 0.01× is allowed, the pays could be quoted to the cent and the gap all but disappears.
- **Equal neighbouring pays.** Quoted to 0.10×, Easy on steps 0 and 1 both pay 1.5×. Is that fine, or should a window never quote the same as the one below it?
- **Bloom placement** is even over steps 0 to the stop, which counts base camp too. Should a bloom never sit on step 0?
- The stop weights, feature rates, bloom odds and the 5,000× cap are first-pass values to tune.

## Build plan

1. **Math (done, second pass):** stop weights, stories, features, blooms, the 92 modes, books and tests.
2. **Math, run:** `run.py` with the optimizer for all modes, then `stats.py` and the SDK checks. Settle the mode-count question first.
3. **Game, placeholder (done):** the ridge, a window control, Climb, played from fixture books through the mock RGS.
4. **Art direction (done):** alpine cartoon: chunky ink outlines that boil, squash and stretch, a sunset palette, a follow-cam.
5. **Game, first real pass (done):** every event staged on a canvas, synthesized sound with one mute, the window dragged in frame, space to climb, the review's screen sizes.
6. **Game, to finish:** a rules screen from the exported numbers, autoplay and turbo, replay polish, then `engine-review-prompt.md`.

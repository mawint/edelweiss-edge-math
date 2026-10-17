Edelweiss Edge: Ueli the yodeler climbs a 25-step ridge in three climbs; the player bets on where he stops (a
window of steps) or that he goes over the edge. One bet = one round; the book is the whole round. The
design is docs/GAME_DESIGN.md (the same file is in the game repo, mawint/edelweiss-edge). The game reads
these books with src/book.ts.

THE MODEL (second pass, October 17, 2026: the stop is decided first, pay rises toward the edge)
  climb.py              the stop weights, the multiplier, each window's pay, and every story (how a round
                        acts out its stop) with the calibrated feature draw rates. No SDK.
  game_config.py        every rate and value, and the bet modes (generated: 92)
  game_calculations.py  deals a round: the stop, its story, the blooms on the way, the win
  gamestate.py          plays the round into book events and pays it
  game_events.py        the event shapes
  game_optimization.py  per-mode optimizer targets, from the exact odds
  stats.py              per-mode pay, hit rate, RTP before the optimizer, max win; feature rates
  export_fixtures.py    a few books per mode for the game repo's demo and tests
  tests/                weights, pays, stories, books, dealt rates

  The stop: step k (0-25) weighs 7134 - 264k out of 100,000, over the edge 316. Of step 25's 534, 79 are told
  as a fall and Barry's Rescue (1 in 5 falls shown); Over the Edge wins only on a real fall (0.316%).
  The story: three climbs of 0-9 steps and the features, Gondola Lift (+2-4 after climb 1 or 2, 1 in 9),
  Avalanche (-2-5 after climb 2 when above step 6, 1 in 10), Alphorn Echo (the last climb again, 1 in 14),
  Foehn Wind (+-1-3 at the end, 1 in 7). A round draws its feature set (calibrated rates), redrawn until a
  story reaches its stop, then one of those stories evenly. Never below step 0; on the ridge never past 25;
  a fall crosses 25 on its last move. Features never change the odds.
  Edelweiss (independent of the stop): no blooms 2/3, one 1/6, two 1/6 (+0.5x each); a Golden Edelweiss
  1 in 400 (x10). Placed on steps 0..stop (0..25 for a fall), hidden until reached, all collected:
  E[multiplier] = 1.278125.

  Bet modes: {easy,medium,hard,pinpoint}_{start step} (windows of 8, 5, 3, 1 steps), all 91 placements,
  and edge. Pay = RTP / (P(window) x 1.278125), down to a 0.10x step; win = pay x multiplier, down to a
  0.10x step, capped at 5,000x (no window reaches it now). 96.5% RTP in every mode (the optimizer closes
  the rounding gap: stats.py shows it, up to ~6% on the cheapest Easy windows).

From the math-sdk root (make setup once):
  env/bin/python games/edelweiss_edge/run.py                simulate, optimize, check
  env/bin/python games/edelweiss_edge/stats.py              exact per-mode numbers
  env/bin/python -m pytest games/edelweiss_edge/tests       odds, stories and book tests
  env/bin/python games/edelweiss_edge/export_fixtures.py ../edelweiss-edge/fixtures/books.json

Upload: library/publish_files/ (the game's dev server reads it too: restart it after a run)

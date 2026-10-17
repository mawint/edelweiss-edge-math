# edelweiss-edge-math

Math for **Edelweiss Edge**, an alpine climbing game for Stake Engine: Ueli the yodeler climbs a 25-step ridge in three climbs, and the player bets on where he stops: the higher the window, the rarer and the more it pays. This repo is Stake's [math-sdk](https://github.com/StakeEngine/math-sdk) (at `a6dccd8`, the same base as thunder-push-math); the game lives in [`games/edelweiss_edge/`](games/edelweiss_edge/) (see its `readme.txt`).

```sh
make setup PYTHON=python3.13                  # once: Python 3.12+ and Rust (rustup.rs) required
env/bin/python games/edelweiss_edge/run.py    # simulate, optimize, check
env/bin/python games/edelweiss_edge/stats.py  # exact per-mode numbers
env/bin/python -m pytest games/edelweiss_edge/tests
```

Upload files land in `games/edelweiss_edge/library/publish_files/` (generated, not committed). The design, target rates and the book event format: [docs/GAME_DESIGN.md](docs/GAME_DESIGN.md) (also in the game repo, mawint/edelweiss-edge).

The upload scripts in `uploads/` read credentials from `uploads/.env`, which is gitignored and must never be committed (this repo is public).

---

# Stake Engine Math SDK

Welcome to [Stake Engine Math SDK](https://engine.stake.com/)!

The Math SDK is a Python-based engine for defining game rules, simulating outcomes, and optimizing win distributions. It generates all necessary backend and configuration files, lookup tables, and simulation results.
   

For technical details [view the docs](https://engineio.github.io/math-sdk/)


# Installation
 
This repository requires Python3 (version >= 3.12), along with the PIP package installer.
If the included optimization algorithm is being used, Rust/Cargo will also need to be installed.

It is recommended to use [Make](https://www.gnu.org/software/make/) and setup the engine by running:
```sh
make setup
```

Alternatively, visit our [Setup and Installation page](https://engineio.github.io/math-sdk/math_docs/general_overview/) for more details.


"""Generates the Edelweiss Edge books, lookup tables and stats for every bet mode."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 10
    rust_threads = 20
    batching_size = 50000
    compression = True
    profiling = False

    # 1e4 books per mode across 92 modes (a book is dealt straight from its stop, no retries): raise it for
    # the approval build.
    config = GameConfig()
    num_sim_args = {mode.get_name(): int(1e4) for mode in config.bet_modes}

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        # (the SDK's stat sheet assumes slot symbols: use stats.py for this game's numbers)
        "run_format_checks": True,
    }
    target_modes = list(num_sim_args.keys())

    gamestate = GameState(config)
    if run_conditions["run_optimization"]:
        OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_format_checks"]:
        execute_all_tests(config)

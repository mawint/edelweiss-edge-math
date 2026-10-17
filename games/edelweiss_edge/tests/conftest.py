"""The game's modules import each other by bare name (gamestate, game_config), as run.py does."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catan.game_engine.game import GameState
from catan.game_engine.board import Board
from catan.strategies.base import Agent
from catan.strategies.random_agent import RandomAgent
from catan.automatic_playing.simulation import simulate_game


def test_agent_protocol_and_layout():
    agent = RandomAgent(seed=7)
    assert isinstance(GameState(board=Board(seed=0), seed=0), GameState)
    assert callable(agent.choose_action)
    state, steps = simulate_game(seed=0, max_actions=4, agents={0: agent, 1: RandomAgent(seed=8)})
    assert steps == 4


def test_engine_import_without_matplotlib():
    """Core game logic must remain usable without the optional plotting library."""
    import subprocess
    import sys

    code = """
import builtins
original_import = builtins.__import__
def import_without_matplotlib(name, *args, **kwargs):
    if name == 'matplotlib' or name.startswith('matplotlib.'):
        raise ImportError('Matplotlib intentionally unavailable for this test')
    return original_import(name, *args, **kwargs)
builtins.__import__ = import_without_matplotlib
from catan.game_engine.board import Board
from catan.game_engine.game import GameState
from catan.automatic_playing.simulation import simulate_game
from catan.strategies.random_agent import RandomAgent
Board(seed=42)
"""
    subprocess.run([sys.executable, "-c", code], check=True)

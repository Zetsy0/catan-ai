from typing import Mapping

from ..game_engine.board import Board
from ..game_engine.game import GameState
from ..game_engine.dispatcher import execute_action
from ..game_engine.validation import validate_game_state
from ..strategies.base import Agent
from ..strategies.random_agent import RandomAgent


def simulate_game(
    seed: int = 0,
    max_actions: int = 5000,
    validate: bool = False,
    agents: Mapping[int, Agent] | None = None,
) -> tuple[GameState, int]:
    """Run a game with one agent per player.

    ``agents`` maps player IDs to objects exposing ``choose_action(state)``.
    If omitted, two seeded random agents are used (the previous behavior).
    The same agent objects are used for the entire game.
    """
    state = GameState(
        board=Board(seed=seed),
        seed=seed,
    )

    if agents is None:
        agents = {
            0: RandomAgent(seed=seed + 1),
            1: RandomAgent(seed=seed + 2),
        }

    if set(agents) != set(state.players):
        raise ValueError(
            f"Expected agents for player IDs {sorted(state.players)}, "
            f"got {sorted(agents)}"
        )

    for step in range(max_actions):
        if state.phase == "game_over":
            return state, step

        # During discards, the actor may differ from current_player_id.
        if state.phase == "discard":
            player_id = next(iter(state.pending_discards))
        else:
            player_id = state.current_player_id

        action = agents[player_id].choose_action(state)
        execute_action(state, action)
        if validate:
            validate_game_state(state)

    return state, max_actions

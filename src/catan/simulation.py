
from .board import Board
from .game import GameState
from .agents import RandomAgent
from .dispatcher import execute_action
from .validation import validate_game_state


def simulate_game(
    seed: int = 0,
    max_actions: int = 5000,
    validate: bool = False,
) -> tuple[GameState, int]:

    state = GameState(
        board=Board(seed=seed),
        seed=seed
    )

    agents = {
        0: RandomAgent(seed=seed + 1),
        1: RandomAgent(seed=seed + 2)
    }

    for step in range(max_actions):

        if state.phase == "game_over":
            return state, step

        # Determine who must make the next decision
        if state.phase == "discard":
            player_id = next(iter(state.pending_discards))
        else:
            player_id = state.current_player_id

        # Choose and execute an action
        action = agents[player_id].choose_action(state)
        execute_action(state, action)
        if validate:
            validate_game_state(state)

    return state, max_actions

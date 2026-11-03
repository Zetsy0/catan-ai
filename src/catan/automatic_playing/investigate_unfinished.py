
from ..game_engine.board import Board
from ..game_engine.game import GameState
from ..strategies.random_agent import RandomAgent
from ..game_engine.dispatcher import execute_action
from .simulation import simulate_game

N = 1000
ORIGINAL_LIMIT = 5000
NEW_LIMIT = 20000
REPORT_EVERY = 1000

# Identify the unfinished seeds
unfinished_seeds = [
    seed
    for seed in range(N)
    if simulate_game(seed, ORIGINAL_LIMIT)[0].phase != "game_over"
]

print(f"Unfinished seeds: {unfinished_seeds}")

# Investigate each unfinished game
for seed in unfinished_seeds:
    state = GameState(Board(seed=seed), seed=seed)

    agents = {
        0: RandomAgent(seed=seed + 1),
        1: RandomAgent(seed=seed + 2),
    }

    print(f"\n--- Seed {seed} ---")

    for step in range(1, NEW_LIMIT + 1):
        if state.phase == "game_over":
            break

        if state.phase == "discard":
            player_id = next(iter(state.pending_discards))
        else:
            player_id = state.current_player_id

        action = agents[player_id].choose_action(state)
        execute_action(state, action)

        if step % REPORT_EVERY == 0 or state.phase == "game_over":
            scores = [
                state.total_victory_points(pid)
                for pid in (0, 1)
            ]

            print(
                f"Actions: {step:5d} | "
                f"Turns: {state.turn_number:5d} | "
                f"VP: {scores} | "
                f"Dev deck: {len(state.development_card_deck)} | "
                f"Phase: {state.phase}"
            )

        if state.phase == "game_over":
            break

    print(f"Winner: {state.winner_id}")

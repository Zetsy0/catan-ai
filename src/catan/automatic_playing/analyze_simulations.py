from collections import Counter
from statistics import mean

from .simulation import simulate_game

N = 100
MAX_ACTIONS = 5000

results = [
    simulate_game(seed=i, max_actions=MAX_ACTIONS)
    for i in range(N)
]

winners = Counter(state.winner_id for state, _ in results)
phases = Counter(state.phase for state, _ in results)

print(f"Simulations: {N}")
print(f"Completed games: {N - winners[None]}")
print(f"Unfinished games: {winners[None]}")
print(f"Wins by player 0: {winners[0]}")
print(f"Wins by player 1: {winners[1]}")

print(f"Average actions: {mean(steps for _, steps in results):.1f}")
print(f"Average turns: {mean(state.turn_number for state, _ in results):.1f}")

print(f"Final phases: {dict(phases)}")
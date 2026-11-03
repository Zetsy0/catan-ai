
import pytest

from catan.simulation import simulate_game
from catan.validation import validate_game_state


def test_random_game_simulation():
    state, steps = simulate_game(seed=42, max_actions=500)

    assert 0 < steps <= 500
    assert state.turn_number > 0

    validate_game_state(state)


@pytest.mark.parametrize("seed", range(100))
def test_multiple_random_games(seed):
    max_actions = 1000

    state, steps = simulate_game(
        seed=seed,
        max_actions=max_actions,
        validate=True
    )

    print(
        f"\nSeed {seed}: "
        f"actions={steps}, "
        f"turns={state.turn_number}, "
        f"phase={state.phase}, "
        f"winner={state.winner_id}"
    )

    assert 0 < steps <= max_actions
    assert state.turn_number > 0

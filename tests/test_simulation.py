import pytest

from catan.game_engine.legal_actions import get_legal_actions
from catan.automatic_playing.simulation import simulate_game
from catan.game_engine.validation import validate_game_state


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


class FirstLegalActionAgent:
    """Simple duck-typed custom agent for interface tests."""

    def __init__(self):
        self.calls = 0

    def choose_action(self, state):
        self.calls += 1
        return get_legal_actions(state)[0]


def test_custom_agents_are_used():
    agent_0 = FirstLegalActionAgent()
    agent_1 = FirstLegalActionAgent()

    state, steps = simulate_game(
        seed=42,
        max_actions=12,
        validate=True,
        agents={0: agent_0, 1: agent_1},
    )

    assert steps == 12
    assert agent_0.calls > 0
    assert agent_1.calls > 0
    assert agent_0.calls + agent_1.calls == steps
    validate_game_state(state)


def test_missing_agent_raises_value_error():
    with pytest.raises(ValueError, match="Expected agents for player IDs"):
        simulate_game(agents={0: FirstLegalActionAgent()})

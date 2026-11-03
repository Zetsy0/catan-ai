
import copy
import pytest

from catan.board import Board
from catan.game import GameState
from catan.agents import RandomAgent, HumanAgent
from catan.legal_actions import get_legal_actions


@pytest.fixture
def state():
    return GameState(board=Board(seed=42), seed=123)


def test_random_agent_chooses_legal_action(state):
    agent = RandomAgent(seed=42)

    legal_actions = get_legal_actions(state)

    for _ in range(100):
        chosen_action = agent.choose_action(state)
        assert chosen_action in legal_actions


def test_random_agent_does_not_modify_state(state):
    agent = RandomAgent(seed=42)

    before = copy.deepcopy(state)
    rng_state = state.rng.getstate()

    agent.choose_action(state)

    assert state.phase == before.phase
    assert state.current_player_id == before.current_player_id
    assert state.players == before.players
    assert state.bank == before.bank
    assert state.development_card_deck == before.development_card_deck
    assert state.rng.getstate() == rng_state



def test_human_agent_selects_action(state, monkeypatch):
    agent = HumanAgent()

    legal_actions = get_legal_actions(state)

    # Simulate the user entering "0"
    monkeypatch.setattr("builtins.input", lambda _: "0")

    chosen_action = agent.choose_action(state)

    assert chosen_action == legal_actions[0]
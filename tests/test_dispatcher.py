
import pytest

from catan.board import Board
from catan.game import GameState
from catan.legal_actions import Action, get_legal_actions
from catan.dispatcher import execute_action


def test_execute_legal_action():
    state = GameState(board=Board(seed=42), seed=123)

    action = get_legal_actions(state)[0]
    assert action.name == "place_initial_settlement"

    execute_action(state, action)

    assert state.phase == "setup_road"
    assert action.args[0] in state.players[0].settlements


def test_reject_illegal_action():
    state = GameState(board=Board(seed=42), seed=123)

    with pytest.raises(ValueError):
        execute_action(state, Action("end_turn"))

    assert state.phase == "setup_settlement"

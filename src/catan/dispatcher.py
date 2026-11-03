from . import actions
from .game import GameState
from .legal_actions import Action, get_legal_actions


def execute_action(state: GameState, action: Action) -> int | None:
    if action not in get_legal_actions(state):
        raise ValueError(f"Illegal action: {action}")

    function = getattr(actions, action.name)
    return function(state, *action.args)

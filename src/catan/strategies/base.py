"""Common action-selection interface for all automated strategies."""

from typing import Protocol

from ..game_engine.game import GameState
from ..game_engine.legal_actions import Action


class Agent(Protocol):
    """Select a legal action for the acting player in the supplied state."""

    def choose_action(self, state: GameState) -> Action:
        ...

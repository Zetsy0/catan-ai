import random

from ..game_engine.game import GameState
from ..game_engine.legal_actions import Action, get_legal_actions


class RandomAgent:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_action(self, state: GameState) -> Action:
        legal_actions = get_legal_actions(state)

        if not legal_actions:
            raise ValueError("No legal actions available")

        return self.rng.choice(legal_actions)

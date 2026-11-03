import random

from .game import GameState
from .legal_actions import Action, get_legal_actions


class RandomAgent:
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def choose_action(self, state: GameState) -> Action:
        legal_actions = get_legal_actions(state)

        if not legal_actions:
            raise ValueError("No legal actions available")

        return self.rng.choice(legal_actions)

class HumanAgent:
    def choose_action(self, state: GameState) -> Action:
        legal_actions = get_legal_actions(state)

        if not legal_actions:
            raise ValueError("No legal actions available")

        # Determine who is making the decision
        if state.phase == "discard":
            player_id = next(iter(state.pending_discards))
        else:
            player_id = state.current_player_id

        player = state.players[player_id]

        print(f"\n--- Player {player_id} ---")
        print(f"Phase: {state.phase}")
        print(f"Victory points: {state.total_victory_points(player_id)}")
        print(f"Resources: {player.resources}")

        # Display available actions
        for i, action in enumerate(legal_actions):
            print(f"{i}: {action.name} {action.args}")

        # Ask the player to choose
        while True:
            try:
                choice = int(input("\nChoose an action: "))

                if 0 <= choice < len(legal_actions):
                    return legal_actions[choice]

            except ValueError:
                pass

            print("Invalid choice. Please try again.")

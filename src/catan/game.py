
from dataclasses import dataclass, field
import random

from .board import Board, Hex, Vertex
from .player import PlayerState

SETUP_ORDER = (0, 1, 1, 0)

@dataclass
class GameState:
    board: Board

    players: dict[int, PlayerState] = field(
        default_factory=lambda: {
            0: PlayerState(0),
            1: PlayerState(1)
        }
    )

    seed: int | None = None
    rng: random.Random = field(init=False, repr=False)
    current_player_id: int = 0
    turn_number: int = 0

    robber_hex: Hex = field(init=False)

    bank: dict[str, int] = field(default_factory = lambda :{
        "wood": 19,
        "brick": 19,
        "sheep": 19,
        "wheat": 19,
        "ore": 19
    })

    development_card_deck: list[str] = field(init=False)

    longest_road_holder: int | None = None
    largest_army_holder: int | None = None

    setup_step: int = 0
    pending_initial_settlement: Vertex | None = None

    last_roll: int | None = None
    pending_discards: dict[int, int] = field(default_factory=dict)

    phase: str = "setup_settlement"
    robber_return_phase: str | None = None # The phase which we will return to after the robber has moved

    def __post_init__(self):
        self.robber_hex = next(h for h, resource in self.board.hex_resources.items() if resource is None)
        self.development_card_deck = ["knight"] * 14 + ["victory_point"] * 5 + \
            ["monopoly"] * 2 + ["year_of_plenty"] * 2 + ["road_building"] * 2
        self.rng = random.Random(self.seed)
        self.rng.shuffle(self.development_card_deck)

    def visible_victory_points(self, player_id: int) -> int:
        return (
            self.players[player_id].building_points
            + 2 * int(player_id == self.longest_road_holder)
            + 2 * int(player_id == self.largest_army_holder)
        )

    def total_victory_points(self, player_id: int) -> int:
        return (
            self.visible_victory_points(player_id)
            + self.players[player_id].hidden_victory_points
        )
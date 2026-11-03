from dataclasses import dataclass, field
from .board import Vertex, Edge

MAX_ROADS = 15
MAX_SETTLEMENTS = 5
MAX_CITIES = 4

@dataclass
class PlayerState:
    player_id: int

    # Resources
    resources: dict[str, int] = field(
        default_factory=lambda: {
            "wood": 0,
            "brick": 0,
            "sheep": 0,
            "wheat": 0,
            "ore": 0
        }
    )

    # Buildings
    settlements: set[Vertex] = field(default_factory=set)
    cities: set[Vertex] = field(default_factory=set)
    roads: set[Edge] = field(default_factory=set)

    # Development cards
    development_cards: list[str] = field(default_factory=list)
    new_development_cards: list[str] = field(default_factory=list)

    played_dev_card_this_turn: bool = False

    # Army
    knights_played: int = 0

    @property
    def building_points(self) -> int:
        return len(self.settlements) + 2 * len(self.cities)

    @property
    def total_resources(self) -> int:
        return sum(self.resources.values())

    @property
    def hidden_victory_points(self) -> int:
        victory_points = self.development_cards.count("victory_point")
        victory_points += self.new_development_cards.count("victory_point")
        return victory_points

    @property
    def remaining_roads(self) -> int:
        return MAX_ROADS - len(self.roads)

    @property
    def remaining_settlements(self) -> int:
        return MAX_SETTLEMENTS - len(self.settlements)

    @property
    def remaining_cities(self) -> int:
        return MAX_CITIES - len(self.cities)

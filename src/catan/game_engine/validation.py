
from collections import Counter
from .game import GameState


RESOURCE_COUNT = 19

DEV_CARD_COUNTS = {
    "knight": 14,
    "victory_point": 5,
    "monopoly": 2,
    "year_of_plenty": 2,
    "road_building": 2,
}


def validate_game_state(state: GameState) -> None:

    # 1. Resource conservation
    for resource in state.bank:
        quantities = [
            state.bank[resource],
            *(player.resources[resource]
              for player in state.players.values())
        ]

        assert all(q >= 0 for q in quantities), (
            f"Negative quantity of {resource}"
        )

        assert sum(quantities) == RESOURCE_COUNT, (
            f"Resource conservation violated for {resource}: "
            f"{sum(quantities)} instead of {RESOURCE_COUNT}"
        )

    # 2. Development cards
    cards = Counter(state.development_card_deck)

    for player in state.players.values():
        cards.update(player.development_cards)
        cards.update(player.new_development_cards)

    assert set(cards).issubset(DEV_CARD_COUNTS), (
        f"Unknown development card type: {set(cards) - set(DEV_CARD_COUNTS)}"
    )

    # Played Knights are tracked separately
    played_knights = sum(
        player.knights_played
        for player in state.players.values()
    )

    for card_type, maximum in DEV_CARD_COUNTS.items():
        count = cards[card_type]

        if card_type == "knight":
            count += played_knights

        assert count <= maximum, (
            f"Too many {card_type} cards: {count} > {maximum}"
        )

    # 3. Buildings and roads
    occupied_vertices = set()
    occupied_edges = set()

    for player_id, player in state.players.items():

        assert len(player.settlements) <= 5, (
            f"Player {player_id} has too many settlements"
        )
        assert len(player.cities) <= 4, (
            f"Player {player_id} has too many cities"
        )
        assert len(player.roads) <= 15, (
            f"Player {player_id} has too many roads"
        )

        buildings = player.settlements | player.cities

        assert player.settlements.isdisjoint(player.cities), (
            f"Player {player_id} has overlapping buildings"
        )

        assert buildings.issubset(state.board.vertices), (
            f"Player {player_id} has buildings outside the board"
        )

        assert player.roads.issubset(state.board.edges), (
            f"Player {player_id} has roads outside the board"
        )

        assert occupied_vertices.isdisjoint(buildings), (
            "Multiple players own a building on the same vertex"
        )

        assert occupied_edges.isdisjoint(player.roads), (
            "Multiple players own the same road"
        )

        occupied_vertices.update(buildings)
        occupied_edges.update(player.roads)

    # 4. Settlement distance rule
    for vertex in occupied_vertices:
        assert state.board.vertex_adjacency[vertex].isdisjoint(
            occupied_vertices
        ), "Two buildings are adjacent"

    # 5. Victory and game termination
    if state.phase == "game_over":
        assert state.winner_id in state.players, (
            "Game ended without a valid winner"
        )

        assert state.total_victory_points(state.winner_id) >= 15, (
            "Winner has fewer than 15 victory points"
        )
    else:
        assert state.winner_id is None, (
            "Winner assigned before game ended"
        )

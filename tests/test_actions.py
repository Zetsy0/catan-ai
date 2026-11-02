
import pytest
from collections import Counter

from catan.board import Board, Vertex, get_vertices
from catan.game import GameState, SETUP_ORDER
from catan.rules import can_place_initial_settlement, can_place_initial_road, can_move_robber, get_trade_ratio
from catan.actions import (place_initial_settlement, place_initial_road, roll_dice, discard_resources, move_robber, build_road,
                           build_settlement, pay_resources, build_city, trade_with_bank, buy_development_card, end_turn, play_knight,
                           update_largest_army
)

@pytest.fixture
def game():
    return GameState(board=Board(seed=42), seed=123)


def test_initial_settlement(game):
    vertex = Vertex(0, 2)

    place_initial_settlement(game, vertex)

    assert vertex in game.players[0].settlements
    assert game.pending_initial_settlement == vertex
    assert game.phase == "setup_road"

    # First settlement gives no resources
    assert game.players[0].total_resources == 0


def test_occupied_vertex(game):
    vertex = Vertex(0, 2)
    game.players[1].settlements.add(vertex)

    with pytest.raises(ValueError):
        place_initial_settlement(game, vertex)

    # Failed action must not modify the state
    assert vertex not in game.players[0].settlements
    assert game.phase == "setup_settlement"


def test_correct_player(game):
    game.current_player_id = 1
    vertex = Vertex(0, 2)

    place_initial_settlement(game, vertex)

    assert vertex in game.players[1].settlements
    assert vertex not in game.players[0].settlements



def test_wrong_phase(game):
    game.phase = "setup_road"

    with pytest.raises(ValueError):
        place_initial_settlement(game, Vertex(0, 2))

    assert game.players[0].settlements == set()


def test_second_settlement_resources(game):
    game.setup_step = 2
    game.current_player_id = 1

    vertex = Vertex(0, 2)

    expected = Counter(
        game.board.hex_resources[h]
        for h in game.board.vertex_hex_adjacency[vertex]
    )

    place_initial_settlement(game, vertex)

    for resource in game.bank:
        assert game.players[1].resources[resource] == expected[resource]
        assert game.bank[resource] == 19 - expected[resource]


def test_initial_road(game):
    vertex = Vertex(0, 2)
    place_initial_settlement(game, vertex)

    neighbor = next(iter(game.board.vertex_adjacency[vertex]))
    edge = frozenset({vertex, neighbor})

    place_initial_road(game, edge)

    assert edge in game.players[0].roads
    assert game.pending_initial_settlement is None
    assert game.setup_step == 1
    assert game.current_player_id == 1
    assert game.phase == "setup_settlement"

def test_complete_setup(game):
    for step, player_id in enumerate(SETUP_ORDER):
        assert game.current_player_id == player_id
        assert game.phase == "setup_settlement"

        # Find a valid settlement location
        vertex = next(
            v for v in game.board.vertices
            if can_place_initial_settlement(game, v)
        )

        place_initial_settlement(game, vertex)

        assert game.phase == "setup_road"

        # Find a valid road connected to the new settlement
        edge = next(
            e for e in game.board.edges
            if can_place_initial_road(game, e)
        )

        place_initial_road(game, edge)

        assert game.setup_step == step + 1

    # Verify the final state
    assert game.setup_step == 4
    assert game.current_player_id == 0
    assert game.phase == "roll_dice"
    assert game.pending_initial_settlement is None

    for player in game.players.values():
        assert len(player.settlements) == 2
        assert len(player.roads) == 2

    
def test_invalid_initial_road(game):
    vertex = Vertex(0, 2)
    place_initial_settlement(game, vertex)

    invalid_edge = next(
        edge for edge in game.board.edges
        if vertex not in edge
    )

    with pytest.raises(ValueError):
        place_initial_road(game, invalid_edge)

    # Verify that the state remains unchanged
    assert game.players[0].roads == set()
    assert game.pending_initial_settlement == vertex
    assert game.setup_step == 0
    assert game.current_player_id == 0
    assert game.phase == "setup_road"


def test_wrong_road_phase(game):
    vertex = Vertex(0, 2)
    place_initial_settlement(game, vertex)

    edge = next(
        edge for edge in game.board.edges
        if can_place_initial_road(game, edge)
    )

    # Force an incorrect phase
    game.phase = "setup_settlement"

    with pytest.raises(ValueError):
        place_initial_road(game, edge)

    # Verify that the state remains unchanged
    assert game.players[0].roads == set()
    assert game.pending_initial_settlement == vertex
    assert game.setup_step == 0
    assert game.phase == "setup_settlement"


def test_roll_dice_wrong_phase(game):
    with pytest.raises(ValueError):
        roll_dice(game)


def test_roll_dice_reproducible():
    game1 = GameState(Board(seed=42), seed=123)
    game2 = GameState(Board(seed=42), seed=123)

    game1.phase = "roll_dice"
    game2.phase = "roll_dice"

    roll1 = roll_dice(game1)
    roll2 = roll_dice(game2)

    assert 2 <= roll1 <= 12
    assert roll1 == roll2


def test_dice_resource_integration(game, monkeypatch):
    game.phase = "roll_dice"

    hexagon = next(
        h for h, number in game.board.hex_numbers.items()
        if number == 6
    )

    vertex = next(iter(get_vertices(hexagon)))
    resource = game.board.hex_resources[hexagon]

    game.players[0].settlements.add(vertex)

    # Force a roll of 2 + 4 = 6
    dice = iter([2, 4])
    monkeypatch.setattr(
        game.rng, "randint", lambda a, b: next(dice)
    )

    result = roll_dice(game)

    assert result == 6
    assert game.last_roll == 6
    assert game.phase == "main_turn"
    assert resource is not None
    assert game.players[0].resources[resource] == 1
    assert game.bank[resource] == 18


def test_discard_resources(game):
    game.phase = "discard"
    game.pending_discards = {0: 5, 1: 6}

    game.players[0].resources["wood"] = 10
    game.players[1].resources["ore"] = 12
    game.bank["wood"] -= 10
    game.bank["ore"] -= 12

    discard_resources(game, 0, {"wood": 5})

    assert game.players[0].resources["wood"] == 5
    assert game.bank["wood"] == 14
    assert game.pending_discards == {1: 6}
    assert game.phase == "discard"

    discard_resources(game, 1, {"ore": 6})

    assert game.players[1].resources["ore"] == 6
    assert game.bank["ore"] == 13
    assert game.pending_discards == {}
    assert game.phase == "move_robber"


@pytest.mark.parametrize(
    "cards",
    [
        {"wood": 3},                  # Wrong total
        {"gold": 5},                  # Unknown resource
        {"wood": -1, "brick": 6},     # Negative quantity
        {"wood": 4, "brick": 1},      # Insufficient wood
    ]
)

def test_invalid_discard(game, cards):
    game.phase = "discard"
    game.pending_discards = {0: 5}

    game.players[0].resources["wood"] = 3
    game.players[0].resources["brick"] = 7
    game.bank["wood"] -= 3
    game.bank["brick"] -= 7

    # Save the state before the attempted action
    original_resources = game.players[0].resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        discard_resources(game, 0, cards)

    # The failed action must leave everything unchanged
    assert game.players[0].resources == original_resources
    assert game.bank == original_bank
    assert game.pending_discards == {0: 5}
    assert game.phase == "discard"

def test_discard_wrong_phase(game):
    with pytest.raises(ValueError):
        discard_resources(game, 0, {"wood": 5})

    assert game.phase == "setup_settlement"

def test_discard_wrong_player(game):
    game.phase = "discard"
    game.pending_discards = {1: 5}

    with pytest.raises(ValueError):
        discard_resources(game, 0, {"wood": 5})

    assert game.pending_discards == {1: 5}
    assert game.phase == "discard"

def test_robber_steals_resource(game):
    game.phase = "move_robber"

    destination = next(
        h for h in game.board.hexes
        if h != game.robber_hex
    )

    vertex = next(iter(get_vertices(destination)))
    game.players[1].settlements.add(vertex)

    # Give player 1 three visible VPs to bypass friendly robber
    game.largest_army_holder = 1

    game.players[1].resources["wood"] = 3
    game.bank["wood"] -= 3

    move_robber(game, destination)

    assert game.robber_hex == destination
    assert game.players[1].resources["wood"] == 2
    assert game.players[0].resources["wood"] == 1
    assert game.bank["wood"] == 16
    assert game.phase == "main_turn"

def test_robber_no_adjacent_victim(game):
    game.phase = "move_robber"

    destination = next(
        h for h in game.board.hexes
        if h != game.robber_hex
    )

    # Place opponent's settlement away from destination
    vertex = next(
        v for v in game.board.vertices
        if v not in get_vertices(destination)
    )

    game.players[1].settlements.add(vertex)
    game.players[1].resources["wood"] = 3

    move_robber(game, destination)

    assert game.robber_hex == destination
    assert game.players[1].resources["wood"] == 3
    assert game.players[0].resources["wood"] == 0
    assert game.phase == "main_turn"

def test_robber_empty_victim(game):
    game.phase = "move_robber"

    destination = next(
        h for h in game.board.hexes
        if h != game.robber_hex
    )

    vertex = next(iter(get_vertices(destination)))
    game.players[1].settlements.add(vertex)
    game.largest_army_holder = 1

    # Opponent has no resources
    assert game.players[1].total_resources == 0

    move_robber(game, destination)

    assert game.robber_hex == destination
    assert game.players[0].total_resources == 0
    assert game.players[1].total_resources == 0
    assert game.phase == "main_turn"

def test_robber_friendly_rule(game):
    game.phase = "move_robber"
    initial_hex = game.robber_hex

    destination = next(
        h for h in game.board.hexes
        if h != initial_hex
    )

    vertex = next(iter(get_vertices(destination)))
    game.players[1].settlements.add(vertex)

    # Player 1 has only one visible VP
    assert game.visible_victory_points(1) == 1
    assert not can_move_robber(game, destination)

    with pytest.raises(ValueError):
        move_robber(game, destination)

    # Invalid action must not modify the state
    assert game.robber_hex == initial_hex
    assert game.phase == "move_robber"
    assert game.players[0].total_resources == 0
    assert game.players[1].total_resources == 0


@pytest.fixture
def road_setup(game):
    edge = next(iter(game.board.edges))
    vertex = next(iter(edge))

    game.players[0].settlements.add(vertex)
    game.players[0].resources["wood"] = 1
    game.players[0].resources["brick"] = 1

    game.bank["wood"] -= 1
    game.bank["brick"] -= 1

    game.phase = "main_turn"

    return game, edge


def test_build_road(road_setup):
    game, edge = road_setup

    build_road(game, edge)

    assert edge in game.players[0].roads
    assert game.players[0].resources["wood"] == 0
    assert game.players[0].resources["brick"] == 0
    assert game.bank["wood"] == 19
    assert game.bank["brick"] == 19
    assert game.phase == "main_turn"


@pytest.mark.parametrize("missing_resource", ["wood", "brick"])
def test_build_road_insufficient_resources(road_setup, missing_resource):
    game, edge = road_setup
    player = game.players[0]

    player.resources[missing_resource] = 0
    game.bank[missing_resource] += 1

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        build_road(game, edge)

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert edge not in player.roads
    assert game.phase == "main_turn"


def test_build_road_invalid_location(road_setup):
    game, edge = road_setup

    # Find an edge disconnected from the player's settlement
    invalid_edge = next(
        e for e in game.board.edges
        if e.isdisjoint(edge)
    )

    original_resources = game.players[0].resources.copy()

    with pytest.raises(ValueError):
        build_road(game, invalid_edge)

    assert game.players[0].roads == set()
    assert game.players[0].resources == original_resources
    assert game.phase == "main_turn"


def test_build_road_wrong_phase(road_setup):
    game, edge = road_setup
    game.phase = "roll_dice"

    original_resources = game.players[0].resources.copy()

    with pytest.raises(ValueError):
        build_road(game, edge)

    assert edge not in game.players[0].roads
    assert game.players[0].resources == original_resources
    assert game.phase == "roll_dice"

def test_pay_resources_success(game):
    player = game.players[0]

    player.resources["wood"] = 3
    player.resources["brick"] = 2
    game.bank["wood"] -= 3
    game.bank["brick"] -= 2

    cost = {"wood": 2, "brick": 1}

    assert pay_resources(game, 0, cost)

    assert player.resources["wood"] == 1
    assert player.resources["brick"] == 1
    assert game.bank["wood"] == 18
    assert game.bank["brick"] == 18


@pytest.mark.parametrize(
    "cost",
    [
        {"wood": 2},                  # Insufficient wood
        {"wood": 1, "brick": 1},      # Insufficient brick
        {"wood": -1},                 # Negative cost
        {"gold": 1},                  # Unknown resource
    ]
)
def test_pay_resources_invalid(game, cost):
    player = game.players[0]

    player.resources["wood"] = 1
    game.bank["wood"] -= 1

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    assert not pay_resources(game, 0, cost)

    # No resources should have been transferred
    assert player.resources == original_resources
    assert game.bank == original_bank


def test_build_settlement(game):
    player = game.players[0]
    game.phase = "main_turn"

    # Connect an empty vertex to the player's road network
    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))
    player.roads.add(frozenset({vertex, neighbor}))

    # Give the player exactly enough resources
    cost = ["wood", "brick", "sheep", "wheat"]

    for resource in cost:
        player.resources[resource] = 1
        game.bank[resource] -= 1

    build_settlement(game, vertex)

    assert vertex in player.settlements
    assert player.building_points == 1
    assert game.phase == "main_turn"

    for resource in cost:
        assert player.resources[resource] == 0
        assert game.bank[resource] == 19


def test_build_settlement_insufficient_resources(game):
    player = game.players[0]
    game.phase = "main_turn"

    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))
    player.roads.add(frozenset({vertex, neighbor}))

    # Missing sheep
    for resource in ["wood", "brick", "wheat"]:
        player.resources[resource] = 1
        game.bank[resource] -= 1

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        build_settlement(game, vertex)

    assert vertex not in player.settlements
    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "main_turn"

def test_build_city(game):
    player = game.players[0]
    game.phase = "main_turn"

    vertex = next(iter(game.board.vertices))
    player.settlements.add(vertex)

    # Give exactly enough resources
    player.resources["ore"] = 3
    player.resources["wheat"] = 2
    game.bank["ore"] -= 3
    game.bank["wheat"] -= 2

    assert player.building_points == 1

    build_city(game, vertex)

    # Settlement upgraded to city
    assert vertex not in player.settlements
    assert vertex in player.cities

    # Victory points and available pieces
    assert player.building_points == 2
    assert player.remaining_settlements == 5
    assert player.remaining_cities == 3

    # Payment
    assert player.resources["ore"] == 0
    assert player.resources["wheat"] == 0
    assert game.bank["ore"] == 19
    assert game.bank["wheat"] == 19

    assert game.phase == "main_turn"


@pytest.mark.parametrize(
    "ore, wheat",
    [
        (2, 2),  # Insufficient ore
        (3, 1),  # Insufficient wheat
    ]
)
def test_build_city_insufficient_resources(game, ore, wheat):
    player = game.players[0]
    game.phase = "main_turn"

    vertex = next(iter(game.board.vertices))
    player.settlements.add(vertex)

    player.resources["ore"] = ore
    player.resources["wheat"] = wheat
    game.bank["ore"] -= ore
    game.bank["wheat"] -= wheat

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        build_city(game, vertex)

    # Failed action leaves state unchanged
    assert vertex in player.settlements
    assert vertex not in player.cities
    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "main_turn"


def test_build_city_wrong_phase(game):
    player = game.players[0]
    game.phase = "roll_dice"

    vertex = next(iter(game.board.vertices))
    player.settlements.add(vertex)

    player.resources["ore"] = 3
    player.resources["wheat"] = 2

    original_resources = player.resources.copy()

    with pytest.raises(ValueError):
        build_city(game, vertex)

    assert vertex in player.settlements
    assert vertex not in player.cities
    assert player.resources == original_resources


def test_build_city_opponent_settlement(game):
    game.phase = "main_turn"
    player = game.players[0]

    vertex = next(iter(game.board.vertices))
    game.players[1].settlements.add(vertex)

    player.resources["ore"] = 3
    player.resources["wheat"] = 2

    original_resources = player.resources.copy()

    with pytest.raises(ValueError):
        build_city(game, vertex)

    assert vertex in game.players[1].settlements
    assert vertex not in player.cities
    assert player.resources == original_resources

@pytest.mark.parametrize(
    "port_type, give_resource, expected_ratio",
    [
        (None, "wood", 4),       # No port
        ("generic", "wood", 3),  # Generic port
        ("wood", "wood", 2),     # Specialized wood port
        ("ore", "ore", 2),       # Specialized ore port
    ]
)
def test_trade_with_bank_success(
    game, port_type, give_resource, expected_ratio
):
    game.phase = "main_turn"
    player = game.players[0]

    # Give the player access to the specified port
    if port_type is not None:
        edge = next(
            e for e, kind in game.board.ports.items()
            if kind == port_type
        )
        player.settlements.add(next(iter(edge)))

    # Give the player exactly enough resources
    player.resources[give_resource] = expected_ratio
    game.bank[give_resource] -= expected_ratio

    assert get_trade_ratio(game, 0, give_resource) == expected_ratio

    trade_with_bank(game, give_resource, "brick")

    # Player gives resources and receives one brick
    assert player.resources[give_resource] == 0
    assert player.resources["brick"] == 1

    # Bank receives resources and gives one brick
    assert game.bank[give_resource] == 19
    assert game.bank["brick"] == 18

    assert game.phase == "main_turn"


def test_trade_with_bank_insufficient_resources(game):
    game.phase = "main_turn"
    player = game.players[0]

    # Player has only 3 wood, but needs 4
    player.resources["wood"] = 3
    game.bank["wood"] -= 3

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        trade_with_bank(game, "wood", "ore")

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "main_turn"


def test_trade_with_bank_empty_bank(game):
    game.phase = "main_turn"
    player = game.players[0]

    player.resources["wood"] = 4
    game.bank["wood"] -= 4

    # Bank has no ore
    game.bank["ore"] = 0

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        trade_with_bank(game, "wood", "ore")

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "main_turn"


@pytest.mark.parametrize(
    "give_resource, receive_resource",
    [
        ("gold", "ore"),  # Invalid offered resource
        ("wood", "gold"), # Invalid requested resource
        ("wood", "wood"), # Same resource
    ]
)
def test_trade_with_bank_invalid_resources(
    game, give_resource, receive_resource
):
    game.phase = "main_turn"
    player = game.players[0]

    player.resources["wood"] = 4
    game.bank["wood"] -= 4

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        trade_with_bank(game, give_resource, receive_resource)

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "main_turn"


def test_trade_with_bank_wrong_phase(game):
    player = game.players[0]

    player.resources["wood"] = 4
    game.bank["wood"] -= 4

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    # Default phase is setup_settlement
    with pytest.raises(ValueError):
        trade_with_bank(game, "wood", "ore")

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.phase == "setup_settlement"

@pytest.fixture
def dev_card_setup(game):
    game.phase = "main_turn"
    player = game.players[0]

    # Give the player exactly enough resources
    for resource in ["ore", "wheat", "sheep"]:
        player.resources[resource] = 1
        game.bank[resource] -= 1

    return game


def test_buy_development_card(dev_card_setup):
    game = dev_card_setup
    player = game.players[0]

    initial_deck_size = len(game.development_card_deck)
    expected_card = game.development_card_deck[-1]

    buy_development_card(game)

    # Card transferred from deck to player
    assert len(game.development_card_deck) == initial_deck_size - 1
    assert player.new_development_cards == [expected_card]
    assert player.development_cards == []

    # Payment completed
    for resource in ["ore", "wheat", "sheep"]:
        assert player.resources[resource] == 0
        assert game.bank[resource] == 19

    assert game.phase == "main_turn"


@pytest.mark.parametrize("missing_resource", ["ore", "wheat", "sheep"])
def test_buy_development_card_insufficient_resources(
    dev_card_setup, missing_resource
):
    game = dev_card_setup
    player = game.players[0]

    player.resources[missing_resource] = 0
    game.bank[missing_resource] += 1

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()
    original_deck = game.development_card_deck.copy()

    with pytest.raises(ValueError):
        buy_development_card(game)

    # Failed purchase leaves everything unchanged
    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.development_card_deck == original_deck
    assert player.new_development_cards == []
    assert game.phase == "main_turn"


def test_buy_development_card_empty_deck(dev_card_setup):
    game = dev_card_setup
    player = game.players[0]

    game.development_card_deck.clear()

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()

    with pytest.raises(ValueError):
        buy_development_card(game)

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert player.new_development_cards == []
    assert game.development_card_deck == []
    assert game.phase == "main_turn"


def test_buy_development_card_wrong_phase(dev_card_setup):
    game = dev_card_setup
    player = game.players[0]

    game.phase = "roll_dice"

    original_resources = player.resources.copy()
    original_bank = game.bank.copy()
    original_deck = game.development_card_deck.copy()

    with pytest.raises(ValueError):
        buy_development_card(game)

    assert player.resources == original_resources
    assert game.bank == original_bank
    assert game.development_card_deck == original_deck
    assert player.new_development_cards == []
    assert game.phase == "roll_dice"


def test_buy_last_development_card(dev_card_setup):
    game = dev_card_setup
    player = game.players[0]

    # Only one card remains
    game.development_card_deck = ["knight"]

    buy_development_card(game)

    assert game.development_card_deck == []
    assert player.new_development_cards == ["knight"]
    assert game.phase == "main_turn"

def test_end_turn(game):
    game.phase = "main_turn"

    # Player 1 has existing and newly purchased cards
    game.players[1].development_cards = ["monopoly"]
    game.players[1].new_development_cards = ["knight"]
    game.players[1].played_dev_card_this_turn = True

    end_turn(game)

    assert game.current_player_id == 1
    assert game.turn_number == 1
    assert game.phase == "roll_dice"

    # New cards become playable, existing cards are preserved
    assert game.players[1].development_cards == ["monopoly", "knight"]
    assert game.players[1].new_development_cards == []

    # Development card allowance resets
    assert game.players[1].played_dev_card_this_turn is False


def test_development_cards_next_turn(game):
    game.phase = "main_turn"

    # Player 0 purchases a knight during their turn
    game.players[0].new_development_cards = ["knight"]

    # Player 0 ends their turn
    end_turn(game)

    # Player 0's card is not yet playable
    assert game.current_player_id == 1
    assert game.players[0].development_cards == []
    assert game.players[0].new_development_cards == ["knight"]

    # Simulate player 1 completing their turn
    game.phase = "main_turn"
    end_turn(game)

    # Player 0 begins their next turn
    assert game.current_player_id == 0
    assert game.turn_number == 2
    assert game.phase == "roll_dice"

    assert game.players[0].development_cards == ["knight"]
    assert game.players[0].new_development_cards == []


@pytest.mark.parametrize(
    "phase",
    ["roll_dice", "discard", "move_robber", "setup_settlement"]
)
def test_end_turn_wrong_phase(game, phase):
    game.phase = phase
    game.players[1].new_development_cards = ["knight"]

    with pytest.raises(ValueError):
        end_turn(game)

    # Invalid action must not modify the game state
    assert game.current_player_id == 0
    assert game.turn_number == 0
    assert game.phase == phase
    assert game.players[1].development_cards == []
    assert game.players[1].new_development_cards == ["knight"]


def test_end_turn_no_development_cards(game):
    game.phase = "main_turn"

    end_turn(game)

    assert game.current_player_id == 1
    assert game.players[1].development_cards == []
    assert game.players[1].new_development_cards == []
    assert game.phase == "roll_dice"


def test_play_knight_before_dice(game):
    game.phase = "roll_dice"
    player = game.players[0]
    player.development_cards = ["knight"]

    play_knight(game)

    assert player.development_cards == []
    assert player.knights_played == 1
    assert player.played_dev_card_this_turn is True
    assert game.phase == "move_robber"
    assert game.robber_return_phase == "roll_dice"

    # Complete robber movement
    destination = next(
        h for h in game.board.hexes
        if can_move_robber(game, h)
    )

    move_robber(game, destination)

    assert game.robber_hex == destination
    assert game.phase == "roll_dice"
    assert game.robber_return_phase is None


def test_play_knight_during_main_turn(game):
    game.phase = "main_turn"
    player = game.players[0]
    player.development_cards = ["knight"]

    play_knight(game)

    assert game.phase == "move_robber"
    assert game.robber_return_phase == "main_turn"

    destination = next(
        h for h in game.board.hexes
        if can_move_robber(game, h)
    )

    move_robber(game, destination)

    assert game.phase == "main_turn"
    assert game.robber_return_phase is None
    assert player.knights_played == 1


def test_cannot_play_new_knight(game):
    game.phase = "roll_dice"
    player = game.players[0]

    # Knight purchased this turn
    player.new_development_cards = ["knight"]

    with pytest.raises(ValueError):
        play_knight(game)

    assert player.new_development_cards == ["knight"]
    assert player.knights_played == 0
    assert player.played_dev_card_this_turn is False
    assert game.phase == "roll_dice"


def test_cannot_play_two_knights(game):
    game.phase = "main_turn"
    player = game.players[0]
    player.development_cards = ["knight", "knight"]

    play_knight(game)

    destination = next(
        h for h in game.board.hexes
        if can_move_robber(game, h)
    )
    move_robber(game, destination)

    # Attempt to play a second Knight
    with pytest.raises(ValueError):
        play_knight(game)

    assert player.development_cards == ["knight"]
    assert player.knights_played == 1
    assert player.played_dev_card_this_turn is True
    assert game.phase == "main_turn"


def test_seven_robber_return_phase(game, monkeypatch):
    game.phase = "roll_dice"

    # Player 1 must discard five wood cards
    game.players[1].resources["wood"] = 10
    game.bank["wood"] -= 10

    # Force a roll of 7
    dice = iter([3, 4])
    monkeypatch.setattr(
        game.rng, "randint",
        lambda a, b: next(dice)
    )

    assert roll_dice(game) == 7
    assert game.phase == "discard"
    assert game.robber_return_phase == "main_turn"
    assert game.pending_discards == {1: 5}

    discard_resources(game, 1, {"wood": 5})

    assert game.phase == "move_robber"

    destination = next(
        h for h in game.board.hexes
        if can_move_robber(game, h)
    )

    move_robber(game, destination)

    assert game.phase == "main_turn"
    assert game.robber_return_phase is None

def test_largest_army_below_threshold(game):
    game.players[0].knights_played = 2
    game.players[1].knights_played = 1

    update_largest_army(game)

    assert game.largest_army_holder is None
    assert game.visible_victory_points(0) == 0
    assert game.visible_victory_points(1) == 0


def test_largest_army_threshold(game):
    game.players[0].knights_played = 3
    game.players[1].knights_played = 2

    update_largest_army(game)

    assert game.largest_army_holder == 0
    assert game.visible_victory_points(0) == 2
    assert game.visible_victory_points(1) == 0


def test_largest_army_tie(game):
    game.players[0].knights_played = 3
    game.players[1].knights_played = 2

    update_largest_army(game)
    assert game.largest_army_holder == 0

    # Player 1 catches up
    game.players[1].knights_played = 3
    update_largest_army(game)

    # Player 0 retains Largest Army
    assert game.largest_army_holder == 0
    assert game.visible_victory_points(0) == 2
    assert game.visible_victory_points(1) == 0


def test_largest_army_transfer(game):
    game.players[0].knights_played = 3
    game.players[1].knights_played = 2

    update_largest_army(game)
    assert game.largest_army_holder == 0

    # Player 1 overtakes player 0
    game.players[1].knights_played = 4
    update_largest_army(game)

    assert game.largest_army_holder == 1

    # Victory points transfer with the award
    assert game.visible_victory_points(0) == 0
    assert game.visible_victory_points(1) == 2


def test_largest_army_integration_with_knight(game):
    game.phase = "main_turn"
    player = game.players[0]

    # Player already played two Knights in previous turns
    player.knights_played = 2
    player.development_cards = ["knight"]

    assert game.largest_army_holder is None

    # Playing the third Knight should award Largest Army
    play_knight(game)

    assert player.knights_played == 3
    assert player.development_cards == []
    assert player.played_dev_card_this_turn is True

    assert game.largest_army_holder == 0
    assert game.visible_victory_points(0) == 2
    assert game.phase == "move_robber"


    

    












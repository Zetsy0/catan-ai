
import copy
import pytest

from catan.board import Board
from catan.game import GameState
from catan import actions as engine_actions
from catan.legal_actions import Action, get_legal_actions
from catan.rules import (
    can_place_initial_settlement,
    can_place_initial_road,
    can_move_robber,
    can_place_road,
)


@pytest.fixture
def state():
    return GameState(board=Board(seed=42), seed=123)


def place_first_settlement_and_road(state):
    """Complete the first player's first settlement-road pair."""
    settlement = get_legal_actions(state)[0]
    engine_actions.place_initial_settlement(state, *settlement.args)

    road = get_legal_actions(state)[0]
    engine_actions.place_initial_road(state, *road.args)


# ==========================================
# Setup
# ==========================================

def test_setup_actions(state):
    settlement_actions = get_legal_actions(state)

    assert settlement_actions
    assert all(a.name == "place_initial_settlement"
               for a in settlement_actions)

    assert {a.args[0] for a in settlement_actions} == {
        vertex for vertex in state.board.vertices
        if can_place_initial_settlement(state, vertex)
    }

    engine_actions.place_initial_settlement(
        state, *settlement_actions[0].args
    )

    road_actions = get_legal_actions(state)

    assert road_actions
    assert all(a.name == "place_initial_road"
               for a in road_actions)

    assert {a.args[0] for a in road_actions} == {
        edge for edge in state.board.edges
        if can_place_initial_road(state, edge)
    }


# ==========================================
# Rolling and development cards
# ==========================================

def test_roll_dice_actions(state):
    state.phase = "roll_dice"

    assert get_legal_actions(state) == [Action("roll_dice")]

    player = state.players[0]
    player.development_cards = [
        "monopoly", "year_of_plenty",
        "knight", "road_building"
    ]

    available = get_legal_actions(state)
    names = {a.name for a in available}

    assert "roll_dice" in names
    assert "play_monopoly" in names
    assert "play_year_of_plenty" in names
    assert "play_knight" in names

    # No connected roads or buildings yet
    assert "play_road_building" not in names

    player.played_dev_card_this_turn = True

    assert get_legal_actions(state) == [Action("roll_dice")]


def test_year_of_plenty_bank_constraints(state):
    state.phase = "roll_dice"
    state.players[0].development_cards = ["year_of_plenty"]

    state.bank["wood"] = 1
    state.bank["brick"] = 0
    state.bank["ore"] = 2

    available = get_legal_actions(state)

    assert Action(
        "play_year_of_plenty", ("wood", "wood")
    ) not in available

    assert Action(
        "play_year_of_plenty", ("brick", "ore")
    ) not in available

    assert Action(
        "play_year_of_plenty", ("wood", "ore")
    ) in available

    assert Action(
        "play_year_of_plenty", ("ore", "ore")
    ) in available


# ==========================================
# Main turn
# ==========================================

def test_main_turn_affordability_and_trading(state):
    state.phase = "main_turn"
    state.players[0].resources["wood"] = 4

    # The bank has no ore to trade
    state.bank["ore"] = 0

    available = get_legal_actions(state)
    names = {a.name for a in available}

    assert Action("end_turn") in available

    assert "build_road" not in names
    assert "build_settlement" not in names
    assert "build_city" not in names
    assert "buy_development_card" not in names

    assert Action(
        "trade_with_bank", ("wood", "wheat")
    ) in available

    assert Action(
        "trade_with_bank", ("wood", "ore")
    ) not in available

    assert all(
        a.args[0] != a.args[1]
        for a in available
        if a.name == "trade_with_bank"
    )


def test_generated_main_turn_actions_execute(state):
    place_first_settlement_and_road(state)

    state.current_player_id = 0
    state.phase = "main_turn"

    player = state.players[0]

    for resource in player.resources:
        player.resources[resource] = 8
        state.bank[resource] -= 8

    player.development_cards = [
        "knight", "monopoly",
        "year_of_plenty", "road_building"
    ]

    available = get_legal_actions(state)

    # Confirm several action categories are present
    names = {a.name for a in available}

    assert "build_road" in names
    assert "build_city" in names
    assert "buy_development_card" in names
    assert "trade_with_bank" in names
    assert "play_road_building" in names
    assert "end_turn" in names

    # Each generated action must execute successfully
    # when applied independently to the original state.
    for action in available:
        trial = copy.deepcopy(state)

        function = getattr(engine_actions, action.name)
        function(trial, *action.args)


# ==========================================
# Robber
# ==========================================

def test_move_robber_actions(state):
    state.phase = "move_robber"

    available = get_legal_actions(state)

    assert available
    assert all(a.name == "move_robber" for a in available)

    assert {a.args[0] for a in available} == {
        hexagon for hexagon in state.board.hexes
        if can_move_robber(state, hexagon)
    }

    assert all(
        a.args[0] != state.robber_hex
        for a in available
    )


# ==========================================
# Discard
# ==========================================


def test_sequential_discard_actions(state):
    state.phase = "discard"
    state.current_player_id = 1
    state.pending_discards = {0: 2, 1: 1}

    state.players[0].resources["wood"] = 2
    state.players[0].resources["brick"] = 1

    state.players[1].resources["sheep"] = 1
    state.players[1].resources["wheat"] = 1

    # Step 1: only player 0 can discard
    available = get_legal_actions(state)

    assert len(available) == 2
    assert all(
        action.name == "discard_resources"
        and action.args[0] == 0
        for action in available
    )

    # Execute player 0's discard
    engine_actions.discard_resources(state, *available[0].args)

    assert 0 not in state.pending_discards
    assert 1 in state.pending_discards
    assert state.phase == "discard"

    # Step 2: only player 1 can discard
    available = get_legal_actions(state)

    assert len(available) == 2
    assert all(
        action.name == "discard_resources"
        and action.args[0] == 1
        for action in available
    )

    # Execute player 1's discard
    engine_actions.discard_resources(state, *available[0].args)

    # Step 3: discarding is complete
    assert state.pending_discards == {}
    assert state.phase == "move_robber"

    # Next legal actions are robber movements
    available = get_legal_actions(state)

    assert available
    assert all(
        action.name == "move_robber"
        for action in available
    )

    assert state.current_player_id == 1


# ==========================================
# Free roads
# ==========================================

def test_road_building_actions(state):
    place_first_settlement_and_road(state)

    state.current_player_id = 0
    state.phase = "road_building"
    state.free_roads_remaining = 2
    state.road_building_return_phase = "main_turn"

    available = get_legal_actions(state)

    assert available
    assert all(a.name == "place_free_road"
               for a in available)

    assert {a.args[0] for a in available} == {
        edge for edge in state.board.edges
        if can_place_road(state, edge, 0)
    }

    # Execute the first free road
    engine_actions.place_free_road(
        state, *available[0].args
    )

    assert state.free_roads_remaining == 1
    assert state.phase == "road_building"

    # The next set of legal roads is recalculated
    assert get_legal_actions(state)


# ==========================================
# Terminal state and immutability
# ==========================================

def test_game_over_has_no_actions(state):
    state.phase = "game_over"
    state.winner_id = 0

    assert get_legal_actions(state) == []


def test_action_generation_does_not_modify_state(state):
    state.phase = "main_turn"
    state.players[0].resources["wood"] = 4

    before = copy.deepcopy(state)

    get_legal_actions(state)

    assert state.phase == before.phase
    assert state.players == before.players
    assert state.bank == before.bank
    assert state.development_card_deck == before.development_card_deck
    assert state.rng.getstate() == before.rng.getstate()

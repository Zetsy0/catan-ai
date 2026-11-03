from collections import Counter

from catan.game_engine.board import Board
from catan.game_engine.game import GameState

def test_bank_initialization():
    game = GameState(board=Board(seed=42), seed=123)

    assert game.bank == {
        "wood": 19,
        "brick": 19,
        "sheep": 19,
        "wheat": 19,
        "ore": 19
    }
    assert sum(game.bank.values()) == 95


def test_development_deck():
    game = GameState(board=Board(seed=42), seed=123)

    assert len(game.development_card_deck) == 25

    assert Counter(game.development_card_deck) == {
        "knight": 14,
        "victory_point": 5,
        "monopoly": 2,
        "year_of_plenty": 2,
        "road_building": 2
    }


def test_deck_reproducibility():
    game1 = GameState(board=Board(seed=42), seed=123)
    game2 = GameState(board=Board(seed=42), seed=123)

    assert game1.development_card_deck == game2.development_card_deck


def test_game_independence():
    game1 = GameState(board=Board(seed=42), seed=123)
    game2 = GameState(board=Board(seed=42), seed=123)

    # Modify the first game's bank
    game1.bank["wood"] -= 3

    assert game1.bank["wood"] == 16
    assert game2.bank["wood"] == 19

    # Draw a development card from the first game
    game1.development_card_deck.pop()

    assert len(game1.development_card_deck) == 24
    assert len(game2.development_card_deck) == 25

    # Check that players' resources are also independent
    game1.players[0].resources["ore"] = 5

    assert game2.players[0].resources["ore"] == 0


from catan.game_engine.board import Vertex

def test_victory_points():
    game = GameState(board=Board(seed=42), seed=123)
    player = game.players[0]

    # Initially, no points
    assert game.visible_victory_points(0) == 0
    assert game.total_victory_points(0) == 0

    # Build two settlements
    player.settlements.update({
        Vertex(0, 2),
        Vertex(4, 2)
    })

    assert game.visible_victory_points(0) == 2

    # Acquire a hidden VP card
    player.development_cards.append("victory_point")

    assert game.visible_victory_points(0) == 2
    assert game.total_victory_points(0) == 3

    # Award Longest Road
    game.longest_road_holder = 0

    assert game.visible_victory_points(0) == 4
    assert game.total_victory_points(0) == 5

    # Award Largest Army to the other player
    game.largest_army_holder = 1

    assert game.visible_victory_points(1) == 2
    assert game.total_victory_points(1) == 2



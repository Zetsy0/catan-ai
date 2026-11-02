
from catan.player import PlayerState


def test_player_initialization():
    player = PlayerState(player_id=0)

    assert player.total_resources == 0
    assert player.hidden_victory_points == 0
    assert len(player.settlements) == 0
    assert len(player.cities) == 0
    assert len(player.roads) == 0


def test_total_resources():
    player = PlayerState(player_id=0)

    player.resources["wood"] = 3
    player.resources["wheat"] = 2
    player.resources["ore"] = 1

    assert player.total_resources == 6

    player.resources["wood"] -= 2

    assert player.total_resources == 4


def test_hidden_victory_points():
    player = PlayerState(player_id=0)

    player.development_cards = [
        "knight", "victory_point", "victory_point"
    ]
    player.new_development_cards = [
        "monopoly", "victory_point", "knight"
    ]

    assert player.hidden_victory_points == 3

    player.new_development_cards.clear()

    assert player.hidden_victory_points == 2

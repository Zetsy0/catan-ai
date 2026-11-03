
import random
from collections import Counter

from catan.game_engine.board import Board, generate_hexes, get_neighbors, Hex


def test_hex_generation():
    hexes = generate_hexes(2)

    assert len(hexes) == 19
    assert Hex(0, 0) in hexes
    assert Hex(2, 1) not in hexes


def test_hex_adjacency():
    hexes = generate_hexes(2)

    assert len(get_neighbors(Hex(0, 0), hexes)) == 6
    assert len(get_neighbors(Hex(2, 0), hexes)) == 3


def test_board_geometry():
    board = Board(seed=42)

    assert len(board.hexes) == 19
    assert len(board.vertices) == 54
    assert len(board.edges) == 72
    assert len(board.ports) == 9

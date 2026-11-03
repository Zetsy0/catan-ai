
import pytest

from catan.game_engine.board import Board, Vertex, Hex, get_vertices
from catan.game_engine.game import GameState
from catan.game_engine.rules import (
    can_place_initial_settlement,
    valid_vertex,
    edge_connected,
    can_move_robber,
    can_place_road,
    can_place_settlement,
    can_place_city,
    get_trade_ratio,
    longest_road_length
)


@pytest.fixture
def game():
    return GameState(board=Board(seed=42), seed=123)


def test_empty_board(game):
    # Every vertex should initially be available
    assert all(
        can_place_initial_settlement(game, v)
        for v in game.board.vertices
    )


def test_occupied_vertex(game):
    vertex = Vertex(0, 2)
    game.players[0].settlements.add(vertex)

    # Neither player can build on an occupied vertex
    assert not valid_vertex(game, vertex)


def test_distance_rule(game):
    vertex = Vertex(0, 2)
    game.players[0].settlements.add(vertex)

    # All neighboring vertices must be unavailable
    assert all(
        not valid_vertex(game, neighbor)
        for neighbor in game.board.vertex_adjacency[vertex]
    )

    # A sufficiently distant vertex should remain available
    distant_vertex = next(
        v for v in game.board.vertices
        if v != vertex
        and v not in game.board.vertex_adjacency[vertex]
    )
    assert valid_vertex(game, distant_vertex)


def test_city_distance_rule(game):
    vertex = Vertex(0, 2)
    game.players[1].cities.add(vertex)

    assert not valid_vertex(game, vertex)

    assert all(
        not valid_vertex(game, neighbor)
        for neighbor in game.board.vertex_adjacency[vertex]
    )


def test_invalid_vertex(game):
    assert not valid_vertex(game, Vertex(999, 999))


def test_edge_connected(game):
    vertex = Vertex(0, 2)
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))

    # Initially, neither player has roads
    assert not edge_connected(game, vertex, 0)

    # Add a road for player 0
    edge = frozenset({vertex, neighbor})
    game.players[0].roads.add(edge)

    assert edge_connected(game, vertex, 0)
    assert edge_connected(game, neighbor, 0)

    # Player 1 still has no connecting road
    assert not edge_connected(game, vertex, 1)

def test_friendly_robber(game):
    hexagon = next(
        h for h, number in game.board.hex_numbers.items()
        if number == 6
    )

    vertex = next(iter(get_vertices(hexagon)))
    game.players[1].settlements.add(vertex)

    # Player 1 has only one visible VP
    assert not can_move_robber(game, hexagon)


def test_robber_unprotected_player(game):
    hexagon = next(
        h for h, number in game.board.hex_numbers.items()
        if number == 6
    )

    vertex = next(iter(get_vertices(hexagon)))
    game.players[1].settlements.add(vertex)

    # Give player 1 another 2 visible VPs
    game.largest_army_holder = 1

    assert can_move_robber(game, hexagon)

def test_road_connected_to_settlement(game):
    edge = next(iter(game.board.edges))
    vertex = next(iter(edge))

    game.players[0].settlements.add(vertex)

    assert can_place_road(game, edge, 0)

def test_road_connected_to_road(game):
    existing_edge = next(iter(game.board.edges))
    a, b = tuple(existing_edge)

    c = next(
        v for v in game.board.vertex_adjacency[b]
        if v != a
    )

    new_edge = frozenset({b, c})
    game.players[0].roads.add(existing_edge)

    assert can_place_road(game, new_edge, 0)


def test_road_blocked_by_opponent(game):
    existing_edge = next(iter(game.board.edges))
    a, b = tuple(existing_edge)

    c = next(
        v for v in game.board.vertex_adjacency[b]
        if v != a
    )

    new_edge = frozenset({b, c})

    game.players[0].roads.add(existing_edge)

    # Initially the connection is legal
    assert can_place_road(game, new_edge, 0)

    # Opponent blocks the connecting vertex
    game.players[1].settlements.add(b)

    assert not can_place_road(game, new_edge, 0)


def test_road_ending_at_opponent_settlement(game):
    existing_edge = next(iter(game.board.edges))
    a, b = tuple(existing_edge)

    c = next(
        v for v in game.board.vertex_adjacency[b]
        if v != a
    )

    new_edge = frozenset({b, c})

    game.players[0].roads.add(existing_edge)
    game.players[1].settlements.add(c)

    assert can_place_road(game, new_edge, 0)


@pytest.mark.parametrize("owner_id", [0, 1])
def test_road_occupied(game, owner_id):
    edge = next(iter(game.board.edges))

    game.players[0].settlements.add(next(iter(edge)))
    game.players[owner_id].roads.add(edge)

    assert not can_place_road(game, edge, 0)


def test_road_invalid_edge(game):
    edge = frozenset({
        Vertex(999, 999),
        Vertex(1000, 1000)
    })

    assert not can_place_road(game, edge, 0)


def test_road_piece_limit(game):
    edge = next(iter(game.board.edges))
    player = game.players[0]

    player.settlements.add(next(iter(edge)))

    other_edges = [e for e in game.board.edges if e != edge]

    # Give the player 14 roads
    player.roads.update(other_edges[:14])

    assert can_place_road(game, edge, 0)

    # Give the player their 15th road
    player.roads.add(other_edges[14])

    assert player.remaining_roads == 0
    assert not can_place_road(game, edge, 0)

def test_can_place_settlement(game):
    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))

    edge = frozenset({vertex, neighbor})
    game.players[0].roads.add(edge)

    assert can_place_settlement(game, vertex, 0)


def test_settlement_not_connected(game):
    vertex = next(iter(game.board.vertices))

    assert not can_place_settlement(game, vertex, 0)

@pytest.mark.parametrize("building", ["settlements", "cities"])
@pytest.mark.parametrize("at_vertex", [True, False])
def test_settlement_distance_rule(game, building, at_vertex):
    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))

    edge = frozenset({vertex, neighbor})
    game.players[0].roads.add(edge)

    # Place an opponent's building
    occupied_vertex = vertex if at_vertex else neighbor
    getattr(game.players[1], building).add(occupied_vertex)

    assert not can_place_settlement(game, vertex, 0)

def test_settlement_opponent_road(game):
    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))

    edge = frozenset({vertex, neighbor})
    game.players[1].roads.add(edge)

    assert not can_place_settlement(game, vertex, 0)

def test_settlement_piece_limit(game):
    vertex = next(iter(game.board.vertices))
    neighbor = next(iter(game.board.vertex_adjacency[vertex]))

    game.players[0].roads.add(frozenset({vertex, neighbor}))

    # Select 5 vertices away from the proposed location
    unavailable = game.board.vertex_adjacency[vertex] | {vertex}

    other_vertices = [
        v for v in game.board.vertices
        if v not in unavailable
    ]

    game.players[0].settlements.update(other_vertices[:5])

    assert game.players[0].remaining_settlements == 0
    assert not can_place_settlement(game, vertex, 0)

def test_settlement_invalid_vertex(game):
    vertex = Vertex(999, 999)

    assert not can_place_settlement(game, vertex, 0)


def test_can_place_city(game):
    vertex = next(iter(game.board.vertices))
    game.players[0].settlements.add(vertex)

    assert can_place_city(game, vertex, 0)


def test_city_requires_own_settlement(game):
    vertex = next(iter(game.board.vertices))

    # Empty vertex
    assert not can_place_city(game, vertex, 0)

    # Opponent's settlement
    game.players[1].settlements.add(vertex)
    assert not can_place_city(game, vertex, 0)

    # Already a city
    game.players[1].settlements.remove(vertex)
    game.players[0].cities.add(vertex)
    assert not can_place_city(game, vertex, 0)


def test_city_piece_limit(game):
    player = game.players[0]
    vertices = list(game.board.vertices)

    player.settlements.add(vertices[0])

    # Player already has four cities
    player.cities.update(vertices[1:5])

    assert player.remaining_cities == 0
    assert not can_place_city(game, vertices[0], 0)


def test_city_invalid_vertex(game):
    vertex = Vertex(999, 999)
    game.players[0].settlements.add(vertex)

    assert not can_place_city(game, vertex, 0)

def get_port_vertex(game, port_type):
    """Return one vertex connected to a port of the given type."""
    edge = next(
        edge for edge, kind in game.board.ports.items()
        if kind == port_type
    )
    return next(iter(edge))

def test_trade_ratio_no_port(game):
    # Player has no buildings at ports
    for resource in game.bank:
        assert get_trade_ratio(game, 0, resource) == 4

def test_trade_ratio_generic_port(game):
    vertex = get_port_vertex(game, "generic")
    game.players[0].settlements.add(vertex)

    # Generic port gives 3:1 for every resource
    for resource in game.bank:
        assert get_trade_ratio(game, 0, resource) == 3

    # Opponent doesn't benefit
    assert get_trade_ratio(game, 1, "wood") == 4

def test_trade_ratio_specialized_port(game):
    vertex = get_port_vertex(game, "ore")
    game.players[0].settlements.add(vertex)

    assert get_trade_ratio(game, 0, "ore") == 2
    assert get_trade_ratio(game, 0, "wood") == 4

def test_trade_ratio_city_port(game):
    vertex = get_port_vertex(game, "generic")
    game.players[0].cities.add(vertex)

    assert get_trade_ratio(game, 0, "wood") == 3

def test_trade_ratio_multiple_ports(game):
    player = game.players[0]

    generic_vertex = get_port_vertex(game, "generic")
    ore_vertex = get_port_vertex(game, "ore")

    player.settlements.add(generic_vertex)
    player.cities.add(ore_vertex)

    # Specialized port takes priority
    assert get_trade_ratio(game, 0, "ore") == 2

    # Other resources benefit from the generic port
    assert get_trade_ratio(game, 0, "brick") == 3

@pytest.fixture
def road_chain(game):
    """Create a chain of three connected roads."""
    vertices = [
        Vertex(1, 1),
        Vertex(0, 2),
        Vertex(-1, 1),
        Vertex(-1, -1),
    ]

    edges = [
        frozenset({a, b})
        for a, b in zip(vertices, vertices[1:])
    ]

    assert all(edge in game.board.edges for edge in edges)

    game.players[0].roads.update(edges)

    return game, vertices


def test_longest_road_empty(game):
    assert longest_road_length(game, 0) == 0


def test_longest_road_straight(road_chain):
    game, vertices = road_chain

    assert longest_road_length(game, 0) == 3
    assert longest_road_length(game, 1) == 0


def test_longest_road_branch(game):
    # Find a vertex with three neighbors
    center = next(
        v for v, neighbors in game.board.vertex_adjacency.items()
        if len(neighbors) == 3
    )

    # Create three branches from the same vertex
    for neighbor in game.board.vertex_adjacency[center]:
        game.players[0].roads.add(
            frozenset({center, neighbor})
        )

    # Three roads exist, but the longest route uses only two
    assert len(game.players[0].roads) == 3
    assert longest_road_length(game, 0) == 2


def test_longest_road_loop(game):
    # Build all six roads around the central hexagon
    vertices = get_vertices(Hex(0, 0))

    edges = {
        edge for edge in game.board.edges
        if edge.issubset(vertices)
    }

    assert len(edges) == 6

    game.players[0].roads.update(edges)

    # A complete loop counts all six roads
    assert longest_road_length(game, 0) == 6


@pytest.mark.parametrize("building", ["settlements", "cities"])
def test_longest_road_blocked_by_opponent(road_chain, building):
    game, vertices = road_chain

    # Opponent builds at an intermediate vertex
    blocked_vertex = vertices[1]
    getattr(game.players[1], building).add(blocked_vertex)

    # The original chain of 3 is split into lengths 1 and 2
    assert longest_road_length(game, 0) == 2


def test_longest_road_own_settlement_does_not_block(road_chain):
    game, vertices = road_chain

    game.players[0].settlements.add(vertices[1])

    # The player's own settlement doesn't interrupt the route
    assert longest_road_length(game, 0) == 3


def test_longest_road_disconnected(road_chain):
    game, vertices = road_chain

    # Add an isolated road elsewhere
    disconnected_edge = next(
        edge for edge in game.board.edges
        if edge.isdisjoint(vertices)
    )

    game.players[0].roads.add(disconnected_edge)

    # Four roads total, but longest connected route is three
    assert len(game.players[0].roads) == 4
    assert longest_road_length(game, 0) == 3

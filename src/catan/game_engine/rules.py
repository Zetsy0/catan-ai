from .board import Vertex, Edge, Hex, get_vertices
from .game import GameState

def can_place_initial_settlement(
        state: GameState,
        vertex: Vertex,
    ) -> bool:
    return valid_vertex(state, vertex)

def valid_vertex(
        state: GameState,
        vertex: Vertex
    ) -> bool :
    if vertex in state.board.vertices :
        neighboring_vertices = state.board.vertex_adjacency[vertex] | {vertex}
        for player in state.players.values() :
            if not player.cities.isdisjoint(neighboring_vertices)\
            or not player.settlements.isdisjoint(neighboring_vertices):
                return False
        return True
    else:
        return False

def edge_connected(
        state: GameState,
        vertex: Vertex,
        player_id: int,
    ) -> bool :
    if vertex not in state.board.vertices:
        return False
    else :
        for neighboring_vertex in state.board.vertex_adjacency[vertex] :
            if frozenset({vertex, neighboring_vertex}) in state.players[player_id].roads :
                return True
        return False

def can_place_settlement(
    state: GameState,
    vertex: Vertex,
    player_id: int
) -> bool:
    if state.players[player_id].remaining_settlements <= 0:
        return False

    if not valid_vertex(state, vertex):
        return False

    return edge_connected(state, vertex, player_id)


def can_place_initial_road(
    state: GameState,
    edge: Edge,
) -> bool:
    if edge not in state.board.edges:
        return False
    else :
        if (state.pending_initial_settlement in edge) and all(edge not in player.roads for player in state.players.values()):
            return True
        else:
            return False

def can_place_road(
        state: GameState,
        edge: Edge,
        player_id: int
)-> bool:

    player = state.players[player_id]

    if player.remaining_roads <= 0 :
        return False 
    
    if edge not in state.board.edges:
        return False
    
    if any(edge in p.roads for p in state.players.values()):
        return False

    for vertex in edge:
        if any(
            vertex in opponent.settlements or vertex in opponent.cities
            for pid, opponent in state.players.items()
            if pid != player_id
        ):
            continue
        if vertex in player.settlements or vertex in player.cities:
            return True
        for neighboring_vertex in state.board.vertex_adjacency[vertex] :
            if frozenset({vertex, neighboring_vertex}) in player.roads :
                return True
    return False

def can_place_city(state: GameState, vertex: Vertex, player_id: int) -> bool:
    if vertex not in state.board.vertices :
        return False

    if state.players[player_id].remaining_cities <= 0 :
        return False
    
    if vertex not in state.players[player_id].settlements :
        return False

    return True

def can_move_robber(state: GameState, hexagon: Hex) -> bool:
    if hexagon not in state.board.hexes :
        return False
    
    if hexagon == state.robber_hex :
        return False
    
    for vertex in get_vertices(hexagon) :
        for player_id in state.players :
            if (vertex in state.players[player_id].settlements or vertex in state.players[player_id].cities)\
                and state.visible_victory_points(player_id) <= 2 :
                return False
    return True


def get_trade_ratio(
    state: GameState,
    player_id: int,
    resource: str
) -> int:
    player = state.players[player_id]
    buildings = player.settlements | player.cities

    ratio = 4

    for edge, port_type in state.board.ports.items():
        if edge.isdisjoint(buildings):
            continue

        if port_type == resource:
            return 2

        if port_type == "generic":
            ratio = 3

    return ratio


def longest_road_length(state: GameState, player_id: int) -> int:
    player = state.players[player_id]

    if not player.roads:
        return 0

    # 1. Build adjacency dictionary for the player's roads
    road_adjacency: dict[Vertex, set[Edge]] = {}

    for edge in player.roads:
        for vertex in edge:
            road_adjacency.setdefault(vertex, set()).add(edge)

    # 2. Identify vertices blocked by opponents
    blocked_vertices = set()

    for opponent_id, opponent in state.players.items():
        if opponent_id != player_id:
            blocked_vertices.update(opponent.settlements)
            blocked_vertices.update(opponent.cities)

    # 3. Depth-First Search
    def dfs(vertex: Vertex, used_edges: set[Edge]) -> int:

        # An opponent's building prevents continuing a road
        if vertex in blocked_vertices and used_edges:
            return 0

        longest = 0

        for edge in road_adjacency.get(vertex, set()):

            # Cannot use the same road twice
            if edge in used_edges:
                continue

            # Find the other endpoint of this edge
            next_vertex = next(iter(edge - {vertex}))

            # Explore this road
            used_edges.add(edge)

            length = 1 + dfs(next_vertex, used_edges)
            longest = max(longest, length)

            # Backtrack to explore other possibilities
            used_edges.remove(edge)

        return longest

    # 4. Try every possible starting vertex
    return max(
        dfs(vertex, set())
        for vertex in road_adjacency
    )


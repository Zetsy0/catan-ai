from dataclasses import dataclass

CORNER_OFFSETS = [
    (1, 1), (0, 2), (-1, 1),
    (-1, -1), (0, -2), (1, -1)
]

@dataclass(frozen=True)
class Hex:
    q: int
    r: int

def generate_hexes(radius: int = 2) -> set[Hex]:
    hexes = set()
    for q in range(-radius,radius+1) :
        for r in range(-radius,radius+1) :
            if max(abs(q),abs(r),abs(r+q)) <= radius :
                hexes.add(Hex(q,r))
    return hexes

def get_neighbors(hexagon: Hex, hexes: set[Hex]) -> set[Hex]:
    potential_neighbors_coords = [(1,0),(-1,0),(0,1),(-1,1),(0,-1),(1,-1)]
    neighbors = set()
    for dq,dr in potential_neighbors_coords :
        neighbor = Hex(hexagon.q + dq, hexagon.r + dr)
        if neighbor in hexes :
            neighbors.add(neighbor)
    return neighbors

@dataclass(frozen=True)
class Vertex:
    x: int
    y: int

def axial_to_cartesian(q,r) :
    return 2 * q + r, 3 * r

def cartesian_to_axial(x,y) :
    return x/2 - y/6, y/3

def get_vertices(hexagon: Hex) -> set[Vertex]:
    corner_offsets = [
        (1, 1), (0, 2), (-1, 1),
        (-1, -1), (0, -2), (1, -1)
    ]
    x,y = axial_to_cartesian(hexagon.q,hexagon.r)
    vertices = set()
    for dx,dy in corner_offsets :
        vertices.add(Vertex(x + dx,y + dy))
    return vertices

def generate_vertices(hexes: set[Hex]) -> set[Vertex]:
    vertices = set()
    for hexagon in hexes :
        vertices.update(get_vertices(hexagon))
    return vertices

Edge = frozenset[Vertex]

def get_edges(hexagon: Hex) -> set[Edge]:
    corner_offsets = [
        (1, 1), (0, 2), (-1, 1),
        (-1, -1), (0, -2), (1, -1)
    ]
    edges = set()
    vertex_list = []
    x,y = axial_to_cartesian(hexagon.q, hexagon.r)
    for dx, dy in corner_offsets :
        vertex_list.append(Vertex(x + dx, y + dy))
    for i in range(6) :
        edges.add(frozenset({vertex_list[i],vertex_list[(i+1)%6]}))
    return edges

def generate_edges(hexes: set[Hex]) -> set[Edge]:
    edges = set()
    for hexagon in hexes:
        edges.update(get_edges(hexagon))
    return edges

if __name__ == "__main__":
    hexes = generate_hexes(2)
    vertices = generate_vertices(hexes)
    edges = generate_edges(hexes)

    assert len(edges) == 72

    assert all(edge <= vertices for edge in edges)

    assert len(
        get_edges(Hex(0, 0)) &
        get_edges(Hex(1, 0))
    ) == 1

    print("All tests passed!")

    
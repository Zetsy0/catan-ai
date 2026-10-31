from dataclasses import dataclass
from collections import Counter
import random

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
    x,y = axial_to_cartesian(hexagon.q,hexagon.r)
    vertices = set()
    for dx,dy in CORNER_OFFSETS :
        vertices.add(Vertex(x + dx,y + dy))
    return vertices

def generate_vertices(hexes: set[Hex]) -> set[Vertex]:
    vertices = set()
    for hexagon in hexes :
        vertices.update(get_vertices(hexagon))
    return vertices

Edge = frozenset[Vertex]

def get_edges(hexagon: Hex) -> set[Edge]:
    edges = set()
    vertex_list = []
    x,y = axial_to_cartesian(hexagon.q, hexagon.r)
    for dx, dy in CORNER_OFFSETS :
        vertex_list.append(Vertex(x + dx, y + dy))
    for i in range(6) :
        edges.add(frozenset({vertex_list[i],vertex_list[(i+1)%6]}))
    return edges

def generate_edges(hexes: set[Hex]) -> set[Edge]:
    edges = set()
    for hexagon in hexes:
        edges.update(get_edges(hexagon))
    return edges

def generate_vertex_adjacency(vertices: set[Vertex], edges: set[Edge] )\
      -> dict[Vertex, set[Vertex]]:
    adjacency_dict = {vertex: set() for vertex in vertices}
    for edge in edges :
        v1, v2 = edge
        adjacency_dict[v1].add(v2)
        adjacency_dict[v2].add(v1)
    return adjacency_dict

def generate_vertex_hex_adjacency(vertices: set[Vertex], hexes: set[Hex])\
      -> dict[Vertex, set[Hex]]:
    vertex_hex_adjacency_dict = {vertex: set() for vertex in vertices}
    for hexagon in hexes:
        surrounding_vertices = get_vertices(hexagon)
        for v in surrounding_vertices :
            vertex_hex_adjacency_dict[v].add(hexagon)
    return vertex_hex_adjacency_dict

class Board:
    def __init__(self, radius: int = 2):
        self.radius = radius
        self.hexes = generate_hexes(radius)
        self.vertices = generate_vertices(self.hexes)

        self.edges = generate_edges(self.hexes)
        self.vertex_adjacency = generate_vertex_adjacency(self.vertices, self.edges)
        self.vertex_hex_adjacency = generate_vertex_hex_adjacency(self.vertices, self.hexes)



def generate_terrain(hexes: set[Hex], rng: random.Random) -> dict[Hex, str | None]:
    if len(hexes) != 19:
        raise ValueError("Resource generation requires exactly 19 hexagons.")
    sorted_hexes = sorted(hexes, key=lambda h: (h.q, h.r))
    terrain_list = ["ore"] * 3 + ["wheat"] * 4 + ["sheep"] * 4 + ["wood"] * 4 + ["brick"] * 3 + [None]
    rng.shuffle(terrain_list)
    terrain_dict = {hexagon: terrain_list[i] for i,hexagon in enumerate(sorted_hexes)}
    return terrain_dict

def generate_numbers(hexes: set[Hex], hex_resources: dict[Hex, str | None],\
    rng: random.Random, max_attempts: int = 100) -> dict[Hex, int | None] :

    sorted_hexes = sorted(hexes, key=lambda h: (h.q, h.r))
    productive_hexes = [h for h in sorted_hexes if hex_resources[h] is not None]
    tokens = [2] + [3] * 2 + [4] * 2 + [5] * 2 + [6] * 2 + [8] * 2 + [9] * 2 + [10] * 2 + [11] * 2 + [12]

    for attempt in range(max_attempts):
        numbers_dict: dict[Hex, int | None] = {hexagon: None for hexagon in sorted_hexes}
        rng.shuffle(tokens)

        for hexagon, token in zip(productive_hexes, tokens):
            numbers_dict[hexagon] = token

        if is_valid_number_placement(numbers_dict, hexes):
            return numbers_dict

    raise RuntimeError("Could not generate a valid board")

def is_valid_number_placement(numbers: dict[Hex, int | None], hexes: set[Hex]) -> bool:
    hexes_6_8 = {hexagon for hexagon, number in numbers.items() if number in (6,8)}
    for hexagon in hexes_6_8 :
        neighbors = get_neighbors(hexagon, hexes)
        if not hexes_6_8.isdisjoint(neighbors) :
            return False
    return True

def get_coastal_edges(hexes: set[Hex]) -> set[Edge]:
    coastal_edges = set()
    for hexagon in hexes:
        coastal_edges ^= get_edges(hexagon)
    return coastal_edges

def order_coastal_edges(coastal_edges: set[Edge]) -> list[Edge]:
    # Sorting the coastal edges
    edge_0 = frozenset({
        Vertex(5, -1),
        Vertex(5, 1)
    })
    vertex_0 = Vertex(5, -1)
    current_edge = edge_0
    current_vertex = vertex_0
    ordered_coastal_edges = [current_edge]
    for _ in range(len(coastal_edges) - 1):
        next_edge = next(edge for edge in coastal_edges if current_vertex in edge and edge != current_edge)
        current_vertex = next(vertex for vertex in next_edge if vertex != current_vertex)
        current_edge = next_edge
        ordered_coastal_edges.append(current_edge)
    return ordered_coastal_edges

def generate_ports_location(ordered_coastal_edges: list[Edge], rng: random.Random) -> list[Edge]:
    port_indices = [0, 3, 7, 10, 13, 17, 20, 23, 27]
    offset = rng.choice([0, 5]) # shifts the corners by 1/6-th of a turn

    port_edges = [ordered_coastal_edges[(i + offset) % 30] for i in port_indices]
    return port_edges

def assign_port_types(port_edges: list[Edge], rng: random.Random) -> dict[Edge, str]:
    port_types = ["generic"] * 4 + ["wheat","ore","sheep","brick","wood"]
    rng.shuffle(port_types)
    port_dict = {edge: port_type for edge, port_type in zip(port_edges, port_types)}
    return port_dict


import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


def plot_board(hexes, resources, numbers, ports):
    colors = {
        "wood": "#36854b",
        "brick": "#bc6250",
        "sheep": "#a5ce76",
        "wheat": "#e8c65c",
        "ore": "#8f9ba8",
        None: "#e3d4b5"
    }

    fig, ax = plt.subplots(figsize=(9, 9))

    def plot_coords(v):
        return (v.x * math.sqrt(3) / 2, v.y / 2)

    # Draw hexagons
    for hexagon in hexes:
        vertices = [
            Vertex(
                axial_to_cartesian(hexagon.q, hexagon.r)[0] + dx,
                axial_to_cartesian(hexagon.q, hexagon.r)[1] + dy
            )
            for dx, dy in CORNER_OFFSETS
        ]

        corners = [plot_coords(v) for v in vertices]
        ax.add_patch(Polygon(
            corners,
            facecolor=colors[resources[hexagon]],
            edgecolor="black"
        ))

        x, y = axial_to_cartesian(hexagon.q, hexagon.r)
        cx, cy = plot_coords(Vertex(x, y))

        ax.text(cx, cy + 0.25, str(resources[hexagon]),
                ha="center", va="center", fontsize=9)

        number = numbers[hexagon]
        if number is not None:
            ax.text(cx, cy - 0.2, str(number),
                    ha="center", va="center",
                    fontsize=14, fontweight="bold",
                    color="red" if number in (6, 8) else "black")

    # Draw ports
    for edge, port_type in ports.items():
        v1, v2 = tuple(edge)
        x1, y1 = plot_coords(v1)
        x2, y2 = plot_coords(v2)

        ax.plot([x1, x2], [y1, y2],
                color="blue", linewidth=5)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        distance = math.hypot(mx, my)

        label = "3:1" if port_type == "generic" else f"2:1 {port_type}"

        ax.text(mx + 0.5 * mx / distance,
                my + 0.5 * my / distance,
                label, ha="center", va="center", fontsize=9)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.25)
    ax.axis("off")
    plt.show()




if __name__ == "__main__":
    
    rng = random.Random(42)

    hexes = generate_hexes(2)
    resources = generate_terrain(hexes, rng)
    numbers = generate_numbers(hexes, resources, rng)

    coastal_edges = get_coastal_edges(hexes)
    ordered_edges = order_coastal_edges(coastal_edges)
    port_edges = generate_ports_location(ordered_edges, rng)
    ports = assign_port_types(port_edges, rng)

    plot_board(hexes, resources, numbers, ports)

import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from .board import Board, Vertex, CORNER_OFFSETS, axial_to_cartesian


def plot_board( board: Board, show: bool = True, save: bool = False, filename: str = "board.png") -> None:
    colors = {
        "wood": "#36854b",
        "brick": "#bc6250",
        "sheep": "#a5ce76",
        "wheat": "#d9b64e",
        "ore": "#8f9ba8",
        None: "#e3d4b5"
    }

    fig, ax = plt.subplots(figsize=(9, 9))

    def plot_coords(v):
        return (v.x * math.sqrt(3) / 2, v.y / 2)

    # Draw hexagons
    for hexagon in board.hexes:
        x, y = axial_to_cartesian(hexagon.q, hexagon.r)

        vertices = [Vertex(x + dx, y + dy) for dx, dy in CORNER_OFFSETS]

        corners = [plot_coords(v) for v in vertices]

        ax.add_patch(Polygon(
            corners,
            facecolor=colors[board.hex_resources[hexagon]],
            edgecolor="black"
        ))

        x, y = axial_to_cartesian(hexagon.q, hexagon.r)
        cx, cy = plot_coords(Vertex(x, y))

        ax.text(cx, cy + 0.25, str(board.hex_resources[hexagon]),
                ha="center", va="center", fontsize=9)

        number = board.hex_numbers[hexagon]
        if number is not None:
            ax.text(cx, cy - 0.2, str(number),
                    ha="center", va="center",
                    fontsize=14, fontweight="bold",
                    color="red" if number in (6, 8) else "black")

    # Draw ports
    for edge, port_type in board.ports.items():
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
    if save:
        fig.savefig(filename, dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    plt.close(fig)

if __name__ == "__main__":
    board = Board(seed=42)
    plot_board(board)

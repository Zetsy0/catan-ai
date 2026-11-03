import math
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from .board import Board, Vertex, CORNER_OFFSETS, axial_to_cartesian
from .game import GameState


def plot_board( board: Board, show: bool = True, save: bool = False, filename: str = "board.png", state: GameState | None = None) -> None:
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
                color="#6b7280", linewidth=5)

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        distance = math.hypot(mx, my)

        label = "3:1" if port_type == "generic" else f"2:1 {port_type}"

        ax.text(mx + 0.5 * mx / distance,
                my + 0.5 * my / distance,
                label, ha="center", va="center", fontsize=9)

    if state is not None:
        player_colors = {
            0: "#2563eb",  # Blue
            1: "#dc2626",  # Red
        }

        for player_id, player in state.players.items():
            color = player_colors[player_id]

            # Draw roads
            for edge in player.roads:
                v1, v2 = tuple(edge)
                x1, y1 = plot_coords(v1)
                x2, y2 = plot_coords(v2)

                ax.plot(
                    [x1, x2], [y1, y2],
                    color=color,
                    linewidth=6,
                    solid_capstyle="round",
                    zorder=4,
                )

            # Draw settlements as circles
            for vertex in player.settlements:
                x, y = plot_coords(vertex)

                ax.scatter(
                    x, y,
                    s=130,
                    marker="o",
                    color=color,
                    edgecolors="black",
                    zorder=5,
                )

            # Draw cities as squares
            for vertex in player.cities:
                x, y = plot_coords(vertex)

                ax.scatter(
                    x, y,
                    s=210,
                    marker="s",
                    color=color,
                    edgecolors="black",
                    zorder=5,
                )

        # Draw the robber
        x, y = axial_to_cartesian(
            state.robber_hex.q,
            state.robber_hex.r
        )
        rx, ry = plot_coords(Vertex(x, y))

        ax.scatter(
            rx, ry,
            s=250,
            marker="X",
            color="black",
            edgecolors="white",
            zorder=6,
        )

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
    from .legal_actions import get_legal_actions
    from .dispatcher import execute_action

    state = GameState(board=Board(seed=42), seed=42)

    # Place the first settlement
    action = get_legal_actions(state)[0]
    execute_action(state, action)

    # Place its connected road
    action = get_legal_actions(state)[0]
    execute_action(state, action)

    plot_board(state.board, state=state)


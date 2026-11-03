import math
import matplotlib.pyplot as plt

from typing import cast
from matplotlib.patches import Polygon
from matplotlib.axes import Axes
from matplotlib.patches import Circle
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure

from .game import GameState
from .legal_actions import Action, get_legal_actions
from .dispatcher import execute_action

from .board import Board, Vertex, CORNER_OFFSETS, axial_to_cartesian
from .game import GameState


def plot_coords(v):
        return (v.x * math.sqrt(3) / 2, v.y / 2)

def plot_board( board: Board, show: bool = True, save: bool = False, filename: str = "board.png", state: GameState | None = None,
               ax: Axes | None = None,
               ) -> None:
    colors = {
        "wood": "#36854b",
        "brick": "#bc6250",
        "sheep": "#a5ce76",
        "wheat": "#d9b64e",
        "ore": "#8f9ba8",
        None: "#e3d4b5"
    }

    owns_figure = ax is None

    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 9))
    else:
        fig = cast(Figure, ax.figure)

    ax.clear()

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

    if show and owns_figure:
        plt.show()

    if owns_figure:
        plt.close(fig)


def interactive_board(state: GameState) -> None:
    fig, ax = plt.subplots(figsize=(9, 9))

    # Associate each clickable circle with its legal action
    targets: dict[Circle, Action] = {}

    vertex_actions = {
        "place_initial_settlement",
        "build_settlement",
        "build_city",
    }

    edge_actions = {
        "place_initial_road",
        "build_road",
        "place_free_road",
    }

    def redraw() -> None:
        targets.clear()

        # Draw the current board and player pieces
        plot_board(
            state.board,
            state=state,
            show=False,
            ax=ax,
        )

        # Add clickable circles for legal placements
        for action in get_legal_actions(state):

            if action.name in vertex_actions:
                vertex = action.args[0]
                x, y = plot_coords(vertex)
                radius = 0.22
                color = "#16a34a"

            elif action.name in edge_actions:
                edge = action.args[0]
                v1, v2 = tuple(edge)

                x1, y1 = plot_coords(v1)
                x2, y2 = plot_coords(v2)

                x = (x1 + x2) / 2
                y = (y1 + y2) / 2

                radius = 0.22
                color = "#f59e0b"

            elif action.name == "move_robber":
                hexagon = action.args[0]

                vx, vy = axial_to_cartesian(
                    hexagon.q, hexagon.r
                )
                x, y = plot_coords(Vertex(vx, vy))

                radius = 0.45
                color = "#374151"

            else:
                continue

            circle = Circle(
                (x, y),
                radius=radius,
                facecolor=to_rgba(color, 0.15),
                edgecolor=color,
                linewidth=2,
                zorder=20,
                picker=True,
            )

            ax.add_patch(circle)
            targets[circle] = action

        ax.set_title(
            f"Player {state.current_player_id} — "
            f"{state.phase}"
        )

        fig.canvas.draw_idle()

    def on_pick(event) -> None:
        action = targets.get(event.artist)

        if action is None:
            return

        # Execute the selected action
        execute_action(state, action)

        # Update the board and legal positions
        redraw()

    fig.canvas.mpl_connect("pick_event", on_pick)

    redraw()
    plt.show()

if __name__ == "__main__":
    state = GameState(
        board=Board(seed=42),
        seed=42
    )

    interactive_board(state)


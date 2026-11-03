"""Matplotlib-only board visualization.

The engine never imports this module; graphical dependencies stay optional.
``plot_board`` supports standalone usage and drawing into existing Axes.
"""
from __future__ import annotations

import math
from typing import cast

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import Polygon

from .game_engine.board import Board, Vertex, CORNER_OFFSETS, axial_to_cartesian
from .game_engine.game import GameState


RESOURCE_COLORS = {
    "wood": "#36854b",
    "brick": "#bc6250",
    "sheep": "#a5ce76",
    "wheat": "#d9b64e",
    "ore": "#8f9ba8",
    None: "#e3d4b5",
}
PLAYER_COLORS = {0: "#2563eb", 1: "#dc2626"}


def plot_coords(vertex: Vertex) -> tuple[float, float]:
    return (vertex.x * math.sqrt(3) / 2, vertex.y / 2)


def plot_board(
    board: Board,
    show: bool = True,
    save: bool = False,
    filename: str = "board.png",
    state: GameState | None = None,
    ax: Axes | None = None,
) -> None:
    """Plot terrain and ports, optionally with game pieces, on an existing axis.

    When ``ax`` is given, the caller owns its figure; do not show/close it here.
    """
    owns_figure = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(9, 9))
    else:
        fig = cast(Figure, ax.figure)
    ax.clear()

    for hexagon in board.hexes:
        x, y = axial_to_cartesian(hexagon.q, hexagon.r)
        vertices = [Vertex(x + dx, y + dy) for dx, dy in CORNER_OFFSETS]
        ax.add_patch(Polygon(
            [plot_coords(v) for v in vertices],
            facecolor=RESOURCE_COLORS[board.hex_resources[hexagon]],
            edgecolor="black",
            zorder=1,
        ))
        cx, cy = plot_coords(Vertex(x, y))
        ax.text(cx, cy + 0.25, str(board.hex_resources[hexagon]),
                ha="center", va="center", fontsize=9, zorder=2)
        number = board.hex_numbers[hexagon]
        if number is not None:
            ax.text(cx, cy - 0.2, str(number),
                    ha="center", va="center", fontsize=14,
                    fontweight="bold", color="red" if number in (6, 8) else "black",
                    zorder=2)

    for edge, port_type in board.ports.items():
        v1, v2 = tuple(edge)
        x1, y1 = plot_coords(v1)
        x2, y2 = plot_coords(v2)
        ax.plot([x1, x2], [y1, y2], color="#6b7280", linewidth=5, zorder=3)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        distance = math.hypot(mx, my)
        label = "3:1" if port_type == "generic" else f"2:1 {port_type}"
        if distance:
            mx += 0.5 * mx / distance
            my += 0.5 * my / distance
        ax.text(mx, my, label, ha="center", va="center", fontsize=9, zorder=4)

    if state is not None:
        for player_id, player in state.players.items():
            color = PLAYER_COLORS[player_id]
            for edge in player.roads:
                v1, v2 = tuple(edge)
                x1, y1 = plot_coords(v1)
                x2, y2 = plot_coords(v2)
                ax.plot([x1, x2], [y1, y2], color=color, linewidth=6,
                        solid_capstyle="round", zorder=5)
            for vertex in player.settlements:
                x, y = plot_coords(vertex)
                ax.scatter(x, y, s=130, marker="o", color=color,
                           edgecolors="black", zorder=6)
            for vertex in player.cities:
                x, y = plot_coords(vertex)
                ax.scatter(x, y, s=210, marker="s", color=color,
                           edgecolors="black", zorder=6)
        x, y = axial_to_cartesian(state.robber_hex.q, state.robber_hex.r)
        rx, ry = plot_coords(Vertex(x, y))
        ax.scatter(rx, ry, s=250, marker="X", color="black",
                   edgecolors="white", zorder=7)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.margins(0.25)
    ax.axis("off")

    if save:
        fig.savefig(filename, dpi=150, bbox_inches="tight")
    if owns_figure:
        if show:
            plt.show()
        plt.close(fig)


if __name__ == "__main__":
    plot_board(Board(seed=42))

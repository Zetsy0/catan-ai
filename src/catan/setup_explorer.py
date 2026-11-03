"""Interactive explorer for the A–B–B–A Catan setup heuristic.

Install into ``src/catan/setup_explorer.py`` and run from the project root:

    python -m catan.setup_explorer --seed 7

Each legal settlement vertex displays the score used by the paired-settlement
heuristic. Legal initial roads display their expansion heuristic score instead.
Click a marked vertex or road midpoint to play it; use Undo to reverse a step.
Both players are human-controlled for this exploratory tool.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent, PickEvent
from matplotlib.colors import Normalize
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.widgets import Button

from .game_engine.board import Board, Vertex
from .game_engine.dispatcher import execute_action
from .game_engine.game import GameState
from .game_engine.legal_actions import Action, get_legal_actions
from .strategies.setup_heuristic import (
    RESOURCES,
    SetupWeights,
    pair_features,
    production_profile,
    score_initial_road,
    score_pair,
)
from .visualization import plot_board, plot_coords


@dataclass(frozen=True)
class ScoredChoice:
    action: Action
    score: float
    best_partner: Vertex | None = None


def score_setup_choices(
    state: GameState, weights: SetupWeights | None = None
) -> list[ScoredChoice]:
    """Score legal setup choices exactly as the heuristic agent does.

    For a first settlement, use the mean of the four best partner scores for
    A's opening, and the highest partner score for B's opening. For a second
    settlement, evaluate the actual pair. For roads, use score_initial_road.
    """
    if weights is None:
        weights = SetupWeights()
    actions = get_legal_actions(state)
    if state.phase == "setup_road":
        return [ScoredChoice(a, score_initial_road(state, a)) for a in actions]
    if state.phase != "setup_settlement":
        return []

    existing = state.players[state.current_player_id].settlements
    choices: list[ScoredChoice] = []
    if existing:
        first = next(iter(existing))
        return [ScoredChoice(a, score_pair(state, first, a.args[0], weights))
                for a in actions]

    count = 4 if state.setup_step == 0 else 1
    for action in actions:
        first = action.args[0]
        partners = [other.args[0] for other in actions
                    if other.args[0] != first
                    and other.args[0] not in state.board.vertex_adjacency[first]]
        if not partners:
            choices.append(ScoredChoice(action, float("-inf")))
            continue
        scored_partners = sorted(
            ((score_pair(state, first, second, weights), second)
             for second in partners),
            key=lambda item: (-item[0], item[1].x, item[1].y),
        )
        score = sum(s for s, _ in scored_partners[:count]) / min(count, len(scored_partners))
        choices.append(ScoredChoice(action, score, scored_partners[0][1]))
    return choices


class SetupExplorer:
    """Matplotlib window for manually trying setup actions and undoing them."""

    def __init__(self, seed: int = 7, weights: SetupWeights | None = None,
                 show: bool = True):
        self.seed = seed
        self.weights = weights or SetupWeights()
        self.state = GameState(board=Board(seed=seed), seed=seed)
        self.history: list[GameState] = []
        self.action_history: list[str] = []
        self.candidates: list[ScoredChoice] = []
        self.targets: dict[Circle, ScoredChoice] = {}
        self.hovered: ScoredChoice | None = None

        self.fig: Figure = plt.figure(figsize=(15.5, 9))
        if self.fig.canvas.manager is not None:
            self.fig.canvas.manager.set_window_title(f"Catan setup explorer — seed {seed}")
        self.ax: Axes = self.fig.add_axes((0.035, 0.075, 0.71, 0.89))
        self.panel: Axes = self.fig.add_axes((0.76, 0.19, 0.225, 0.76))
        undo_ax = self.fig.add_axes((0.77, 0.105, 0.095, 0.065))
        reset_ax = self.fig.add_axes((0.88, 0.105, 0.095, 0.065))
        self.undo_button = Button(undo_ax, "Undo (U)")
        self.reset_button = Button(reset_ax, "Reset (R)")
        self.undo_button.on_clicked(self.undo)
        self.reset_button.on_clicked(self.reset)

        self.fig.canvas.mpl_connect("pick_event", self.on_pick)
        self.fig.canvas.mpl_connect("motion_notify_event", self.on_hover)
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)
        self.redraw()
        if show:
            plt.show()

    def current_choices(self) -> list[ScoredChoice]:
        return self.candidates

    def apply_choice(self, choice: ScoredChoice) -> None:
        if choice.action not in get_legal_actions(self.state):
            raise ValueError("This choice is no longer legal")
        previous = deepcopy(self.state)
        execute_action(self.state, choice.action)
        self.history.append(previous)
        location = choice.action.args[0]
        label = (f"{choice.action.name} {location}"
                 f" (score {choice.score:.3f})")
        self.action_history.append(label)
        self.hovered = None
        self.redraw()

    def undo(self, _event: Any = None) -> None:
        if not self.history:
            return
        self.state = self.history.pop()
        self.action_history.pop()
        self.hovered = None
        self.redraw()

    def reset(self, _event: Any = None) -> None:
        self.state = GameState(board=Board(seed=self.seed), seed=self.seed)
        self.history.clear()
        self.action_history.clear()
        self.hovered = None
        self.redraw()

    def on_key(self, event: KeyEvent) -> None:
        if event.key in ("u", "ctrl+z", "cmd+z"):
            self.undo()
        elif event.key == "r":
            self.reset()

    def on_pick(self, event: PickEvent) -> None:
        choice = self.targets.get(event.artist)
        if choice is not None:
            self.apply_choice(choice)

    def on_hover(self, event: MouseEvent) -> None:
        if event.inaxes != self.ax:
            found = None
        else:
            found = next(
                (choice for circle, choice in self.targets.items()
                 if circle.contains(event)[0]), None
            )
        if found is self.hovered:
            return
        self.hovered = found
        self.draw_panel()
        self.fig.canvas.draw_idle()

    def redraw(self) -> None:
        self.candidates = score_setup_choices(self.state, self.weights)
        self.targets.clear()
        plot_board(self.state.board, state=self.state, show=False, ax=self.ax)

        # Keep a fixed view, so scores and targets do not move when the
        # candidate set changes during the A–B–B–A sequence.
        coords = [plot_coords(vertex) for vertex in self.state.board.vertices]
        self.ax.set_xlim(min(x for x, _ in coords) - 1.0,
                         max(x for x, _ in coords) + 1.0)
        self.ax.set_ylim(min(y for _, y in coords) - 0.95,
                         max(y for _, y in coords) + 0.95)

        finite_scores = [c.score for c in self.candidates if c.score != float("-inf")]
        low = min(finite_scores, default=0)
        high = max(finite_scores, default=1)
        norm = Normalize(vmin=low, vmax=high if high > low else low + 1)
        best = max(finite_scores, default=float("-inf"))
        settlement_phase = self.state.phase == "setup_settlement"

        for choice in self.candidates:
            if settlement_phase:
                x, y = plot_coords(choice.action.args[0])
                radius = 0.25
            else:
                v1, v2 = tuple(choice.action.args[0])
                x1, y1 = plot_coords(v1)
                x2, y2 = plot_coords(v2)
                x, y = (x1 + x2) / 2, (y1 + y2) / 2
                radius = 0.22

            color = plt.get_cmap("RdYlGn")(norm(choice.score))
            is_best = abs(choice.score - best) < 1e-9
            circle = Circle(
                (x, y), radius,
                facecolor=(*color[:3], 0.37),
                edgecolor="#111827" if is_best else (*color[:3], 1.0),
                linewidth=2.9 if is_best else 1.5,
                zorder=20, picker=True,
            )
            self.ax.add_patch(circle)
            self.targets[circle] = choice
            self.ax.annotate(
                f"{choice.score:.2f}", (x, y),
                xytext=(0, 15 if settlement_phase else 13),
                textcoords="offset points", ha="center", va="center",
                fontsize=7.0 if settlement_phase else 7.5,
                color="#111827", fontweight="bold" if is_best else "normal",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": .84, "pad": .8},
                zorder=21,
            )

        if self.state.phase.startswith("setup_"):
            label = ("Click a numbered VERTEX to place a settlement"
                     if settlement_phase else
                     "Click a numbered EDGE MIDPOINT to place a road")
            self.ax.set_title(label, fontsize=13, pad=12)
        else:
            self.ax.set_title("Setup complete — use Undo or Reset to explore alternatives",
                              fontsize=13, pad=12)
        self.draw_panel()
        self.fig.canvas.draw_idle()

    def describe_choice(self, choice: ScoredChoice) -> str:
        if self.state.phase == "setup_road":
            return f"Road expansion score: {choice.score:.3f}\nEdge: {choice.action.args[0]}"

        vertex = choice.action.args[0]
        existing = self.state.players[self.state.current_player_id].settlements
        if existing:
            first, second = next(iter(existing)), vertex
            heading = "Complete pair"
        else:
            first, second = vertex, choice.best_partner
            heading = "Projected best pair"
        if second is None:
            return "No legal partner for this vertex"
        values = pair_features(self.state, first, second)
        pips, _ = production_profile(self.state, (first, second))
        output = [
            f"{heading} (score {choice.score:.3f})",
            f"First: ({first.x}, {first.y})",
            f"Second: ({second.x}, {second.y})",
            "",
            "Production (pips / 36 rolls):",
        ]
        output += [f"  {r:<6} {pips[r]:.0f}" for r in RESOURCES]
        output += ["", "Feature values (normalized):"]
        output += [f"  {k:<15} {v:.3f}" for k, v in values.items()]
        if not existing:
            output.append("\nOpening score aggregates possible pairs;")
            output.append("details show the highest-scoring partner.")
        return "\n".join(output)

    def draw_panel(self) -> None:
        ax = self.panel
        ax.clear()
        ax.set_axis_off()
        pid = self.state.current_player_id
        step = self.state.setup_step
        phase = self.state.phase
        phase_label = "Settlement" if phase == "setup_settlement" else "Road" if phase == "setup_road" else "Finished"
        ax.text(0, 1.0, f"BOARD SEED {self.seed}", fontsize=13, weight="bold", va="top",
                transform=ax.transAxes)
        ax.text(0, .945, f"Move {min(step + 1, 4)} / 4 · Player {'A (blue)' if pid == 0 else 'B (red)'}",
                fontsize=10, va="top", transform=ax.transAxes)
        ax.text(0, .905, f"Phase: {phase_label}", fontsize=10, va="top", transform=ax.transAxes)

        y = .850
        for player_id in (0, 1):
            vertices = sorted(self.state.players[player_id].settlements,
                              key=lambda v: (v.x, v.y))
            label = "A" if player_id == 0 else "B"
            text = ", ".join(f"({v.x},{v.y})" for v in vertices) or "none"
            ax.text(0, y, f"{label} settlements: {text}", fontsize=9, va="top",
                    transform=ax.transAxes)
            y -= .038

        ax.text(0, .782, "Green = higher score; dark outline = best",
                fontsize=8, color="#4b5563", va="top", transform=ax.transAxes)
        ax.text(0, .747, "TOP LEGAL CHOICES", fontsize=10, weight="bold", va="top",
                transform=ax.transAxes)
        order = sorted(self.candidates, key=lambda c: -c.score)[:5]
        for i, choice in enumerate(order):
            if phase == "setup_settlement":
                v = choice.action.args[0]
                location = f"({v.x:2d}, {v.y:2d})"
            else:
                location = "road endpoint"
            ax.text(0, .710 - i * .037, f"{i + 1}. {location}   {choice.score:.3f}",
                    fontsize=9, va="top", transform=ax.transAxes)

        if self.hovered is not None:
            details = self.describe_choice(self.hovered)
            title = "HOVERED CHOICE"
        else:
            title = "EXPLANATION"
            if phase == "setup_settlement":
                details = ("Scores on circles reflect expected value of\n"
                           "the complete settlement pair.\n\n"
                           "First settlement: best possible future\n"
                           "partners (A averages top 4; B top 1).\n\n"
                           "Second settlement: score of actual pair.\n\n"
                           "Hover over a circle for the feature\n"
                           "breakdown and resource production.")
            elif phase == "setup_road":
                details = ("Road scores estimate access to useful\n"
                           "future settlement sites.\n\n"
                           "Hover to inspect a specific road.")
            else:
                details = ("Setup is complete.\n\n"
                           "Use Undo to compare nearby choices,\n"
                           "or Reset to try a different setup.")
        ax.text(0, .490, title, fontsize=10, weight="bold", va="top", transform=ax.transAxes)
        ax.text(0, .460, details, fontsize=7.9, va="top", linespacing=1.16,
                transform=ax.transAxes, family="monospace")
        ax.text(0, .020, f"Actions played: {len(self.history)} / 8\n"
                "Click marker to place · U = Undo · R = Reset",
                fontsize=8, color="#4b5563", va="top", transform=ax.transAxes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7,
                        help="Board seed, matching Board(seed=...) (default: 7)")
    args = parser.parse_args()
    SetupExplorer(seed=args.seed)


if __name__ == "__main__":
    main()

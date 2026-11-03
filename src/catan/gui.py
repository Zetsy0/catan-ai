"""A simple Catan GUI: human player 0 versus random agent player 1.

Run from the project root with: python -m catan.gui
Requires Tkinter and Matplotlib.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle

from .agents import RandomAgent
from .board import Board, Vertex, axial_to_cartesian
from .dispatcher import execute_action
from .game import GameState
from .legal_actions import Action, get_legal_actions
from .rules import get_trade_ratio
from .visualization import plot_board, plot_coords


SPATIAL_ACTIONS = {
    "place_initial_settlement", "place_initial_road",
    "build_settlement", "build_city", "build_road",
    "place_free_road", "move_robber",
}

LABELS = {
    "place_initial_settlement": "Place initial settlement",
    "place_initial_road": "Place initial road",
    "build_settlement": "Build settlement",
    "build_city": "Build city",
    "build_road": "Build road",
    "place_free_road": "Place free road",
    "move_robber": "Move robber",
    "roll_dice": "Roll dice",
    "end_turn": "End turn",
    "buy_development_card": "Buy development card",
    "trade_with_bank": "Trade with bank",
    "play_monopoly": "Play Monopoly",
    "play_year_of_plenty": "Play Year of Plenty",
    "play_knight": "Play Knight",
    "play_road_building": "Play Road Building",
    "discard_resources": "Discard resources",
}

PAGE_SIZE = 12


class CatanGUI:
    def __init__(self, root: tk.Tk, seed: int = 42):
        self.root = root
        self.root.title("Catan — human vs random AI")

        self.state = GameState(board=Board(seed=seed), seed=seed)
        self.ai = RandomAgent(seed=seed + 2)
        self.human_id = 0

        self.actions: list[Action] = []
        self.options: list[Action] = []
        self.targets: dict[Circle, Action] = {}
        self.page = 0
        self.ai_scheduled = False
        self.winner_announced = False

        # Matplotlib board on the left.
        self.figure = Figure(figsize=(8, 8))
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("pick_event", self.on_board_pick)

        # Tkinter controls on the right.
        panel = ttk.Frame(root, padding=12)
        panel.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar()
        ttk.Label(
            panel, textvariable=self.status_var,
            justify=tk.LEFT, wraplength=310,
        ).pack(anchor=tk.W, pady=(0, 16))

        ttk.Label(panel, text="Action category").pack(anchor=tk.W)
        self.category_var = tk.StringVar()
        self.category = ttk.Combobox(
            panel, textvariable=self.category_var,
            state="readonly", width=30,
        )
        self.category.pack(fill=tk.X, pady=(3, 10))
        self.category.bind("<<ComboboxSelected>>", self.on_category_change)

        ttk.Label(panel, text="Choices (double-click to execute)").pack(anchor=tk.W)
        list_frame = ttk.Frame(panel)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.choices = tk.Listbox(list_frame, width=37, height=12)
        self.choices.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.choices.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.choices.configure(yscrollcommand=scrollbar.set)
        self.choices.bind("<Double-Button-1>", self.on_choice_double_click)

        navigation = ttk.Frame(panel)
        navigation.pack(fill=tk.X, pady=6)
        self.previous_button = ttk.Button(navigation, text="Previous", command=self.previous_page)
        self.previous_button.pack(side=tk.LEFT)
        self.page_var = tk.StringVar()
        ttk.Label(navigation, textvariable=self.page_var).pack(side=tk.LEFT, expand=True)
        self.next_button = ttk.Button(navigation, text="Next", command=self.next_page)
        self.next_button.pack(side=tk.RIGHT)

        self.execute_button = ttk.Button(
            panel, text="Execute selected action", command=self.execute_selected,
        )
        self.execute_button.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(
            panel,
            text="For roads, buildings and the robber, choose a category "
                 "and click a colored circle on the board.",
            wraplength=300, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(12, 0))

        self.refresh()

    def decision_player_id(self) -> int:
        if self.state.phase == "discard":
            return next(iter(self.state.pending_discards))
        return self.state.current_player_id

    def human_to_act(self) -> bool:
        return (
            self.state.phase != "game_over"
            and self.decision_player_id() == self.human_id
        )

    def refresh(self) -> None:
        state = self.state
        human = state.players[self.human_id]
        decision = None if state.phase == "game_over" else self.decision_player_id()
        visible = [state.visible_victory_points(pid) for pid in (0, 1)]

        self.status_var.set(
            f"Turn: {state.turn_number}\n"
            f"Phase: {state.phase}\n"
            f"Current player: {state.current_player_id}\n"
            f"Decision: {'game finished' if decision is None else f'Player {decision}'}\n"
            f"Last roll: {state.last_roll}\n\n"
            f"Visible VP: You {visible[0]} — AI {visible[1]}\n"
            f"Your total VP: {state.total_victory_points(self.human_id)}\n"
            f"Your resources: {human.resources}\n"
            f"Your cards: {human.development_cards}\n"
            f"New cards: {human.new_development_cards}"
        )

        self.actions = get_legal_actions(state) if self.human_to_act() else []
        names = list(dict.fromkeys(a.name for a in self.actions))
        labels = [LABELS.get(name, name) for name in names]
        self.category["values"] = labels

        current_label = self.category_var.get()
        if current_label not in labels:
            preferred = ["Roll dice", "Place initial settlement", "Place initial road", "End turn"]
            current_label = next((v for v in preferred if v in labels), labels[0] if labels else "")
        self.category_var.set(current_label)
        self.page = 0

        self.category.configure(state="readonly" if names else "disabled")
        self.update_choices()
        self.draw_board()

        if state.phase == "game_over" and not self.winner_announced:
            self.winner_announced = True
            messagebox.showinfo("Game over", f"Player {state.winner_id} wins!")
        elif decision == 1:
            self.schedule_ai()

    def chosen_name(self) -> str | None:
        label = self.category_var.get()
        return next((name for name, text in LABELS.items() if text == label), None)

    def on_category_change(self, _event=None) -> None:
        self.page = 0
        self.update_choices()
        self.draw_board()

    def update_choices(self) -> None:
        name = self.chosen_name()
        self.options = [a for a in self.actions if a.name == name]
        self.choices.delete(0, tk.END)

        if name in SPATIAL_ACTIONS:
            self.choices.insert(tk.END, "Click a circle on the board")
            self.execute_button.configure(state="disabled")
            self.page_var.set("")
            self.previous_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            return

        total_pages = max(1, (len(self.options) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(self.page, total_pages - 1)
        start = self.page * PAGE_SIZE
        for action in self.options[start:start + PAGE_SIZE]:
            self.choices.insert(tk.END, self.action_description(action))
        if self.options[start:start + PAGE_SIZE]:
            self.choices.selection_set(0)

        self.page_var.set(f"{self.page + 1}/{total_pages}")
        self.previous_button.configure(state="normal" if self.page > 0 else "disabled")
        self.next_button.configure(state="normal" if self.page + 1 < total_pages else "disabled")
        self.execute_button.configure(state="normal" if self.options else "disabled")

    def action_description(self, action: Action) -> str:
        if action.name == "trade_with_bank":
            ratio = get_trade_ratio(self.state, self.state.current_player_id, action.args[0])
            return f"{ratio} {action.args[0]} → 1 {action.args[1]}"
        if action.name == "discard_resources":
            return ", ".join(f"{res}: {count}" for res, count in action.args[1].items())
        if action.args:
            return ", ".join(str(arg) for arg in action.args)
        return LABELS.get(action.name, action.name)

    def previous_page(self) -> None:
        self.page -= 1
        self.update_choices()

    def next_page(self) -> None:
        self.page += 1
        self.update_choices()

    def on_choice_double_click(self, _event) -> None:
        self.execute_selected()

    def execute_selected(self) -> None:
        if not self.human_to_act() or self.chosen_name() in SPATIAL_ACTIONS:
            return
        selection = self.choices.curselection()
        if not selection:
            return
        index = self.page * PAGE_SIZE + selection[0]
        if index < len(self.options):
            self.apply_action(self.options[index])

    def draw_board(self) -> None:
        self.targets.clear()
        plot_board(self.state.board, state=self.state, show=False, ax=self.ax)

        for action in self.actions:
            if action.name != self.chosen_name() or action.name not in SPATIAL_ACTIONS:
                continue
            if action.name in {"place_initial_settlement", "build_settlement", "build_city"}:
                x, y = plot_coords(action.args[0])
                radius, color = 0.22, "#16a34a"
            elif action.name in {"place_initial_road", "build_road", "place_free_road"}:
                v1, v2 = tuple(action.args[0])
                x1, y1 = plot_coords(v1)
                x2, y2 = plot_coords(v2)
                x, y = (x1 + x2) / 2, (y1 + y2) / 2
                radius, color = 0.22, "#f59e0b"
            else:  # move_robber
                hexagon = action.args[0]
                vx, vy = axial_to_cartesian(hexagon.q, hexagon.r)
                x, y = plot_coords(Vertex(vx, vy))
                radius, color = 0.45, "#374151"

            circle = Circle(
                (x, y), radius,
                facecolor="none", edgecolor=color,
                linewidth=2.5, zorder=20, picker=True,
            )
            self.ax.add_patch(circle)
            self.targets[circle] = action

        self.canvas.draw_idle()

    def on_board_pick(self, event) -> None:
        action = self.targets.get(event.artist)
        if action is not None and self.human_to_act():
            self.apply_action(action)

    def apply_action(self, action: Action) -> None:
        try:
            execute_action(self.state, action)
        except ValueError as exc:
            messagebox.showerror("Invalid action", str(exc))
            return
        self.refresh()

    def schedule_ai(self) -> None:
        if not self.ai_scheduled:
            self.ai_scheduled = True
            self.root.after(1, self.play_ai_batch)

    def play_ai_batch(self) -> None:
        self.ai_scheduled = False
        # Play a batch to avoid freezing the UI on very long AI turns.
        for _ in range(60):
            if self.state.phase == "game_over" or self.decision_player_id() != 1:
                break
            action = self.ai.choose_action(self.state)
            execute_action(self.state, action)
        self.refresh()


def main() -> None:
    root = tk.Tk()
    CatanGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

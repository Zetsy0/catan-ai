# Catan AI

The code is organized in three layers:

- `catan.game_engine`: game state, board, rules, legal actions, transitions and validation. No strategy dependencies.
- `catan.strategies`: interchangeable agents (currently `RandomAgent`) and shared `Agent` protocol.
- `catan.automatic_playing`: automated game simulation and analysis scripts. Depends on the engine and strategy modules.

`catan.visualization` remains separate from the AI and rules.

```python
from catan.automatic_playing.simulation import simulate_game
from catan.strategies.random_agent import RandomAgent

state, steps = simulate_game(
    seed=12,
    agents={0: RandomAgent(seed=1), 1: RandomAgent(seed=2)},
)
```

From the project root, run `python -m pip install -e .` and then `python -m pytest`.

**Import migration:** code using the old flat paths should change, e.g. `from catan.game import GameState` to `from catan.game_engine.game import GameState`. The project has no legacy re-export modules; use the new import paths directly.

## Visualization (optional)

The game engine and agents do **not** need Matplotlib. Install it only if you
want to plot the board:

```bash
python -m pip install -e ".[visualization]"
python -m catan.visualization
```

Or from Python:

```python
from catan.game_engine.board import Board
from catan.visualization import plot_board

plot_board(Board(seed=42))
```

The `plot_board` implementation lives only in `catan.visualization` (not in
`catan.game_engine.board`).

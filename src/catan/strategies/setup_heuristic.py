"""First-pass paired-settlement heuristic for the custom two-player Catan engine.

Only public board/ownership information and this player's pieces are used.
The numerical weights are provisional: tune them by tournament play.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, fields
import random

from ..game_engine.board import Vertex
from ..game_engine.game import GameState
from ..game_engine.legal_actions import Action, get_legal_actions
from ..game_engine.rules import valid_vertex

RESOURCES = ("wood", "brick", "sheep", "wheat", "ore")
DICE_PIPS = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
             8: 5, 9: 4, 10: 3, 11: 2, 12: 1}
RESOURCE_WEIGHTS = {"wood": 1.1, "brick": 1.1, "sheep": 0.85,
                    "wheat": 1.05, "ore": 0.95}
PAIR_WEIGHTS = {("wood", "brick"): 1.0,
                ("ore", "wheat"): 1.0,
                ("sheep", "wheat"): 0.45,
                ("sheep", "ore"): 0.45}


@dataclass(frozen=True)
class SetupWeights:
    production: float = 4.0
    diversity: float = 0.7
    balance: float = 1.6
    synchronization: float = 1.1
    recovery: float = 1.4
    port: float = 0.8
    initial_cards: float = 0.5


def production_profile(state: GameState, vertices: tuple[Vertex, ...]
                       ) -> tuple[dict[str, float], dict[int, dict[str, int]]]:
    """Return expected production in dice 'pips' and the yield per roll.

    A hex with number 6 contributes 5 pips, i.e. 5/36 cards per turn.
    """
    pips = {resource: 0.0 for resource in RESOURCES}
    by_roll: dict[int, dict[str, int]] = {}
    for vertex in vertices:
        for hexagon in state.board.vertex_hex_adjacency[vertex]:
            resource = state.board.hex_resources[hexagon]
            number = state.board.hex_numbers[hexagon]
            if resource is None or number not in DICE_PIPS:
                continue
            pips[resource] += DICE_PIPS[number]
            by_roll.setdefault(number, {r: 0 for r in RESOURCES})[resource] += 1
    return pips, by_roll


def shortest_distances(state: GameState, sources: tuple[Vertex, ...]
                       ) -> dict[Vertex, int]:
    """Optimistic road distances, excluding opponent-owned roads/buildings."""
    player_id = state.current_player_id
    blocked_vertices = set()
    blocked_edges = set()
    for pid, player in state.players.items():
        if pid != player_id:
            blocked_vertices |= player.settlements | player.cities
            blocked_edges |= player.roads

    distances = {v: 0 for v in sources}
    queue = deque(sources)
    while queue:
        vertex = queue.popleft()
        for neighbor in state.board.vertex_adjacency[vertex]:
            if neighbor in distances or neighbor in blocked_vertices:
                continue
            if frozenset((vertex, neighbor)) in blocked_edges:
                continue
            distances[neighbor] = distances[vertex] + 1
            queue.append(neighbor)
    return distances


def future_targets(state: GameState, planned: tuple[Vertex, Vertex]
                   ) -> list[Vertex]:
    """Currently open vertices still satisfying the distance rule after the pair."""
    a, b = planned
    forbidden = ({a, b} | state.board.vertex_adjacency[a]
                 | state.board.vertex_adjacency[b])
    return [v for v in state.board.vertices
            if v not in forbidden and valid_vertex(state, v)]


def future_access_score(state: GameState, planned: tuple[Vertex, Vertex],
                        current_pips: dict[str, float]) -> float:
    """Reward a plausible next settlement which repairs resource shortages.

    The geometric distance assumes the setup roads can be pointed optimally;
    it is NOT a proof that the future spot remains available.
    """
    deficits = {r: max(0.0, 1.0 - current_pips[r] / 5.0)
                for r in RESOURCES}
    distances = shortest_distances(state, planned)
    best = 0.0
    for target in future_targets(state, planned):
        distance = distances.get(target)
        if distance is None:
            continue
        target_pips, _ = production_profile(state, (target,))
        # A location at graph distance two requires roughly one paid road
        # beyond its initial free road, hence the distance discount.
        discount = 0.65 ** max(0, distance - 2)
        repair = sum(deficits[r] * target_pips[r] for r in RESOURCES)
        growth = 0.15 * sum(target_pips.values())
        best = max(best, (repair + growth) * discount)
    return best / 8.0


def port_score(state: GameState, planned: tuple[Vertex, Vertex],
               pips: dict[str, float]) -> float:
    """Value ports owned by either proposed settlement."""
    ports = [port_type for edge, port_type in state.board.ports.items()
             if not edge.isdisjoint(planned)]
    value = 0.0
    for port_type in set(ports):
        if port_type == "generic":
            value += 0.2 * max(pips.values())
        elif port_type in pips:
            value += 0.4 * pips[port_type]
    return value / 8.0


def pair_features(state: GameState, first: Vertex, second: Vertex
                 ) -> dict[str, float]:
    """Features of a hypothetical initial pair; no state mutations."""
    pair = (first, second)
    pips, by_roll = production_profile(state, pair)
    production = sum(RESOURCE_WEIGHTS[r] * pips[r] for r in RESOURCES)
    diversity = sum(pips[r] > 0 for r in RESOURCES)

    # Rate compatibility: roads need 1 wood : 1 brick, cities 3 ore : 2 wheat.
    balance = (min(pips["wood"], pips["brick"])
               + 2 * min(pips["ore"] / 3, pips["wheat"] / 2)
               + 0.4 * min(pips["sheep"], pips["wheat"])
               + 0.4 * min(pips["sheep"], pips["ore"]))

    sync = sum(
        DICE_PIPS[number] * weight * min(yields[r1], yields[r2])
        for number, yields in by_roll.items()
        for (r1, r2), weight in PAIR_WEIGHTS.items()
    )

    # The second settlement grants one card per adjacent productive hex.
    initial_cards = sum(
        RESOURCE_WEIGHTS[state.board.hex_resources[h]]
        for h in state.board.vertex_hex_adjacency[second]
        if state.board.hex_resources[h] is not None
    )

    return {
        "production": production / 28,
        "diversity": diversity / 5,
        "balance": balance / 12,
        "synchronization": sync / 15,
        "recovery": future_access_score(state, pair, pips),
        "port": port_score(state, pair, pips),
        "initial_cards": initial_cards / 3,
    }


def score_pair(state: GameState, first: Vertex, second: Vertex,
               weights: SetupWeights) -> float:
    values = pair_features(state, first, second)
    return sum(getattr(weights, f.name) * values[f.name]
               for f in fields(weights))


def choose_initial_settlement(state: GameState, legal: list[Action],
                              weights: SetupWeights,
                              rng: random.Random) -> Action:
    player_id = state.current_player_id
    existing = state.players[player_id].settlements
    if existing:
        first = next(iter(existing))
        scored = [(score_pair(state, first, a.args[0], weights), a)
                  for a in legal]
    else:
        # Player B chooses two settlements consecutively (B-B), while A's
        # second settlement comes after the opponent's two choices.
        robust_count = 4 if state.setup_step == 0 else 1
        scored = []
        for action in legal:
            first = action.args[0]
            partners = [other.args[0] for other in legal
                        if other.args[0] != first
                        and other.args[0] not in state.board.vertex_adjacency[first]]
            if not partners:
                scored.append((float("-inf"), action))
                continue
            scores = sorted(
                (score_pair(state, first, partner, weights)
                 for partner in partners), reverse=True
            )
            scored.append((sum(scores[:robust_count]) /
                           len(scores[:robust_count]), action))

    best = max(score for score, _ in scored)
    candidates = [a for score, a in scored if abs(score - best) < 1e-9]
    return rng.choice(sorted(candidates, key=lambda a: (a.args[0].x, a.args[0].y)))


def score_initial_road(state: GameState, action: Action) -> float:
    """Prefer a road leading toward a strong *reachable* future settlement."""
    anchor = state.pending_initial_settlement
    if anchor is None:
        return 0.0
    endpoint = next(v for v in action.args[0] if v != anchor)
    player = state.players[state.current_player_id]
    current_pips, _ = production_profile(state, tuple(player.settlements))
    scarcity = {r: max(0.0, 1.0 - current_pips[r] / 5.0)
                for r in RESOURCES}
    distances = shortest_distances(state, (endpoint,))
    options = []
    for target in state.board.vertices:
        if not valid_vertex(state, target):
            continue
        distance = distances.get(target)
        if distance is None:
            continue
        target_pips, _ = production_profile(state, (target,))
        score = (sum(scarcity[r] * target_pips[r] for r in RESOURCES)
                 + 0.3 * sum(target_pips.values()))
        options.append(score * 0.65 ** max(0, distance - 1))
    return max(options, default=0.0)


class HeuristicAgent:
    """Uses paired setup planning; falls back to random actions elsewhere."""

    def __init__(self, seed: int | None = None,
                 weights: SetupWeights | None = None):
        self.rng = random.Random(seed)
        self.weights = weights if weights is not None else SetupWeights()

    def choose_action(self, state: GameState) -> Action:
        legal = get_legal_actions(state)
        if not legal:
            raise ValueError("No legal actions available")

        if state.phase == "setup_settlement":
            return choose_initial_settlement(state, legal, self.weights, self.rng)
        if state.phase == "setup_road":
            scores = [score_initial_road(state, action) for action in legal]
            best = max(scores)
            choices = [action for action, score in zip(legal, scores)
                       if abs(score - best) < 1e-9]
            return self.rng.choice(sorted(
                choices,
                key=lambda a: sorted((v.x, v.y) for v in a.args[0]),
            ))
        return self.rng.choice(legal)

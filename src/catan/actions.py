from .board import Vertex, Edge, Hex, get_vertices
from .game import GameState, PlayerState, SETUP_ORDER
from .rules import (can_place_initial_settlement, can_place_initial_road, can_move_robber, can_place_road, can_place_settlement,
                    can_place_city, get_trade_ratio,
)
from collections import Counter

ROAD_COST = {"wood": 1, "brick": 1}

SETTLEMENT_COST = {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1}

CITY_COST = {"ore": 3, "wheat": 2}

DEV_CARD_COST = {"ore": 1, "wheat": 1, "sheep": 1}

def place_initial_settlement(
    state: GameState,
    vertex: Vertex,
) -> None:
    if state.phase != "setup_settlement":
        raise ValueError("Not in settlement placement phase")
    
    if can_place_initial_settlement(state, vertex) :
        state.players[state.current_player_id].settlements.add(vertex)
        state.pending_initial_settlement = vertex # The current active settlement to which we need to attach a road
        state.phase = "setup_road" # The next step is placing the road
        if state.setup_step >= 2 : # If this is the second settlement, get the surrounding ressources
            new_resources = Counter(
                state.board.hex_resources[hexagon]for hexagon in state.board.vertex_hex_adjacency[vertex]
            )
            for resource_type in state.players[state.current_player_id].resources.keys():
                state.players[state.current_player_id].resources[resource_type] += new_resources[resource_type]
                state.bank[resource_type] -= new_resources[resource_type]
    else :
        raise ValueError("Illegal settlement placement attempt")


def place_initial_road(state: GameState, edge: Edge) -> None:
    if state.phase != "setup_road":
        raise ValueError("Wrong game phase")

    if not can_place_initial_road(state, edge):
        raise ValueError("Invalid road placement")

    # 1. Add the road to the current player's roads
    state.players[state.current_player_id].roads.add(edge)

    # 2. Reset pending_initial_settlement
    state.pending_initial_settlement = None

    # 3. Increment setup_step
    state.setup_step += 1

    # 4. Determine whether setup is complete
    if state.setup_step < len(SETUP_ORDER):
        # Update current_player_id and phase
        state.current_player_id = SETUP_ORDER[state.setup_step]
        state.phase = "setup_settlement"
    else:
        state.current_player_id = 0
        state.phase = "roll_dice"

def roll_dice(state: GameState) -> int:
    if state.phase != "roll_dice":
        raise ValueError("Wrong game phase")

    roll = state.rng.randint(1, 6) + state.rng.randint(1, 6)
    state.last_roll = roll

    if roll != 7:
        produce_resources(state, roll)
        state.phase = "main_turn"

    else:
        state.robber_return_phase = "main_turn"
        state.pending_discards = {}

        for player_id, player in state.players.items():
            if player.total_resources >= 10:
                state.pending_discards[player_id] = player.total_resources // 2

        state.phase = (
            "discard" if state.pending_discards else "move_robber"
        )
    return roll


def produce_resources(state: GameState, roll: int) -> None:
    producing_hexes = [
        h for h, number in state.board.hex_numbers.items()
        if number == roll and h != state.robber_hex
    ]
    for hexagon in producing_hexes:
        resource = state.board.hex_resources[hexagon]
        if resource is None:
            continue
        for vertex in get_vertices(hexagon):
            for player in state.players.values() :
                if vertex in player.settlements :
                    give_resources(state, player, resource, 1)
                elif vertex in player.cities :
                    give_resources(state, player, resource, 2)
    return None

def give_resources(state: GameState, player: PlayerState, resource: str, quantity: int) -> None:
    given = min(quantity, state.bank[resource])
    state.bank[resource] -= given
    player.resources[resource] += given
    return None

def discard_resources(
    state: GameState,
    player_id: int,
    cards: dict[str, int]
) -> None:
    if state.phase != "discard":
        raise ValueError("Discard called outside of discard phase")
    if player_id not in state.pending_discards:
        raise ValueError("Player has no pending discards")
    if sum(cards.values()) != state.pending_discards[player_id]:
        raise ValueError("Incorrect number of cards discarded")
    if not all(resource in state.bank for resource in cards):
        raise ValueError("Unknown resource type")
    if not all(cards[resource] >= 0 for resource in cards) :
        raise ValueError("Negative discard amounts")
    if not all(state.players[player_id].resources[resource] >= cards[resource] for resource in cards) :
        raise ValueError("Not enough cards for the given discard choice")

    
    
    for resource in cards :
        state.players[player_id].resources[resource] -= cards[resource]
        state.bank[resource] += cards[resource]
    _ = state.pending_discards.pop(player_id)
    if not state.pending_discards:
        state.phase = "move_robber"
    return None

def move_robber(state: GameState, hexagon: Hex) -> None:
    # 1. Verify that we're in the correct phase
    if state.phase != "move_robber":
        raise ValueError("Moving robber outside of 'move_robber' phase")

    if not can_move_robber(state, hexagon) :
        raise ValueError("Invalid location for the robber")

    state.robber_hex = hexagon

    opponent_id = 1 - state.current_player_id
    can_steal = any(
                    vertex in state.players[opponent_id].settlements or vertex in state.players[opponent_id].cities
                    for vertex in get_vertices(hexagon)
                )
    if can_steal and state.players[opponent_id].total_resources > 0 :
        stolen_resource = state.rng.choices(
            list(state.players[opponent_id].resources.keys()),
            list(state.players[opponent_id].resources.values()),
            k=1
        )[0]
        state.players[opponent_id].resources[stolen_resource] -= 1
        state.players[state.current_player_id].resources[stolen_resource] += 1

                
    state.phase = state.robber_return_phase or "main_turn"
    state.robber_return_phase = None

    return None

# Buildings

def build_road(
        state: GameState,
        edge: Edge,
)-> None :
    player_id = state.current_player_id
    player = state.players[player_id]

    if state.phase != "main_turn":
        raise ValueError("Attempted to build road outside of 'main_turn' phase")

    if not can_place_road(state, edge, player_id) :
        raise ValueError("Cannot place road at this location")

    if not pay_resources(state, player_id, ROAD_COST) :
        raise ValueError("Player cannot afford the cost or the cost is faulty")

    player.roads.add(edge)
    return None

def build_settlement(
        state: GameState,
        vertex: Vertex,
) -> None :
    player_id = state.current_player_id
    player = state.players[player_id]
    
    if state.phase != "main_turn":
        raise ValueError("Trying to build a settlement outside of 'main_turn' phase")

    if not can_place_settlement(state, vertex, player_id) :
        raise ValueError("Can not place settlement on this vertex")
    
    if not pay_resources(state, player_id, SETTLEMENT_COST) :
        raise ValueError("Player cannot afford the cost or the cost is faulty")

    player.settlements.add(vertex)
    
    return None

def build_city(
        state: GameState,
        vertex: Vertex,
) -> None :
    player_id = state.current_player_id
    player = state.players[player_id]
    
    if state.phase != "main_turn":
        raise ValueError("Trying to build a city outside of 'main_turn' phase")

    if not can_place_city(state, vertex, player_id) :
        raise ValueError("Can not place city on this vertex")
    
    if not pay_resources(state, player_id, CITY_COST) :
        raise ValueError("Player cannot afford the cost or the cost is faulty")

    player.settlements.remove(vertex)
    player.cities.add(vertex)

    
    return None

def pay_resources(state: GameState, player_id: int, cost: dict[str, int]) -> bool :
    # Negative costs
    if any(cost_quantity < 0 for cost_quantity in cost.values()) :
        return False

    # Invalid resources
    if not set(cost).issubset(state.players[player_id].resources):
        return False

    # Player can't afford the cost
    if any(state.players[player_id].resources[resource] < cost_quantity for resource, cost_quantity in cost.items()) :
        return False

    # Deducing resources
    for resource, cost_quantity in cost.items() :
        state.players[player_id].resources[resource] -= cost_quantity
        state.bank[resource] += cost_quantity
    return True

def trade_with_bank(
    state: GameState,
    give_resource: str,
    receive_resource: str
) -> None:
    if state.phase != "main_turn":
        raise ValueError("Attempting to trade with bank outside of 'main_turn' phase")

    if give_resource not in state.bank or receive_resource not in state.bank:
        raise ValueError("Invalid resource type")

    if give_resource == receive_resource:
        raise ValueError("Cannot trade a resource for itself")
    
    player_id = state.current_player_id
    player = state.players[player_id]

    ratio = get_trade_ratio(state, player_id, give_resource)

    if player.resources[give_resource] < ratio :
        raise ValueError("Not enough resources to trade with bank")

    if not state.bank[receive_resource] >= 1 :
        raise ValueError("The bank doesn't have the required ressource")

    state.bank[give_resource] += ratio
    player.resources[give_resource] -= ratio

    state.bank[receive_resource] -= 1
    player.resources[receive_resource] += 1
    return None

def buy_development_card(state: GameState) -> None:
    if state.phase != "main_turn":
        raise ValueError("Attempting to draw a development card outside of 'main_turn' phase")
    
    if not state.development_card_deck :
        raise ValueError("Empty development cards deck")

    if not pay_resources(state, state.current_player_id, DEV_CARD_COST) :
        raise ValueError("Payement unsuccesful")

    state.players[state.current_player_id].new_development_cards.append(state.development_card_deck.pop())
    
    return None

def end_turn(state: GameState) -> None:
    if state.phase != "main_turn":
        raise ValueError("Attempting to end turn outside of 'main_turn' phase")

    state.current_player_id = 1 - state.current_player_id
    new_player = state.players[state.current_player_id]
    
    new_player.development_cards.extend(new_player.new_development_cards)
    new_player.new_development_cards.clear()
    new_player.played_dev_card_this_turn = False


    state.turn_number += 1
    state.phase = "roll_dice"

    return None

# Dev cards

def play_knight(state: GameState) -> None:
    if state.phase not in ("main_turn", "roll_dice"):
        raise ValueError("Wrong game phase")

    player = state.players[state.current_player_id]

    if "knight" not in player.development_cards:
        raise ValueError("Player has no playable Knight")

    if player.played_dev_card_this_turn:
        raise ValueError("Already played a development card this turn")

    # All validations passed
    player.development_cards.remove("knight")
    player.knights_played += 1
    player.played_dev_card_this_turn = True

    update_largest_army(state)

    state.robber_return_phase = state.phase
    state.phase = "move_robber"


def update_largest_army(state: GameState) -> None :
    k0 = state.players[0].knights_played
    k1 = state.players[1].knights_played

    if max(k0, k1) < 3:
        return None

    if k0 == k1:
        return None

    state.largest_army_holder = 0 if k0 > k1 else 1

    return None

def play_monopoly(state: GameState, resource: str) -> None:
    ...

    

    
   
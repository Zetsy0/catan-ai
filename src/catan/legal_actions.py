
from typing import Any
from dataclasses import dataclass
from .game import GameState
from .rules import (
    can_place_initial_settlement,
    can_place_initial_road,
    can_move_robber,
    can_place_road,
    can_place_settlement,
    can_place_city,
    get_trade_ratio,
)
from .actions import(ROAD_COST, CITY_COST, SETTLEMENT_COST, DEV_CARD_COST,)

@dataclass(frozen=True)
class Action:
    name: str
    args: tuple[Any, ...] = ()

def get_legal_dev_cards_actions(state: GameState) -> list[Action]:
    player_id = state.current_player_id
    player = state.players[player_id]
    dev_card_actions = []
    if len(player.development_cards) > 0 and not player.played_dev_card_this_turn :
        if "monopoly" in player.development_cards:
            dev_card_actions += [
                Action("play_monopoly",(resource,))
                    for resource in state.bank.keys()
                ]
        if "year_of_plenty" in player.development_cards :
            year_of_plenty_actions = []
            for resource_1 in state.bank.keys():
                year_of_plenty_actions += [
                    Action("play_year_of_plenty", (resource_1, resource_2))
                        for resource_2 in state.bank.keys()
                        if (
                            (resource_1 == resource_2 and state.bank[resource_1] >= 2)
                            or
                            (resource_1 != resource_2
                            and state.bank[resource_1] >= 1
                            and state.bank[resource_2] >= 1)
                        )
                    ]
                
            dev_card_actions += year_of_plenty_actions

        if "knight" in player.development_cards:
            dev_card_actions += [
                Action("play_knight")
            ]

        if "road_building" in player.development_cards:
            if any(
                can_place_road(state, edge, state.current_player_id)
                for edge in state.board.edges
            ):
                dev_card_actions.append(Action("play_road_building"))
    return dev_card_actions

def get_legal_building_actions(state: GameState) -> list[Action]:
    player_id = state.current_player_id
    player = state.players[player_id]
    building_actions = []

    if all(player.resources[resource] >= quantity for resource, quantity in SETTLEMENT_COST.items()):
        building_actions += [Action("build_settlement",(vertex,))
                             for vertex in state.board.vertices
                             if can_place_settlement(state,vertex,player_id)
                             ]

    if all(player.resources[resource] >= quantity for resource, quantity in CITY_COST.items()) :
        building_actions += [Action("build_city",(vertex,))
                             for vertex in state.board.vertices
                             if can_place_city(state, vertex, player_id)
                             ]

    if all(player.resources[resource] >= quantity for resource, quantity in ROAD_COST.items()) :
        building_actions += [Action("build_road",(edge,))
                             for edge in state.board.edges
                             if can_place_road(state, edge, player_id)]
    return building_actions


def get_legal_discard_actions(state: GameState, player_id: int) -> list[Action]:
    actions = []
    required = state.pending_discards[player_id]
    resources = state.players[player_id].resources
    resource_types = list(resources)

    def generate(
        index: int,
        remaining: int,
        current: dict[str, int]
    ) -> None:

        if index == len(resource_types):
            if remaining == 0:
                actions.append(
                    Action("discard_resources", (player_id, current))
                )
            return

        resource = resource_types[index]

        for amount in range(min(resources[resource], remaining) + 1):
            next_choice = current.copy()

            if amount > 0:
                next_choice[resource] = amount

            generate(index + 1, remaining - amount, next_choice)

    generate(0, required, {})

    return actions


def get_legal_actions(state: GameState) -> list[Action]:
    player_id = state.current_player_id
    player = state.players[player_id]
    if state.phase == "game_over":
        return []

    if state.phase == "setup_settlement":
        return [
            Action("place_initial_settlement", (vertex,))
            for vertex in state.board.vertices
            if can_place_initial_settlement(state, vertex)
        ]

    if state.phase == "setup_road":
        return [
            Action("place_initial_road", (edge,))
            for edge in state.board.edges
            if can_place_initial_road(state, edge)
        ]


    if state.phase == "roll_dice":
        return get_legal_dev_cards_actions(state) + [Action("roll_dice")]


    if state.phase == "main_turn" :
        all_main_turn_actions = get_legal_building_actions(state) + get_legal_dev_cards_actions(state) + [Action("end_turn")]

        if (state.development_card_deck and all(player.resources[resource] >= quantity for resource, quantity in DEV_CARD_COST.items())):
            all_main_turn_actions.append(Action("buy_development_card"))

        for given_resource in state.bank.keys():
            trade_ratio = get_trade_ratio(state, player_id, given_resource)
            all_main_turn_actions += [Action("trade_with_bank", (given_resource, received_resource,))
                                      for received_resource in state.bank.keys()
                                      if player.resources[given_resource]>= trade_ratio
                                      and state.bank[received_resource] >= 1
                                      and given_resource != received_resource
                                      ]

        return all_main_turn_actions

    if state.phase == "move_robber":
        return [
            Action("move_robber",(hexagon,))
            for hexagon in state.board.hexes
            if can_move_robber(state, hexagon)
        ]
    
    if state.phase == "discard":
        player_id = next(iter(state.pending_discards))
        return get_legal_discard_actions(state, player_id)

    if state.phase == "road_building":
        return [Action("place_free_road",(edge,))
                for edge in state.board.edges
                if can_place_road(state, edge, player_id)]

    raise NotImplementedError(
        f"Legal actions not implemented for {state.phase}"
    )

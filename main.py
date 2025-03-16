from renpydux import ActionReducerMapBuilder, RenpyduxState, createReducer, RenpyduxStore, ActionableStateItem, combineReducers, RenpyduxReducer
from immer import Proxy
from typing import Callable, Optional
from enum import Enum
from dataclasses import dataclass, field
import random
import time


class BattleActionType(Enum):
    ATTACK = "ATTACK"
    LOG = "LOG"
    END = "END"
    DAMAGE = "DAMAGE"


@dataclass
class Character(RenpyduxState):
    name: str
    attack: int = 10
    hp: int = 10
    max_hp: int = 10


@dataclass
class BattleState(RenpyduxState):
    player: Character
    enemy: Character
    battle_log: list[str] = field(default_factory=lambda: ["BATTLE STARTED!"])
    turn_count: int = 1,
    battle_over: bool = False
    winner: str = None


def create_action(type: BattleActionType, payload: Optional[T] = None):
    return ActionableStateItem(type.value, payload)

# Helper functions for battle logic
def calculate_damage(attacker: Character, defender: Character):
    return max(0, attacker.attack - (defender.attack // 2))  # Simplified damage

def is_alive(character: Character):
    return character.hp > 0

def create_damage_action(target: str, damage: int):
  return create_action(BattleActionType.ATTACK, {"target": target, "damage": damage})

def create_battle_log_action(log: str):
  return create_action(BattleActionType.LOG, {"log": log})

def create_end_battle_action(winner: str):
  return create_action(BattleActionType.END, {"winner": winner})

def character_reducer_builder_callback(builder: ActionReducerMapBuilder):
    def handle_damage(state: Character, action: ActionableStateItem):
        payload = action.payload
        if payload:
            state.hp = max(0, state.hp - payload)
    builder.add_case(create_action(BattleActionType.DAMAGE), handle_damage)

def battle_reducer_builder_callback(builder):
    def handle_attack(state: Character, action: ActionableStateItem):
        payload = action.payload
        if payload:
            target = payload["target"]
            damage = payload["damage"]
            if target == "player":
                state.player.hp = max(0, state.player.hp - damage)
            elif target == "enemy":
                state.enemy.hp = max(0, state.enemy.hp - damage)

            # Check for battle end
            if not is_alive(state.player):
                state.battle_over = True
                state.winner = "enemy"
            elif not is_alive(state.enemy):
                state.battle_over = True
                state.winner = "player"
            state.turn_count += 1

    def handle_battle_log(state: BattleState, action: ActionableStateItem):
      payload = action.payload
      if payload:
        log = payload["log"]
        with Proxy(state.battle_log) as (_, new_battle_log):
          _.append(log)
          state.battle_log = new_battle_log

    def handle_end_battle(state: BattleState, action: ActionableStateItem):
      payload = action.payload
      if payload:
        state.winner = payload["winner"]
        with Proxy(state.battle_log) as (_, new_battle_log):
            _.append(f"{payload["winner"]} wins!")
            state.battle_log = new_battle_log
        state.battle_over = True

    builder.add_case(create_action(BattleActionType.ATTACK), handle_attack)
    builder.add_case(create_action(BattleActionType.LOG), handle_battle_log)
    builder.add_case(create_action(BattleActionType.END), handle_end_battle)

initial_state = BattleState(
    player=Character(name="Hero", hp=100, attack=15, max_hp=100),
    enemy=Character(name="Goblin", hp=50, attack=8, max_hp=50),
    battle_log=["Battle started!"],
    turn_count=1,
    battle_over=False,
    winner=None,
)

character_reducer = createReducer(initial_state.player, lambda state, action: state)

battle_reducer = createReducer(initial_state, battle_reducer_builder_callback)
# main_reducer = combineReducers({
#     "player": RenpyduxReducer(character_reducer),
#     "enemy": RenpyduxReducer(character_reducer),
#     "battle_log": RenpyduxReducer(battle_reducer)
# })

store = RenpyduxStore(battle_reducer, initial_state)

def battle_turn():
    state: BattleState = store.get_state()

    if state.battle_over:
        return

    player = state.player
    enemy = state.enemy

    # Player's turn
    player_damage = calculate_damage(player, enemy)
    store.dispatch(create_damage_action("enemy", player_damage))
    store.dispatch(create_battle_log_action(f"{player.name} attacks {enemy.name} for {player_damage} damage."))

    if store.get_state().battle_over:
      return

    # Enemy's turn
    enemy_damage = calculate_damage(enemy, player)
    store.dispatch(create_damage_action("player", enemy_damage))
    store.dispatch(create_battle_log_action(f"{enemy.name} attacks {player.name} for {enemy_damage} damage."))

def battle_loop():
    while not store.get_state().battle_over:
        battle_turn()
        time.sleep(1)  # Simulate turn-based delay

    winner = store.get_state().winner
    store.dispatch(create_battle_log_action(f"{store.get_state().winner} wins!"))
    print(f"Battle over! {winner} wins!")
    print("Battle Log:")
    for log in store.get_state().battle_log:
        print(log)

# Run the battle
battle_loop()

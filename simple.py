import time
from renpydux import RenpyduxStore, ActionableStateItem, combineReducers
from immer import Proxy as ImmerProxy, produce
from dataclasses import dataclass

# --- Character and Enemy State ---
@dataclass
class CharacterSlice:
    hp: int = 100
    attack: int = 10

@dataclass
class EnemySlice:
    hp: int = 100
    attack: int = 8

@dataclass
class GameSlice:
    turn: str = "player"
    game_over: bool = False

@dataclass
class OverarchingState:
    player: CharacterSlice
    enemy: EnemySlice
    game: GameSlice

# --- Actions ---
class PlayerAttack(ActionableStateItem):
    def __init__(self):
        super().__init__("PLAYER_ATTACK", None)

class EnemyAttack(ActionableStateItem):
    def __init__(self):
        super().__init__("ENEMY_ATTACK", None)

class EndTurn(ActionableStateItem):
    def __init__(self):
        super().__init__("END_TURN", None)

class CheckGameOver(ActionableStateItem):
    def __init__(self):
        super().__init__("CHECK_GAME_OVER", None)

# --- Reducers ---
def character_reducer(state: CharacterSlice, action: ActionableStateItem):
    with ImmerProxy(state) as (draft_state, next_state):
        if action.type == "ENEMY_ATTACK":
            new_health = state.hp - 8
            draft_state.hp = max(0, new_health)  # Enemy attack damage
    return next_state
    # return state

def enemy_reducer(state: EnemySlice, action: ActionableStateItem):
    with ImmerProxy(state) as (draft_state, next_state):
        if action.type == "PLAYER_ATTACK":
            new_health = state.hp - 8  # Player attack damage
            draft_state.hp = max(0, new_health)  # Player attack damage
    return next_state
    # return state

def game_reducer(state: OverarchingState, action: ActionableStateItem):
    with ImmerProxy(state) as (draft_state, next_state):
        if action.type == "END_TURN":
            draft_state.game.turn = "enemy" if state.game.turn == "player" else "player"
        elif action.type == "CHECK_GAME_OVER":
            if state.enemy.hp <= 0 or state.player.hp <= 0:
                draft_state.game.game_over = True
    return next_state

# --- Combine Reducers ---
reducer = combineReducers({
    "player": character_reducer,
    "enemy": enemy_reducer,
    "root": game_reducer
})

# --- Initialize Store ---
initial_state = OverarchingState(CharacterSlice(), EnemySlice(), GameSlice())
store = RenpyduxStore[OverarchingState](reducer, initial_state)

# --- Simulation ---
def turn_based_simulation():
    def listener(state_change):
        _, new_state = state_change
        if _.game.turn is not new_state.game.turn:
            print(f"Turn: {new_state.game.turn}, Player HP: {new_state.player.hp}, Enemy HP: {new_state.enemy.hp}")
        if new_state.game.game_over:
            print("Game Over!")
            if new_state.player.hp <= 0:
                print("Enemy Wins!")
            else:
                print("Player Wins!")
    
    store.subscribe(listener)
    
    # Sample Turns
    while store.get_state().game.game_over == False:
        if store.get_state().game.turn == "player":
            store.dispatch(PlayerAttack())
        else:    
            store.dispatch(EnemyAttack())
        store.dispatch(EndTurn())
        store.dispatch(CheckGameOver())
        time.sleep(1)
    
# Run the simulation
turn_based_simulation()
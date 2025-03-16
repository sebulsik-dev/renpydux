import warnings
from typing import Any, Callable, List, Set, Tuple, Generic, TypeVar, Optional, Union
from copy import deepcopy, copy
from sebulvents.EventDispatcher import ValueDispatcher
from dataclasses import dataclass
from immer import Proxy

T = TypeVar('T')
TState = TypeVar('TState', bound='RenpyduxState')

@dataclass
class RenpyduxState:
    pass


class ActionableStateItem(Generic[T]):
    def __init__(self, type: str, payload: Optional[T]=None):
        self.type = type
        self.payload = payload


class ActionReducerMapBuilder(Generic[T]):
    def __init__(self):
        self.actions_map: dict[ActionableStateItem, Callable[[RenpyduxState, Optional[ActionableStateItem]], Any]] = {}
        self.matchers_map: dict[Callable[[ActionableStateItem], bool], Callable[[RenpyduxState, Optional[ActionableStateItem]], Any]] = {}
        self.default_reducer: Callable[[RenpyduxState, Optional[ActionableStateItem]], Any] = None

    def add_case(
        self,
        action: ActionableStateItem,
        reducer_action: Callable[[RenpyduxState, Optional[ActionableStateItem]], Any]
    ) -> 'ActionReducerMapBuilder':
        if len(self.matchers_map) > 0:
            raise Exception("add_case must be called before add_matcher")
        if self.default_reducer is not None:
            raise Exception("add_case must be called before set_default_reducer")
        if not action.type:
            raise Exception("Action type is required")
        if action.type in self.actions_map:
            raise Exception(f"Action {action.type} already exists")
        self.actions_map[action.type] = reducer_action
        return self

    def add_matcher(
        self,
        matcher: Callable[[ActionableStateItem], bool],
        reducer_action: Callable[[RenpyduxState, Optional[ActionableStateItem]], Any]
    ) -> 'ActionReducerMapBuilder':
        if self.default_reducer is not None:
            raise Exception("add_matcher must be called before set_default_reducer")
        self.matchers_map[matcher] = reducer_action
        return self

    def set_default_reducer(
        self,
        reducer_action: Callable[[RenpyduxState, Optional[ActionableStateItem]], Any]
    ) -> 'ActionReducerMapBuilder':
        if self.default_reducer is not None:
            raise Exception("Default reducer already set")
        self.default_reducer = reducer_action
        return self

class RenpyduxReducer(Generic[TState]):
    def __init__(self, reducer: Callable[[Optional[TState], Optional[ActionableStateItem]], TState]):
        self.__reducer = reducer

    def __call__(
        self,
        state: Optional[TState]=None,
        action: Optional[ActionableStateItem]=None
    ) -> TState:
        """
        A proxied version of the state is passed to the reducer.
        The reducer will apply the action to the proxied state.
        Developers can use the draft state to apply changes like they would with a mutable object.
        The returned state is a deep copy of the draft state.
        """
        result = self.__reducer(state, action)
        return result


class RenpyduxStore(Generic[TState]):
    def __init__(self, reducer: RenpyduxReducer, initial_state: Union[TState, Callable[[], TState], None]=None):
        if callable(initial_state):
            initial_state = initial_state()
        self.__state = initial_state if initial_state else reducer(None, None)
        self.__reducer = reducer
        self.__event = ValueDispatcher[Tuple[Optional[TState], Optional[TState]]](self.__state)
        self.__event.current = (initial_state, self.__state)

    def dispatch(self, action: ActionableStateItem):
        """
        The reducer will apply the action to the state via proxy (Immer).
        The state is updated and the subscribers are notified.
        """
        old_state = self.__state
        self.__state = self.__reducer(self.__state, action)
        self.__event.current = (self.__event.current[1], self.__state)
        return self.__state

    def subscribe(self, handler: Callable[[Tuple[Optional[TState], Optional[TState]]], Any]) -> Callable[[], None]:
        return self.__event.subscribe(handler)

    def get_state(self) -> TState:
        """
        Due to immer, we can return a shallow copy of the state.
        We already have a deep copy of the state in the store.
        """
        return copy(self.__state)


def combineReducers(slices: dict[str, RenpyduxReducer]):
    def combined_reducer(state: RenpyduxState, action: ActionableStateItem):
        """
        We will always use a deepcopy of the state to avoid mutation.
        The reducer never has be passed in the old state.
        """
        next_state = copy(state)
        for slice_name, reducer in slices.items():
            if slice_name == "root": continue
            if not hasattr(next_state, slice_name): continue
            sub_state = getattr(next_state, slice_name)
            updated_sub_state = reducer(sub_state, action)
            setattr(next_state, slice_name, updated_sub_state)
        if slices.get("root"):
            next_state = slices.get("root")(next_state, action)
        return next_state
    return RenpyduxReducer(combined_reducer)


def __handleReducerBuilderCallback(callback: Callable[[ActionReducerMapBuilder], None]) -> ActionReducerMapBuilder:
    builder = ActionReducerMapBuilder()
    callback(builder)
    return builder

def createReducer(
    initial_state: Union[RenpyduxState, Callable[[], RenpyduxState]],
    builder_callback: Callable[[ActionReducerMapBuilder], None]
) -> RenpyduxReducer:
    if callable(initial_state): initial_state = initial_state()
    builder = __handleReducerBuilderCallback(builder_callback)
    def reducer(base_state: RenpyduxState = initial_state, action: Optional[ActionableStateItem]=None) -> RenpyduxState:
        with Proxy(base_state) as (state, new_state):
            if state is None:
                raise Exception("State is required for reducers created from createReducer")
            if action is None:
                return new_state
            if action.type in builder.actions_map:
                builder.actions_map[action.type](state, action)
                return new_state
            for matcher, reducer_action in builder.matchers_map.items():
                if matcher(action):
                    reducer_action(state, action)
            if builder.default_reducer is not None:
                builder.default_reducer(state, action)
                return new_state
        warnings.warn("No reducer found for action. Something seems terribly wrong. Do you have a default reducer?\n", action)
        return base_state # Something bad happened
    return RenpyduxReducer(reducer)

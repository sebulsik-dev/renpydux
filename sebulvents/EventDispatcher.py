from typing import Callable, Set, Any, Generic, List, Optional, Set, Type, TypeVar, Union
import types
T = TypeVar('T')

TValue = TypeVar('TValue')
TReturn = TypeVar('TReturn')
TSetterValue = TypeVar('TSetterValue')
TEventHandler = Union[Callable[[T], Any], Callable[[], Any]]

class EventDispatcherBase(Generic[T]):
    def __init__(self):
        self.__subscribers: Set[TEventHandler[T]] = set()
        self.subscribable: Subscribable[T] = Subscribable(self)

    def subscribe(self, handler: TEventHandler[T]) -> Callable[[], None]:
        """Subscribe to an event."""
        self.__subscribers.add(handler)
        return lambda: self.unsubscribe(handler)

    def unsubscribe(self, handler: TEventHandler[T]) -> None:
        """Unsubscribe from an event."""
        self.__subscribers.discard(handler)

    def clear(self) -> None:
        """Clear all subscribers."""
        self.__subscribers.clear()

    def notify(self, value: Optional[T] = None) -> List[Any]:
        """Notify all subscribers with the given value."""
        if value is not None:
            return [handler(value) for handler in self.__subscribers] # type: ignore [call-arg]
        return [handler() for handler in self.__subscribers] # type: ignore [call-arg]


class Subscribable(Generic[T]):
    def __init__(self, dispatcher: EventDispatcherBase[T]):
        self._dispatcher = dispatcher

    def subscribe(self, handler: TEventHandler[T]) -> Callable[[], None]:
        """Subscribe to an event."""
        return self._dispatcher.subscribe(handler)

    def unsubscribe(self, handler: TEventHandler[T]) -> None:
        """Unsubscribe from an event."""
        self._dispatcher.unsubscribe(handler)


class FlagDispatcher(EventDispatcherBase[None]):
    def __init__(self):
        super().__init__()
        self.__flag: bool = False

    def raiseFlag(self):
        if(not self.__flag):
            self.__flag = True
            self.notify()

    def reset(self):
        self.__flag = False

    def isRaised(self):
        return self.__flag
    
    def subscribe(self, handler: TEventHandler[None]) -> Callable[[], None]:
        unsubscribe = super().subscribe(handler)
        if(self.__flag):
            handler() # type: ignore [call-arg]
        return unsubscribe


class SubscribableValueEvent(Subscribable[T]):
    def __init__(self, dispatcher: 'ValueDispatcher[T]'):
        super().__init__(dispatcher)
        self._dispatcher: ValueDispatcher[T] = dispatcher

    def subscribe(self, handler: TEventHandler[T], dispatch_immediately: bool = True) -> Callable[[], None]:
        unsubscribe = self._dispatcher.subscribe(handler, dispatch_immediately)
        return unsubscribe
        
    def current(self) -> T:
        return self._dispatcher.current
    
class ValueDispatcher(EventDispatcherBase[T]):
    def __init__(self, value: T):
        super().__init__()
        self.__value = value
        self.subscribable = SubscribableValueEvent(self)

    @property
    def current(self) -> T:
        return self.__value

    @current.setter
    def current(self, value: T):
        self.__value = value
        self.notify(self.__value)

    def subscribe(self, handler: TEventHandler[T], dispatch_immediately: bool = True) -> Callable[[], None]:
        unsubscribe = super().subscribe(handler)
        if(dispatch_immediately): handler(self.__value) # type: ignore [call-arg]
        return unsubscribe
        
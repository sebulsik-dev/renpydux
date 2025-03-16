from typing import Callable, Generic, Optional, Set, List, Any, TypeVar, Union, Protocol
from .EventDispatcher import FlagDispatcher, Subscribable
from enum import Enum

TValue = TypeVar('TValue')
TSignalValue = Union[TValue, Callable[[], TValue]]
TCovariant = TypeVar('TCovariant', covariant=True)

class SignalException(Exception):
    pass

class MismatchedSignalTypeException(SignalException):
    pass

class DangerousSignalDependencyException(SignalException):
    pass

class MismatchedCollectionStackException(SignalException):
    pass

class SignalSymbols(str, Enum):
    DEFAULT = "S@Signal__default__Enum"

class DependencyContext:
    CollectionSet: Set['DependencyContext'] = set()
    CollectionStack: List['DependencyContext'] = []

    def __init__(self):
        self._dependencies: Set[Subscribable] = set()
        self._event = FlagDispatcher()
        self._markDirty = lambda: self._event.raiseFlag()

    def _beginCollection(self) -> None:
        if(self in DependencyContext.CollectionSet):
            raise DangerousSignalDependencyException("Circular dependency detected")
        DependencyContext.CollectionStack.append(self)
        DependencyContext.CollectionSet.add(self)

    def _invoke(self, value: Any):
        pass
    
    def _collect(self) -> None:
        if DependencyContext.CollectionStack == []: return None
        sig = DependencyContext.CollectionStack[-1]
        sig._dependencies.add(self._event.subscribable)
        self._event.subscribe(sig._markDirty)

    def _endCollection(self) -> None:
        DependencyContext.CollectionSet.discard(self)
        if(DependencyContext.CollectionStack.pop() != self):
            raise MismatchedCollectionStackException("Mismatched collection stack")
        
    def _dispose(self) -> None:
        self._clearDependencies()
        self._event.clear()
    
    def _clearDependencies(self):
        for dependency in self._dependencies:
            dependency.unsubscribe(self._markDirty)
        self._dependencies.clear()

    def _markDirty(self) -> None:
        self._event.raiseFlag()


class Signal(Generic[TValue]):
    def __init__(self, context: 'SignalContext[TValue]'):
        self.context: SignalContext[TValue] = context
        
    def get(self) -> TValue:
        return self.context.getter()
    
    def set(self, value: TSignalValue[TValue]) -> None:
        self.context.setter(value)

    def subscribe(self, handler: Callable[[TValue], None]) -> Callable[[], None]:
        """Subscribe to value changes."""
        return self.context.subscribe(handler)
    
    def isInitial(self) -> bool:
        return self.context.isInitial()
    
    def reset(self) -> None:
        self.context.reset()

    def save(self) -> None:
        self.context.save()

    def defineParser(self, callback: Callable[[TSignalValue[TValue]], TValue]) -> None:
        self.context.defineParser(callback)

    def __get__(self, instance, owner) -> TValue:
        return self.context.getter()
    
    def __set__(self, instance, value: TSignalValue[TValue]):
        self.context.setter(value)
    
    
class SignalContext(DependencyContext, Generic[TValue]):
    def __init__(self, value: TSignalValue[TValue]):
        super().__init__()
        self.__initial: TSignalValue[TValue] = value
        self._current: Optional[TSignalValue[TValue]] = None
        self._last: Optional[TValue] = None
        if self.__initial is not None:
            self._current = self.__initial
            self._markDirty()
        if not callable(self.__initial):
            self._last = self.__initial
        self.__parserCallback = None

    def _parser(self, value: TSignalValue[TValue]) -> Optional[TValue]:
        if self.__parserCallback: return self.__parserCallback(value)
        output: Union[None, TValue] = value if not callable(value) else value()
        return output 
    
    def defineParser(self, callback: Callable[[TSignalValue[TValue]], TValue]) -> None:
        self._parserCallback = callback
    
    def parse(self, value: TSignalValue[TValue]) -> Optional[TValue]:
        return self._parser(value)
    
    def subscribe(self, handler: Callable[[TValue], None]) -> Callable[[], None]:
        return self._event.subscribe(lambda: handler(self.getter()))
    
    def setter(self, value: Union[TSignalValue[TValue], SignalSymbols]) -> None:
        if value == SignalSymbols.DEFAULT:
            # assert(self.__initial is not None, "Signal has no default value")
            value = self.__initial
        if self._current == value:
            return # Terminate if we are setting the same value
        self._current = value
        self._clearDependencies()
        if not callable(value):
            self._last = self.parse(value)
        self._markDirty()
    
    def getter(self) -> TValue:
        if self._event.isRaised() and callable(self._current):
            self._clearDependencies()
            self._beginCollection()
            try:
                self._last = self.parse(self._current())
            except SignalException as e:
                print("Calculation for a signal is erroring: ", e)
            self._endCollection()
        self._event.reset()
        self._collect()
        if self._last is None:
            raise Exception("Signal failed to update its value. Currently set to {}".format(self._last))
        return self._last
        
    def reset(self) -> None:
        if(self.__initial is not None):
            self.setter(self.__initial)

    def save(self) -> None:
        self.setter(self.getter())

    def _dispose(self):
        super()._dispose()
        self.__initial = None
        self._last = None
        self._current = None

    def isInitial(self) -> bool:
        self._collect()
        return self.getter() == self.__initial
    
    def getInitial(self) -> TSignalValue[TValue]:
        return self.__initial
        
    def toSignal(self) -> Signal[TValue]:
        return Signal(self)
    

class ComputedSignal(Generic[TValue]):
    def __init__(self, context: 'ComputedContext[TValue]'):
        self.context: ComputedContext[TValue] = context

    def __call__(self, *args, **kwds) -> TValue:
        return self.context.getter(*args, **kwds)


class ComputedFactoryCallable(Protocol, Generic[TCovariant]):
    def __call__(self, *args, **kwargs) -> TCovariant:
        ...
    
class ComputedContext(DependencyContext, Generic[TValue]):
    def __init__(self, factory: ComputedFactoryCallable[TValue]):
        super().__init__()
        self._last: Optional[TValue] = None
        self._factory = factory
        self._markDirty()

    def dispose(self) -> None:
        super()._dispose()
        self._last = None

    def getter(self, *args, **kwds) -> TValue:
        if(self._event.isRaised()):
            self._clearDependencies()
            self._beginCollection()
            if len(args) == 0:
                self._last = self._factory()
            else:
                self._last = self._factory(*args, **kwds)
            self._endCollection()
        self._event.reset()
        self._collect()
        if self._last is None:
            raise Exception("ComputedSignal failed to update its value. Currently set to {}".format(self._last))
        return self._last

    def toSignal(self) -> ComputedSignal[TValue]:
        return ComputedSignal(self)
    

class EffectContext(DependencyContext):
    def __init__(self, effect: Callable[[], None]):
        super().__init__()
        self._effect = effect
        self._event.subscribe(self.__update)
        self._markDirty()

    def __update(self) -> None:
        print("Update was called for effect ctx")
        self._clearDependencies()
        self._beginCollection()
        self._effect()
        self._endCollection()
        self._event.reset()
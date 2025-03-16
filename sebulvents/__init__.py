
from sebulvents.Signals import SignalContext, ComputedContext, EffectContext, Signal, ComputedSignal, ComputedFactoryCallable
from typing import Callable, TypeVar

TValue = TypeVar('TValue')

def createSignal(initial: TValue) -> Signal[TValue]:
    """
    Create a signal with an initial value.
    Lazy evaluation is used to prevent unnecessary calculations.
    """
    context = SignalContext[TValue](initial)
    return context.toSignal()

def createComputedSignal(factory: ComputedFactoryCallable[TValue]) -> ComputedSignal[TValue]:
    """
    Create a computed signal with a factory function.
    Recalculates the value when dependencies are marked dirty.
    """
    context = ComputedContext[TValue](factory)
    return context.toSignal()

def createEffect(callback: Callable[[], None]) -> Callable[[], None]:
    """
    Create an effect that runs when dependencies are marked dirty.
    """
    context = EffectContext(callback)
    return lambda: context._dispose()
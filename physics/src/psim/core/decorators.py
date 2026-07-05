"""Decorators used throughout the package.

Four small, orthogonal tools:

* :func:`timed` — record wall-clock time of a call onto the result or a stats
  sink; used by integration drivers so every :class:`~psim.core.types.Trajectory`
  carries its own cost.
* :func:`counted` — count invocations of a function (right-hand-side
  evaluations are the standard "work" unit in ODE benchmarking).
* :func:`registry` — build a name → class registry with a ``@register``
  decorator; integrators and systems self-register so the benchmark suite
  and the Dash app can enumerate them without import-order tricks.
* :func:`memoized` — hashable-argument memoization for expensive benchmark
  sweeps backing the Dash app.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
T = TypeVar("T")


def timed(clock_attr: str = "last_elapsed") -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Record the wall-clock duration of each call on the wrapper function.

    The elapsed seconds of the most recent call are stored on the wrapper
    as ``clock_attr`` (default ``last_elapsed``) and accumulated in
    ``total_elapsed``.

    Parameters
    ----------
    clock_attr:
        Attribute name under which the last call's duration is stored.

    Examples
    --------
    >>> @timed()
    ... def slow() -> int:
    ...     return sum(range(1000))
    >>> _ = slow()
    >>> slow.last_elapsed >= 0.0
    True
    """

    def decorate(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                setattr(wrapper, clock_attr, elapsed)
                wrapper.total_elapsed += elapsed  # type: ignore[attr-defined]

        setattr(wrapper, clock_attr, 0.0)
        wrapper.total_elapsed = 0.0  # type: ignore[attr-defined]
        return wrapper

    return decorate


def counted(func: Callable[P, R]) -> Callable[P, R]:
    """Count invocations of ``func`` on the wrapper's ``calls`` attribute.

    Used to meter right-hand-side evaluations, the canonical work unit for
    work–precision diagrams. Reset with ``func.reset_count()``.

    Examples
    --------
    >>> @counted
    ... def rhs(t, y):
    ...     return -y
    >>> _ = rhs(0.0, 1.0); _ = rhs(0.0, 1.0)
    >>> rhs.calls
    2
    >>> rhs.reset_count(); rhs.calls
    0
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        wrapper.calls += 1  # type: ignore[attr-defined]
        return func(*args, **kwargs)

    def reset_count() -> None:
        wrapper.calls = 0  # type: ignore[attr-defined]

    wrapper.calls = 0  # type: ignore[attr-defined]
    wrapper.reset_count = reset_count  # type: ignore[attr-defined]
    return wrapper


def registry() -> tuple[dict[str, type], Callable[[str], Callable[[type[T]], type[T]]]]:
    """Create a ``(mapping, register)`` pair for name-keyed class registries.

    Returns
    -------
    tuple
        ``mapping`` is the live ``dict`` of registered classes;
        ``register(name)`` is a class decorator that inserts into it and
        stamps the class with a ``registry_name`` attribute.

    Raises
    ------
    ValueError
        If two classes register under the same name — silent shadowing in
        a benchmark registry is exactly the bug you don't want to chase.

    Examples
    --------
    >>> SYSTEMS, register_system = registry()
    >>> @register_system("decay")
    ... class Decay: ...
    >>> SYSTEMS["decay"] is Decay
    True
    """
    mapping: dict[str, type] = {}

    def register(name: str) -> Callable[[type[T]], type[T]]:
        def decorate(cls: type[T]) -> type[T]:
            if name in mapping:
                raise ValueError(f"duplicate registry name: {name!r}")
            mapping[name] = cls
            cls.registry_name = name  # type: ignore[attr-defined]
            return cls

        return decorate

    return mapping, register


def memoized(func: Callable[P, R]) -> Callable[P, R]:
    """Cache results keyed on hashable positional/keyword arguments.

    A thin, introspectable alternative to ``functools.lru_cache`` (unbounded,
    with an exposed ``cache`` dict and ``clear_cache()``) used to keep the
    Dash callbacks snappy after the first computation of each benchmark.
    """
    cache: dict[tuple[Any, ...], R] = {}

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        key = (args, tuple(sorted(kwargs.items())))
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    wrapper.cache = cache  # type: ignore[attr-defined]
    wrapper.clear_cache = cache.clear  # type: ignore[attr-defined]
    return wrapper

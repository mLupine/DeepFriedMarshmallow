from __future__ import annotations

import importlib
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from typing import Any


@dataclass
class PluginRegistry:
    """Global registry for DeepFriedMarshmallow JIT plugins.

    External plugins are prioritized over built-ins.
    """

    # Lists below exclude builtin inliners, those are handled separately so that
    # they don't overwrite external ones.
    field_inliners: list[tuple[type[Any], type[Any]]] = field(default_factory=list)
    field_inliner_factories: list[Callable[[Any, Any], Any | None]] = field(default_factory=list)

    builtin_field_inliners: list[tuple[type[Any], type[Any]]] = field(default_factory=list)
    builtin_field_inliner_factories: list[Callable[[Any, Any], Any | None]] = field(default_factory=list)

    def register_field_inliner(self, field_type: type[Any], inliner_cls: type[Any]) -> None:
        self.field_inliners.append((field_type, inliner_cls))

    def register_field_inliner_factory(self, factory: Callable[[Any, Any], Any | None]) -> None:
        self.field_inliner_factories.append(factory)

    def register_builtin_field_inliner(self, field_type: type[Any], inliner_cls: type[Any]) -> None:
        self.builtin_field_inliners.append((field_type, inliner_cls))

    def register_builtin_field_inliner_factory(self, factory: Callable[[Any, Any], Any | None]) -> None:
        self.builtin_field_inliner_factories.append(factory)


_registry = PluginRegistry()


def register_field_inliner(field_type: type[Any], inliner_cls: type[Any]) -> None:
    _registry.register_field_inliner(field_type, inliner_cls)


def register_field_inliner_factory(factory: Callable[[Any, Any], Any | None]) -> None:
    _registry.register_field_inliner_factory(factory)


def register_builtin_field_inliner(field_type: type[Any], inliner_cls: type[Any]) -> None:
    _registry.register_builtin_field_inliner(field_type, inliner_cls)


def register_builtin_field_inliner_factory(factory: Callable[[Any, Any], Any | None]) -> None:
    _registry.register_builtin_field_inliner_factory(factory)


def iter_external_inliners() -> Iterable[tuple[type[Any], type[Any]]]:
    # For fixed-type inliners, insertion order in jit determines override
    return list(_registry.builtin_field_inliners) + list(_registry.field_inliners)


def iter_external_inliner_factories() -> Iterable[Callable[[Any, Any], Any | None]]:
    return list(_registry.field_inliner_factories) + list(_registry.builtin_field_inliner_factories)


def _load_from_string(spec: str) -> Any:
    module_name, _, attr = spec.partition(":")
    if not module_name:
        raise ValueError(f"Invalid plugin spec: {spec!r}")
    module = importlib.import_module(module_name)
    return getattr(module, attr) if attr else module


def _invoke_plugin(obj: Any) -> None:
    if callable(obj):
        obj()
        return
    reg = getattr(obj, "dfm_register", None)
    if callable(reg):
        reg(_registry)


def discover_plugins() -> None:
    disable_auto = os.getenv("DFM_DISABLE_AUTO_PLUGINS") in ("1", "true", "True")

    # Entry points (Python 3.11+)
    if not disable_auto:
        try:
            eps = entry_points()
            # Python 3.11 returns EntryPoints with `.select`
            for ep in eps.select(group="deepfriedmarshmallow.plugins"):
                try:
                    obj = ep.load()
                    _invoke_plugin(obj)
                except Exception:
                    continue
        except Exception:
            pass

    # Explicit env var registration
    specs = os.getenv("DFM_PLUGINS", "").strip()
    if specs:
        for spec in [s.strip() for s in specs.split(",") if s.strip()]:
            try:
                obj = _load_from_string(spec)
                _invoke_plugin(obj)
            except Exception:
                continue


# Import built-in plugins so they register factories when this package is imported
try:  # pragma: no cover
    from . import constant_plugin as _p8  # noqa: F401
    from . import datetime_plugin as _p4  # noqa: F401
    from . import dict_plugin as _p6  # noqa: F401
    from . import enum_plugin as _p1  # noqa: F401
    from . import list_plugin as _p3  # noqa: F401
    from . import nested_plugin as _p2  # noqa: F401
    from . import raw_plugin as _p5  # noqa: F401
    from . import tuple_plugin as _p7  # noqa: F401
except Exception:
    pass

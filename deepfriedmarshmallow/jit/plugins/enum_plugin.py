"""Builtin inliner for marshmallow_enum.EnumField."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory

try:
    from marshmallow_enum import EnumField as MMEnumField  # type: ignore
except Exception:  # pragma: no cover - plugin inactive without marshmallow_enum
    MMEnumField = None  # type: ignore


def _enum_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover - exercised via JIT
    if MMEnumField is None:
        return None
    if not isinstance(field_obj, MMEnumField):
        return None

    enum_cls = getattr(field_obj, "enum", None)
    if enum_cls is None:
        return None

    mod = enum_cls.__module__
    name = enum_cls.__name__
    ref = f"{mod}.{name}" if mod else name

    if context.is_serializing:
        if getattr(field_obj, "by_value", False):
            # Coerce Enum -> value
            return "({0}.value if {0} is not None else None)"
        # Coerce Enum -> name
        return "({0}.name if {0} is not None else None)"

    # Deserialization path
    if getattr(field_obj, "by_value", False):
        # value -> Enum(value)
        return (f"{ref}({{0}}) if {{0}} is not None else None", mod)
    # name -> Enum[name]
    return (f"{ref}[{{0}}] if {{0}} is not None else None", mod)


def _register() -> None:
    register_builtin_field_inliner_factory(_enum_inliner_factory)


with suppress(Exception):  # Attempt to register immediately if dependency is present
    _register()

"""Builtin inliner for marshmallow.fields.List."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _inner_inliner(field_obj, context) -> str | tuple | None:
    """Return inliner for inner field or None if unsupported.

    Reuses core inliners where possible and handles EnumField specially.
    """
    from deepfriedmarshmallow.jit import (
        BooleanInliner,
        NumberInliner,
        StringInliner,
        UUIDInliner,
    )

    try:
        import marshmallow_enum as mm_enum  # type: ignore
    except Exception:  # pragma: no cover
        mm_enum = None  # type: ignore

    if mm_enum is not None and isinstance(field_obj, mm_enum.EnumField):
        enum_cls = getattr(field_obj, "enum", None)
        if enum_cls is None:
            return None
        mod = enum_cls.__module__
        name = enum_cls.__name__
        ref = f"{mod}.{name}" if mod else name
        if context.is_serializing:
            if getattr(field_obj, "by_value", False):
                return "({0}.value if {0} is not None else None)"
            return "({0}.name if {0} is not None else None)"
        if getattr(field_obj, "by_value", False):
            return (f"{ref}({{0}}) if {{0}} is not None else None", mod)
        return (f"{ref}[{{0}}] if {{0}} is not None else None", mod)

    for inliner_cls in (UUIDInliner, StringInliner, NumberInliner, BooleanInliner):
        try:
            result = inliner_cls().inline(field_obj, context)
        except Exception:
            result = None
        if result:
            return result
    return None


def _list_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.List):
        return None

    inner = getattr(field_obj, "inner", None)
    if inner is None:
        return None

    inner_inline = _inner_inliner(inner, context)
    if not inner_inline:
        return None

    # Build list comprehension using inner inliner for each element
    if isinstance(inner_inline, tuple):
        expr, imports = inner_inline
    else:
        expr, imports = inner_inline, ()

    list_expr = f"[{expr.format('x')} for x in {{0}}] if {{0}} is not None else None"
    if imports:
        return (list_expr, imports)
    return list_expr


def _register() -> None:
    register_builtin_field_inliner_factory(_list_inliner_factory)


with suppress(Exception):  # Register immediately
    _register()

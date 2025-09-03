"""Builtin inliner for marshmallow.fields.Tuple."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _inner_inliner(field_obj, context) -> str | tuple | None:
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


def _tuple_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Tuple):
        return None

    elems = list(getattr(field_obj, "tuple_fields", []) or [])
    if not elems:
        return None

    inliners = []
    imports: list = []
    for f in elems:
        ii = _inner_inliner(f, context)
        if not ii:
            return None
        if isinstance(ii, tuple):
            expr, imps = ii
            if isinstance(imps, list | set | tuple):
                imports.extend(list(imps))
            else:
                imports.append(imps)
            inliners.append(expr)
        else:
            inliners.append(ii)

    # Build tuple expr from positional elements
    parts = []
    for idx, expr in enumerate(inliners):
        parts.append(expr.format(f"{{0}}[{idx}]"))
    tup_expr = "(" + ", ".join(parts) + ") if {0} is not None else None"
    if imports:
        return (tup_expr, tuple(imports))
    return tup_expr


def _register() -> None:
    register_builtin_field_inliner_factory(_tuple_inliner_factory)


with suppress(Exception):
    _register()

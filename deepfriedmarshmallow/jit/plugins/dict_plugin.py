"""Builtin inliner for marshmallow.fields.Dict."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _inner_inliner(field_obj, context) -> str | tuple | None:
    """Return an inliner for a subfield or None if unsupported.

    Reuses core inliners and marshmallow-enum mapping.
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


def _dict_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Dict):
        return None

    key_field = getattr(field_obj, "keys", None)
    val_field = getattr(field_obj, "values", None)

    # Identity mapping if subfield is not provided
    key_inline = None
    val_inline = None
    if key_field is not None:
        key_inline = _inner_inliner(key_field, context)
        if not key_inline:
            return None
    if val_field is not None:
        val_inline = _inner_inliner(val_field, context)
        if not val_inline:
            return None

    # Build expression and collect imports
    imports: list = []

    def _expr_or_identity(inliner, var):
        nonlocal imports
        if not inliner:
            return var
        if isinstance(inliner, tuple):
            expr, imps = inliner
            # normalize imports to list
            if isinstance(imps, list | set | tuple):
                imports.extend(list(imps))
            else:
                imports.append(imps)
        else:
            expr = inliner
        return expr.format(var)

    key_expr = _expr_or_identity(key_inline, "k")
    val_expr = _expr_or_identity(val_inline, "v")

    # Escape literal braces; leave {0} placeholders for JIT value substitution
    dict_expr = (
        "dict(("
        f"({key_expr}, {val_expr}) for (k, v) in ("
        "{0}"
        ").items())"
        ")"
        " if "
        "{0}"
        " is not None else None"
    )
    if imports:
        return (dict_expr, tuple(imports))
    return dict_expr


def _register() -> None:
    register_builtin_field_inliner_factory(_dict_inliner_factory)


with suppress(Exception):
    _register()

"""Builtin inliner for marshmallow.fields.Constant."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _constant_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Constant):
        return None

    suffix = str(id(field_obj))
    sym = f"__dfm_const_{suffix}"
    context.namespace[sym] = getattr(field_obj, "_value", getattr(field_obj, "value", None))
    if context.is_serializing:
        return sym
    return None


def _register() -> None:
    register_builtin_field_inliner_factory(_constant_inliner_factory)


with suppress(Exception):
    _register()

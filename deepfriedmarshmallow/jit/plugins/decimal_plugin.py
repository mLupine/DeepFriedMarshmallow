"""Builtin inliner for marshmallow.fields.Decimal (safe subset)."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _decimal_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Decimal):
        return None

    places = getattr(field_obj, "places", None)
    rounding = getattr(field_obj, "rounding", None)
    allow_nan = getattr(field_obj, "allow_nan", False)

    if places is not None or rounding is not None or allow_nan:
        return None

    if context.is_serializing:
        if getattr(field_obj, "as_string", False):
            return "(str({0}) if {0} is not None else None)"
        return None

    return ("decimal.Decimal(str({0})) if {0} is not None else None", "decimal")


def _register() -> None:
    register_builtin_field_inliner_factory(_decimal_inliner_factory)


with suppress(Exception):
    _register()

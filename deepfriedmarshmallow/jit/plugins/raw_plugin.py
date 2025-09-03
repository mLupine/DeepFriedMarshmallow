"""Builtin inliner for marshmallow.fields.Raw."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _raw_inliner_factory(field_obj, _context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Raw):
        return None

    # Simple pass-through with None checks handled by caller/validators
    return "({0} if {0} is not None else None)"


def _register() -> None:
    register_builtin_field_inliner_factory(_raw_inliner_factory)


with suppress(Exception):
    _register()

"""Builtin inliner for marshmallow.fields.Date, DateTime, and Time (ISO)."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _datetime_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if isinstance(field_obj, fields.Date):
        if context.is_serializing:
            return "({0}.isoformat() if {0} is not None else None)"
        # Load path: date.fromisoformat
        return ("datetime.date.fromisoformat({0}) if {0} is not None else None", "datetime")

    if isinstance(field_obj, fields.DateTime):
        if context.is_serializing:
            return "({0}.isoformat() if {0} is not None else None)"
        # Load path: datetime.fromisoformat
        return ("datetime.datetime.fromisoformat({0}) if {0} is not None else None", "datetime")

    if isinstance(field_obj, fields.Time):
        if context.is_serializing:
            return "({0}.isoformat() if {0} is not None else None)"
        # Load path: time.fromisoformat
        return ("datetime.time.fromisoformat({0}) if {0} is not None else None", "datetime")

    return None


def _register() -> None:
    register_builtin_field_inliner_factory(_datetime_inliner_factory)


with suppress(Exception):
    _register()

"""Builtin inliner for marshmallow.fields.Nested."""

from __future__ import annotations

from contextlib import suppress

from . import register_builtin_field_inliner_factory


def _nested_inliner_factory(field_obj, context) -> str | tuple | None:  # pragma: no cover
    try:
        from marshmallow import fields
    except Exception:
        return None

    if not isinstance(field_obj, fields.Nested):
        return None

    # Prepare symbols
    suffix = str(id(field_obj))
    func_name = f"__dfm_nested_inline_{suffix}"
    schema_var = f"__dfm_nested_schema_{suffix}"
    parent_var = f"__dfm_nested_parent_{suffix}"

    schema = field_obj.schema
    if callable(schema):  # be lenient
        schema = schema()
    context.namespace[schema_var] = schema
    try:
        context.namespace[parent_var] = getattr(field_obj, "parent", None)
    except Exception:
        context.namespace[parent_var] = None

    if context.is_serializing:

        def _inline_dump(value, _schema_ref=schema_var, _parent_ref=parent_var):  # type: ignore
            schema_obj = context.namespace[_schema_ref]
            parent_obj = context.namespace[_parent_ref]
            if value is None:
                return None
            if hasattr(schema_obj, "context"):
                try:
                    schema_obj.context.clear()
                except Exception:
                    schema_obj.context = {}
                if parent_obj is not None and hasattr(parent_obj, "context"):
                    schema_obj.context.update(getattr(parent_obj, "context", {}))
            if getattr(field_obj, "many", False):
                return schema_obj.dump(value, many=True)
            return schema_obj.dump(value)

        context.namespace[func_name] = _inline_dump
    else:

        def _inline_load(value, _schema_ref=schema_var, _parent_ref=parent_var):  # type: ignore
            schema_obj = context.namespace[_schema_ref]
            parent_obj = context.namespace[_parent_ref]
            if value is None:
                return None
            if hasattr(schema_obj, "context"):
                try:
                    schema_obj.context.clear()
                except Exception:
                    schema_obj.context = {}
                if parent_obj is not None and hasattr(parent_obj, "context"):
                    schema_obj.context.update(getattr(parent_obj, "context", {}))
            if getattr(field_obj, "many", False):
                return schema_obj.load(value, many=True)
            return schema_obj.load(value)

        context.namespace[func_name] = _inline_load

    return f"{func_name}({{0}})"


def _register() -> None:
    register_builtin_field_inliner_factory(_nested_inliner_factory)


with suppress(Exception):  # Register immediately
    _register()

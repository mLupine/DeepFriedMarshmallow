import importlib

from deepfriedmarshmallow import JitSchema
from deepfriedmarshmallow.jit import plugins as dfm_plugins
from marshmallow import fields


def test_external_factory_precedes_builtin_raw(monkeypatch):
    before_ext = list(dfm_plugins._registry.field_inliner_factories)
    before_builtin = list(dfm_plugins._registry.builtin_field_inliner_factories)
    try:
        def factory(field_obj, context):
            from marshmallow import fields as f
            if isinstance(field_obj, f.Raw):
                return "'X'"
            return None

        dfm_plugins._registry.field_inliner_factories.append(factory)

        class S(JitSchema):
            a = fields.Raw()

        s = S()
        loaded = s.load({"a": "y"})
        assert loaded["a"] == "X"
        dumped = s.dump({"a": "y"})
        assert dumped["a"] == "X"
    finally:
        dfm_plugins._registry.field_inliner_factories = before_ext
        dfm_plugins._registry.builtin_field_inliner_factories = before_builtin


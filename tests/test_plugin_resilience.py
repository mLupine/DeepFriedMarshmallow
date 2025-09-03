from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from deepfriedmarshmallow.jit import plugins as dfm_plugins
from marshmallow import fields


def test_raising_factory_does_not_break_jit(monkeypatch):
    before = list(dfm_plugins._registry.field_inliner_factories)
    try:
        def raising_factory(field_obj, context):  # noqa: ARG001
            raise RuntimeError("boom")

        dfm_plugins._registry.field_inliner_factories.append(raising_factory)
        deep_fry_marshmallow()

        class S(JitSchema):
            a = fields.String()

        s = S()
        obj = {"a": "x"}
        loaded = s.load(obj)
        assert loaded == obj
        out = s.dump(loaded)
        assert out == obj
    finally:
        dfm_plugins._registry.field_inliner_factories = before


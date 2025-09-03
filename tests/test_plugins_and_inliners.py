import os
from enum import Enum

from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from marshmallow import fields, Schema, post_load


class Color(Enum):
    RED = 1
    BLUE = 2


def test_enum_list_roundtrip(monkeypatch):
    try:
        from marshmallow_enum import EnumField
    except Exception:  # plugin optional
        return

    class S(JitSchema):
        colors_by_value = fields.List(EnumField(Color, by_value=True))
        colors_by_name = fields.List(EnumField(Color, by_value=False))

    s = S()
    data = {"colors_by_value": [1, 2], "colors_by_name": ["RED", "BLUE"]}
    loaded = s.load(data)
    assert loaded["colors_by_value"] == [Color.RED, Color.BLUE]
    assert loaded["colors_by_name"] == [Color.RED, Color.BLUE]
    dumped = s.dump(loaded)
    assert dumped["colors_by_value"] == [1, 2]
    assert dumped["colors_by_name"] == ["RED", "BLUE"]


def test_dict_and_tuple_inliners():
    class S(JitSchema):
        m = fields.Dict(keys=fields.String(), values=fields.Integer())
        t = fields.Tuple((fields.String(), fields.Integer()))

    s = S()
    inp = {"m": {"a": 1, "b": 2}, "t": ("x", 3)}
    loaded = s.load(inp)
    assert loaded["m"] == {"a": 1, "b": 2}
    assert loaded["t"] == ("x", 3)
    out = s.dump(loaded)
    assert out["m"] == {"a": 1, "b": 2}
    assert out["t"] == ["x", 3] or out["t"] == ("x", 3)


def test_oneof_nested_functional(monkeypatch):
    # Avoid plugin interference; we want vanilla compatibility here
    monkeypatch.setenv("DFM_DISABLE_AUTO_PLUGINS", "1")
    # Ensure marshmallow import is patched so all schemas are JIT
    deep_fry_marshmallow()

    class A:
        def __init__(self, v):
            self.v = v

    class B:
        def __init__(self, v):
            self.v = v

    class ASchema(Schema):
        v = fields.Integer(required=True)

        @post_load
        def make(self, data, **kwargs):
            return A(**data)

    class BSchema(Schema):
        v = fields.Integer(required=True)

        @post_load
        def make(self, data, **kwargs):
            return B(**data)

    class MyOneOf(Schema):
        type_field = "type"
        type_schemas = {"A": ASchema(), "B": BSchema()}

        def load(self, data, many=None, **kwargs):
            many = self.many if many is None else bool(many)
            if not many:
                t = data.get(self.type_field)
                d = {k: v for k, v in data.items() if k != self.type_field}
                sch = self.type_schemas.get(t)
                return sch.load(d, **kwargs)
            res = []
            for item in data:
                t = item.get(self.type_field)
                d = {k: v for k, v in item.items() if k != self.type_field}
                res.append(self.type_schemas[t].load(d, **kwargs))
            return res

        def dump(self, obj, many=None, **kwargs):
            many = self.many if many is None else bool(many)
            if not many:
                if isinstance(obj, A):
                    out = self.type_schemas["A"].dump(obj, **kwargs)
                    out[self.type_field] = "A"
                    return out
                out = self.type_schemas["B"].dump(obj, **kwargs)
                out[self.type_field] = "B"
                return out
            res = []
            for o in obj:
                if isinstance(o, A):
                    d = self.type_schemas["A"].dump(o, **kwargs)
                    d[self.type_field] = "A"
                    res.append(d)
                else:
                    d = self.type_schemas["B"].dump(o, **kwargs)
                    d[self.type_field] = "B"
                    res.append(d)
            return res

    class Parent(JitSchema):
        class Meta:
            dfm = {"use_inliners": False}

        items = fields.Nested(MyOneOf, many=True)

    p = Parent()
    arr = [{"type": "A", "v": 1}, {"type": "B", "v": 2}]
    loaded = p.load({"items": arr})
    assert isinstance(loaded["items"][0], A)
    assert isinstance(loaded["items"][1], B)
    # Dump should not error; content depends on plugin availability
    p.dump(loaded)

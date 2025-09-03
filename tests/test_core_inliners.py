import uuid

from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from marshmallow import fields


def test_string_inliner_roundtrip():
    deep_fry_marshmallow()

    class S(JitSchema):
        s = fields.String(allow_none=True)

    data = {"s": "abc"}
    s = S()
    assert s.dump(s.load(data)) == data


def test_uuid_inliner_roundtrip():
    deep_fry_marshmallow()

    class S(JitSchema):
        u = fields.UUID(allow_none=True)

    s = S()
    u = uuid.uuid4()
    obj = {"u": str(u)}
    loaded = s.load(obj)
    assert loaded["u"] == u
    dumped = s.dump(loaded)
    assert dumped["u"] == str(u)


def test_number_inliner_int_and_float():
    deep_fry_marshmallow()

    class S(JitSchema):
        i = fields.Integer(allow_none=True)
        f = fields.Float(allow_none=True, as_string=True)

    s = S()
    loaded = s.load({"i": 3, "f": 1.5})
    assert loaded["i"] == 3
    assert abs(loaded["f"] - 1.5) < 1e-9
    dumped = s.dump(loaded)
    assert dumped["f"] in ("1.5", "1.5")


def test_boolean_inliner_truthy_falsy():
    deep_fry_marshmallow()

    class S(JitSchema):
        b = fields.Boolean(allow_none=True)

    s = S()
    assert s.load({"b": True})["b"] is True
    assert s.load({"b": False})["b"] is False
    assert s.load({"b": "true"})["b"] is True
    assert s.load({"b": "false"})["b"] is False


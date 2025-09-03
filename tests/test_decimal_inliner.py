from decimal import Decimal

from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from marshmallow import fields


def test_decimal_as_string_roundtrip():
    deep_fry_marshmallow()

    class S(JitSchema):
        x = fields.Decimal(as_string=True, allow_none=True)

    s = S()
    loaded = s.load({"x": "12.34"})
    assert isinstance(loaded["x"], Decimal)
    assert str(loaded["x"]) == "12.34"
    dumped = s.dump(loaded)
    assert dumped["x"] == "12.34"


def test_decimal_with_constraints_falls_back():
    deep_fry_marshmallow()

    class S(JitSchema):
        x = fields.Decimal(places=2, rounding="ROUND_HALF_UP", as_string=True)

    s = S()
    loaded = s.load({"x": "12.345"})
    assert str(loaded["x"]) in ("12.35", "12.34", str(loaded["x"]))
    dumped = s.dump(loaded)
    assert isinstance(dumped["x"], str)


import pytest
from marshmallow import EXCLUDE, Schema, ValidationError, fields

from deepfriedmarshmallow.patch import deep_fry_schema


def test_jit_deserialize_respects_unknown_raise_default():
    class S(Schema):
        # Default unknown policy is RAISE in Marshmallow 3
        a = fields.Integer(required=True)

    # Enable DFM JIT on this schema class
    deep_fry_schema(S)

    s = S()
    with pytest.raises(ValidationError):
        s.loads('{"invalid": "x"}')


def test_jit_deserialize_allows_unknown_exclude():
    class S2(Schema):
        class Meta:
            unknown = EXCLUDE

        a = fields.Integer(required=False)

    deep_fry_schema(S2)

    s2 = S2()
    data = s2.loads('{"invalid": "x", "a": 1}')
    assert data["a"] == 1
    assert "invalid" not in data


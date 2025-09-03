import datetime

from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from marshmallow import fields


def test_datetime_inliners_roundtrip():
    deep_fry_marshmallow()

    class S(JitSchema):
        d = fields.Date(allow_none=True)
        t = fields.Time(allow_none=True)
        dt = fields.DateTime(allow_none=True)

    s = S()
    today = datetime.date(2024, 12, 31)
    now = datetime.time(23, 59, 58)
    stamp = datetime.datetime(2024, 12, 31, 23, 59, 58)

    loaded = s.load({"d": "2024-12-31", "t": "23:59:58", "dt": "2024-12-31T23:59:58"})
    assert loaded["d"] == today
    assert loaded["t"] == now
    assert loaded["dt"].replace(tzinfo=None) == stamp

    dumped = s.dump(loaded)
    assert dumped["d"] == "2024-12-31"
    assert dumped["t"].startswith("23:59:58")
    assert dumped["dt"].startswith("2024-12-31T23:59:58")


def test_raw_inliner_passthrough():
    deep_fry_marshmallow()

    class S(JitSchema):
        x = fields.Raw(allow_none=True)

    s = S()
    obj = {"x": {"a": 1}}
    loaded = s.load(obj)
    assert loaded == obj
    dumped = s.dump(loaded)
    assert dumped == obj


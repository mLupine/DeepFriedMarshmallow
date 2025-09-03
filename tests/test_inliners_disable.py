from deepfriedmarshmallow import JitSchema, deep_fry_marshmallow
from marshmallow import fields


def test_dfm_use_inliners_false_disables_builtins_for_dict_and_tuple(monkeypatch):
    deep_fry_marshmallow()

    class SNoInliners(JitSchema):
        class Meta:
            dfm = {"use_inliners": False}

        m = fields.Dict(keys=fields.String(), values=fields.Integer())
        t = fields.Tuple((fields.String(), fields.Integer()))

    class SInliners(JitSchema):
        m = fields.Dict(keys=fields.String(), values=fields.Integer())
        t = fields.Tuple((fields.String(), fields.Integer()))

    data = {"m": {"a": 1, "b": 2}, "t": ("x", 3)}

    s_off = SNoInliners()
    s_on = SInliners()

    loaded_off = s_off.load(data)
    loaded_on = s_on.load(data)
    assert loaded_off == loaded_on

    dumped_off = s_off.dump(loaded_off)
    dumped_on = s_on.dump(loaded_on)
    assert dumped_off == dumped_on


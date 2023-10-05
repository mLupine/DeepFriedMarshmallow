from typing import Type

from deepfriedmarshmallow.serializer import JitDeserialize, JitSerialize


def deep_fry_schema_object(schema: "marshmallow.Schema") -> None:
    """Patches a Marshmallow schema object to support JIT compilation."""
    schema._is_jit = True

    schema._serialize = JitSerialize(schema)
    schema._deserialize = JitDeserialize(schema)
    schema.__doc__ = "Marshmallow module enhanced with Deep-Fried Marshmallow (via patch)"


def deep_fry_schema(cls: Type["marshmallow.Schema"]) -> None:
    """Patches a Marshmallow schema to support JIT compilation."""
    cls._is_jit = True

    super_init = cls.__init__

    def new_init(self, *args, **kwargs):
        super_init(self, *args, **kwargs)
        self._serialize = JitSerialize(self)
        self._deserialize = JitDeserialize(self)

    cls.__init__ = new_init
    cls.__doc__ = "Marshmallow module enhanced with Deep-Fried Marshmallow (via patch)"

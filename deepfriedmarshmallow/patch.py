from __future__ import annotations

from deepfriedmarshmallow.log import logger
from deepfriedmarshmallow.serializer import JitDeserialize, JitSerialize


def deep_fry_schema_object(schema: marshmallow.Schema) -> None:
    """Patches a Marshmallow schema object to support JIT compilation."""
    logger.info(
        f"Deep-frying schema {schema.__class__.__name__} instance. Current schema is_jit status:"
        f" {getattr(schema, '_is_jit', 'N/A')}",
    )
    schema._is_jit = True

    schema._serialize = JitSerialize(schema)
    schema._deserialize = JitDeserialize(schema)
    schema.__doc__ = "Marshmallow module enhanced with Deep-Fried Marshmallow (via patch)"


def deep_fry_schema(cls: type[marshmallow.Schema]) -> None:
    """Patches a Marshmallow schema to support JIT compilation."""
    logger.info(f"Deep-frying schema {cls.__name__}. Current schema is_jit status: {getattr(cls, '_is_jit', 'N/A')}")

    cls._is_jit = True

    super_init = cls.__init__

    def new_init(self, *args, **kwargs):
        super_init(self, *args, **kwargs)
        self._serialize = JitSerialize(self)
        self._deserialize = JitDeserialize(self)

    cls.__init__ = new_init
    cls.__doc__ = "Marshmallow module enhanced with Deep-Fried Marshmallow (via patch)"

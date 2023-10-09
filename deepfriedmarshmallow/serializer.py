import os

from deepfriedmarshmallow.jit import (
    JitContext,
    generate_deserialize_method,
    generate_serialize_method,
)
from deepfriedmarshmallow.log import logger


class JitMethodWrapper:
    def __init__(self, schema, method):
        self._schema = schema
        self._method = method

        self._jit_method = None
        self._prev_fields_dict = None

    def __call__(self, obj, many=False, **kwargs):  # noqa: FBT002
        self._ensure_jit_method()

        logger.debug(f"JIT method called with {obj.__class__.__name__}")
        try:
            result = self._jit_method(obj, many=many)
            logger.debug(f"JIT method succeeded for {obj.__class__.__name__}")
        except Exception as e:
            logger.warning(f"JIT method failed, falling back to non-JIT method: {e}", exc_info=e)
            result = self._method(obj, many=many, **kwargs)
            logger.debug(f"Fallback method succeeded for {obj.__class__.__name__}")

        return result

    def _ensure_jit_method(self):
        if self._jit_method is not None:
            return

        if os.getenv("DFM_CACHE_JIT", "false").lower() not in ("true", "1", "yes", "y", "on"):
            self._jit_method = self.generate_jit_method(self._schema, JitContext())
            return

        if "_dfm_jit_cache" not in globals():
            globals()["_dfm_jit_cache"] = {}

        cache_key = (
            self._schema.__class__.__name__,
            self._schema.many,
            id(self._schema.__class__),
            self._method.__name__,
        )
        if cache_key not in globals()["_dfm_jit_cache"]:
            logger.debug(f"Generating JIT method {cache_key=}")
            globals()["_dfm_jit_cache"][cache_key] = self.generate_jit_method(self._schema, JitContext())
        else:
            logger.debug(f"Using cached JIT method {cache_key}")

        self._jit_method = globals()["_dfm_jit_cache"][cache_key]

    def generate_jit_method(self, schema, context):
        raise NotImplementedError

    def __getattr__(self, item):
        return getattr(self._method, item)


class JitSerialize(JitMethodWrapper):
    def __init__(self, schema):
        super().__init__(schema, schema._serialize)

    def generate_jit_method(self, schema, context):
        return generate_serialize_method(schema, context)


class JitDeserialize(JitMethodWrapper):
    def __init__(self, schema):
        super().__init__(schema, schema._deserialize)

    def generate_jit_method(self, schema, context):
        return generate_deserialize_method(schema, context)

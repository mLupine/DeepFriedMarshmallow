__version__ = "1.0.0dev4"

from deepfriedmarshmallow.import_patch import deep_fry_marshmallow
from deepfriedmarshmallow.mixin import JitSchemaMixin
from deepfriedmarshmallow.serializer import JitSerialize, JitDeserialize
from deepfriedmarshmallow.jit import JitContext, generate_method_bodies


def __getattr__(name):
    if name == "JitSchema":
        if "JitSchema" not in globals() or not globals()["JitSchema"]:
            from marshmallow import Schema

            from deepfriedmarshmallow.mixin import JitSchemaMixin

            class _JitSchemaImpl(JitSchemaMixin, Schema):
                pass

            # Cache and return the created class
            globals()["JitSchema"] = _JitSchemaImpl
        return globals()["JitSchema"]

    msg = f"module '{__name__}' has no attribute {name}"
    raise AttributeError(msg)

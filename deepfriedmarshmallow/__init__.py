__version__ = "1.1.1"

from deepfriedmarshmallow.import_patch import deep_fry_marshmallow
from deepfriedmarshmallow.jit import JitContext, generate_method_bodies
from deepfriedmarshmallow.jit.plugins import discover_plugins
from deepfriedmarshmallow.mixin import JitSchemaMixin
from deepfriedmarshmallow.patch import deep_fry_schema, deep_fry_schema_object
from deepfriedmarshmallow.serializer import JitDeserialize, JitSerialize


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


# Attempt to discover and load external plugins on import unless disabled.
try:  # pragma: no cover - import-time side effect
    discover_plugins()
except Exception:
    # Best-effort discovery; failures should not prevent base DFM usage
    pass

# Built-ins are imported by deepfriedmarshmallow.jit.plugins package

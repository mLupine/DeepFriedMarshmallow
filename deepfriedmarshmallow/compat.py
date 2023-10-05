def is_overridden(instance_func, class_func):
    # type: (MethodType, MethodType) -> bool
    return instance_func.__func__ is not class_func


def is_schema_overridden(schema: "marshmallow.Schema") -> bool:
    return hasattr(schema, "_is_jit") and schema._is_jit

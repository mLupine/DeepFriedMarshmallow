from deepfriedmarshmallow.serializer import JitDeserialize, JitSerialize


class JitSchemaMixin:
    jit_serialize_class = JitSerialize
    jit_deserialize_class = JitDeserialize
    _is_jit = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._serialize = self.jit_serialize_class(self)
        self._deserialize = self.jit_deserialize_class(self)

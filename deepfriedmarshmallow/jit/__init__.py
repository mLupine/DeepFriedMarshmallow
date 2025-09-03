import base64
import keyword
import os
import re
from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

import attr
from six import add_metaclass, exec_, iteritems, string_types, text_type

from ..compat import is_overridden
from ..utils import IndentedString
from .plugins import iter_external_inliner_factories, iter_external_inliners

# Regular Expression for identifying a valid Python identifier name.
_VALID_IDENTIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Field-level profiling controls
FIELD_PROFILE_ENABLED = any(
    os.getenv(v, "0").lower() in ("1", "true", "yes", "on") for v in ("DFM_FIELD_PROFILE", "DFM_PROFILE")
)
FIELD_PROFILE_STATS = {}


@dataclass
class MarshmallowCacheStore:
    _Schema = None
    _SchemaABC = None
    _fields = None
    _missing = None

    @property
    def Schema(self) -> "marshmallow.Schema":  # noqa: N802
        self._ensure_imported()
        return self._Schema

    @property
    def SchemaABC(self) -> object:  # noqa: N802
        self._ensure_imported()
        return self._SchemaABC

    @property
    def fields(self) -> "marshmallow.fields":
        self._ensure_imported()
        return self._fields

    @property
    def missing(self) -> "marshmallow.missing":
        self._ensure_imported()
        return self._missing

    def _ensure_imported(self) -> None:
        if self._Schema is None:
            from marshmallow import Schema

            self._Schema = Schema

        if self._SchemaABC is None:
            try:
                # Marshmallow <4
                from marshmallow.base import SchemaABC as _SchemaABC  # type: ignore
            except Exception:
                # Marshmallow >=4 no longer exposes SchemaABC
                from marshmallow import Schema as _SchemaABC
            self._SchemaABC = _SchemaABC

        if self._fields is None:
            from marshmallow import fields

            self._fields = fields

        if self._missing is None:
            try:
                from marshmallow import missing as _missing
            except Exception:  # pragma: no cover - compatibility with Marshmallow 4
                try:
                    from marshmallow.utils import (
                        missing as _missing,  # type: ignore[attr-defined]
                    )
                except Exception:

                    class _MissingSentinel:
                        pass

                    _missing = _MissingSentinel()
            self._missing = _missing


marshmallow = MarshmallowCacheStore()


def field_symbol_name(field_name):
    # type: (str) -> str
    """Generates the symbol name to be used when accessing a field in generated
    code.

    If the field name isn't a valid identifier name, synthesizes a name by
    base64 encoding the fieldname.
    """
    if not _VALID_IDENTIFIER.match(field_name):
        field_name = str(base64.b64encode(field_name.encode("utf-8")).decode("utf-8").strip("="))
    return f"_field_{field_name}"


def attr_str(attr_name):
    # type: (str) -> str
    """Gets the string to use when accessing an attribute on an object.

    Handles case where the attribute name collides with a keyword and would
    therefore be illegal to access with dot notation.
    """
    if keyword.iskeyword(attr_name):
        return f'getattr(obj, "{attr_name}")'
    return f"obj.{attr_name}"


@add_metaclass(ABCMeta)
class FieldSerializer:
    """Base class for generating code to serialize a field."""

    def __init__(self, context=None):
        # type: (JitContext) -> None
        """
        :param context: The context for the current Jit
        """
        self.context = context or JitContext()

    @abstractmethod
    def serialize(self, attr_name, field_symbol, assignment_template, field_obj):
        # type: (str, str, str, marshmallow.fields.Field) -> IndentedString
        """Generates the code to pull a field off of an object into the result.

        :param attr_name: The name of the attribute being accessed/
        :param field_symbol: The symbol to use when accessing the field.  Should
            be generated via field_symbol_name.
        :param assignment_template: A string template to use when generating
            code.  The assignment template is passed into the serializer and
            has a single possitional placeholder for string formatting.  An
            example of a value that may be passed into assignment_template is:
            `res['some_field'] = {0}`
        :param field_obj: The instance of the Marshmallow field being
            serialized.
        :return: The code to pull a field off of the object passed in.
        """
        # pragma: no cover


class InstanceSerializer(FieldSerializer):
    """Generates code for accessing fields as if they were instance variables.

    For example, generates:

    res['some_value'] = obj.some_value
    """

    def serialize(self, attr_name, field_symbol, assignment_template, field_obj):
        # type: (str, str, str, marshmallow.fields.Field) -> IndentedString
        return IndentedString(assignment_template.format(attr_str(attr_name)))


class DictSerializer(FieldSerializer):
    """Generates code for accessing fields as if they were a dict, generating
    the proper code for handing missing fields as well.  For example, generates:

    # Required field with no default
    res['some_value'] = obj['some_value']

    # Field with a default.  some_value__default will be injected at exec time.
    res['some_value'] = obj.get('some_value', some_value__default)

    # Non required field:
    if 'some_value' in obj:
        res['some_value'] = obj['some_value']
    """

    def serialize(self, attr_name, field_symbol, assignment_template, field_obj):
        # type: (str, str, str, marshmallow.fields.Field) -> IndentedString
        body = IndentedString()
        if self.context.is_serializing:
            default_str = "dump_default"
            default_value = field_obj.dump_default
        else:
            default_str = "load_default"
            default_value = field_obj.load_default
            if field_obj.required:
                body += assignment_template.format(f'obj["{attr_name}"]')
                return body
        if default_value == marshmallow.missing:
            body += f'if "{attr_name}" in obj:'
            with body.indent():
                body += assignment_template.format(f'obj["{attr_name}"]')
        else:
            if callable(default_value):
                default_str += "()"

            body += assignment_template.format(
                f'obj.get("{attr_name}", {field_symbol}__{default_str})',
            )
        return body


class HybridSerializer(FieldSerializer):
    """Generates code for accessing fields as if they were a hybrid object.

    Hybrid objects are objects that don't inherit from `Mapping`, but do
    implement `__getitem__`.  This means we first have to attempt a lookup by
    key, then fall back to looking up by instance variable.

    For example, generates:

    try:
        value = obj['some_value']
    except (KeyError, AttributeError, IndexError, TypeError):
        value = obj.some_value
    res['some_value'] = value
    """

    def serialize(self, attr_name, field_symbol, assignment_template, field_obj):
        # type: (str, str, str, marshmallow.fields.Field) -> IndentedString
        body = IndentedString()
        body += "try:"
        with body.indent():
            body += f'value = obj["{attr_name}"]'
        body += "except (KeyError, AttributeError, IndexError, TypeError):"
        with body.indent():
            body += f"value = {attr_str(attr_name)}"
        body += assignment_template.format("value")
        return body


@attr.s
class JitContext:
    """Bag of properties to keep track of the context of what's being jitted."""

    namespace = attr.ib(default={})  # type: dict[str, Any]
    use_inliners = attr.ib(default=True)  # type: bool
    schema_stack = attr.ib(default=attr.Factory(set))  # type: set[str]
    only = attr.ib(default=None)  # type: Optional[set[str]]
    exclude = attr.ib(default=set())  # type: set[str]
    is_serializing = attr.ib(default=True)  # type: bool


@add_metaclass(ABCMeta)
class FieldInliner:
    """Base class for generating code to serialize a field.

    Inliners are used to generate the code to validate/parse fields without
    having to bounce back into the underlying marshmallow code.  While this is
    somewhat fragile as it requires the inliners to be kept in sync with the
    underlying implementation, it's good for a >2X speedup on benchmarks.
    """

    @abstractmethod
    def inline(self, field, context):
        # type: (marshmallow.fields.Field, JitContext) -> Optional[Union[str, tuple]]
        pass  # pragma: no cover


class StringInliner(FieldInliner):
    def inline(self, field, context):
        # type: (marshmallow.fields.Field, JitContext) -> Optional[str]
        """Generates a template for inlining string serialization.

        For example, generates "unicode(value) if value is not None else None"
        to serialize a string in Python 2.7
        """
        if is_overridden(field._serialize, marshmallow.fields.String._serialize):
            return None
        result = text_type.__name__ + "({0})"
        result += " if {0} is not None else None"
        if not context.is_serializing:
            string_type_strings = ",".join([x.__name__ for x in string_types])
            result = (
                "("
                + result
                + ") if (isinstance({0}, ("
                + string_type_strings
                + ')) or {0} is None) else dict()["error"]'
            )
        return result


class UUIDInliner(FieldInliner):
    def inline(self, field, context):
        # type: (marshmallow.fields.Field, JitContext) -> Optional[tuple]

        """Generates a template for inlining UUID serialization."""
        if is_overridden(field._serialize, marshmallow.fields.UUID._serialize):
            return None
        if not context.is_serializing:
            result = "uuid.UUID({0})"
            result += " if {0} is not None and isinstance({0}, str) else "
            result += "({0} if {0} is not None and isinstance({0}, uuid.UUID) else None)"
            result = f"({result})" + " if (isinstance({0}, (uuid.UUID, str)) or {0} is None) else dict()['error']"
        else:
            result = "str({0})"
            result += " if {0} is not None and isinstance({0}, (uuid.UUID, str)) else None"
        return result, "uuid"


class BooleanInliner(FieldInliner):
    def inline(self, field, context):
        # type: (marshmallow.fields.Field, JitContext) -> Optional[str]
        """Generates a template for inlining boolean serialization.

        For example, generates:

        (
            (value in __some_field_truthy) or
            (False if value in __some_field_falsy else bool(value))
        )

        This is somewhat fragile but it tracks what Marshmallow does.
        """
        if is_overridden(field._serialize, marshmallow.fields.Boolean._serialize):
            return None
        truthy_symbol = f"__{field.name}_truthy"
        falsy_symbol = f"__{field.name}_falsy"
        context.namespace[truthy_symbol] = field.truthy
        context.namespace[falsy_symbol] = field.falsy
        result = "(({0} in " + truthy_symbol + ") or (False if {0} in " + falsy_symbol + ' else dict()["error"]))'
        return result + " if {0} is not None else None"


class NumberInliner(FieldInliner):
    def inline(self, field, context):
        # type: (marshmallow.fields.Field, JitContext) -> Optional[str]
        """Generates a template for inlining string serialization.

        For example, generates "float(value) if value is not None else None"
        to serialize a float.  If `field.as_string` is `True` the result will
        be coerced to a string if not None.
        """
        if (
            is_overridden(field._validated, marshmallow.fields.Number._validated)
            or is_overridden(field._serialize, marshmallow.fields.Number._serialize)
            or field.num_type not in (int, float)
        ):
            return None
        result = field.num_type.__name__ + "({0})"
        if field.as_string and context.is_serializing:
            result = f"str({result})"
        if getattr(field, "allow_none", False) is True or context.is_serializing:
            # Only emit the Null checking code if nulls are allowed.  If they
            # aren't allowed casting `None` to an integer will throw and the
            # slow path will take over.
            result += " if {0} is not None else None"
        return result


class NestedInliner(FieldInliner):  # pragma: no cover
    def inline(self, field, context):
        """Generates a template for inlining nested field.

        This doesn't pass tests yet in Marshmallow, namely due to issues around
        code expecting the context of nested schema to be populated on first
        access, so disabling for now.
        """
        if is_overridden(field._serialize, marshmallow.fields.Nested._serialize):
            return None

        if not (isinstance(field.nested, type) and issubclass(field.nested, marshmallow.SchemaABC)):
            return None

        if field.nested.__class__ in context.schema_stack:
            return None

        method_name = f"__nested_{field_symbol_name(field.name)}_serialize"

        old_only = context.only
        old_exclude = context.exclude
        old_namespace = context.namespace

        context.only = set(field.only) if field.only else None
        context.exclude = set(field.exclude)
        context.namespace = {}

        for only_field in old_only or []:
            if only_field.startswith(field.name + "."):
                if not context.only:
                    context.only = set()
                context.only.add(only_field[len(field.name + ".") :])
        for only_field in list(context.only or []):
            if "." in only_field:
                if not context.only:
                    context.only = set()
                context.only.add(only_field.split(".")[0])

        for exclude_field in old_exclude:
            if exclude_field.startswith(field.name + "."):
                context.exclude.add(exclude_field[len(field.name + ".") :])

        serialize_method = generate_serialize_method(field.schema, context)
        if serialize_method is None:
            return None

        context.namespace = old_namespace
        context.only = old_only
        context.exclude = old_exclude

        context.namespace[method_name] = serialize_method

        if field.many:
            return "[" + method_name + "(_x) for _x in {0}] if {0} is not None else None"
        return method_name + "({0}) if {0} is not None else None"


EXPECTED_TYPE_TO_CLASS = {"object": InstanceSerializer, "dict": DictSerializer, "hybrid": HybridSerializer}


def _should_skip_field(field_name, field_obj, context):
    # type: (str, marshmallow.fields.Field, JitContext) -> bool
    load_only = getattr(field_obj, "load_only", False)
    dump_only = getattr(field_obj, "dump_only", False)
    # Marshmallow 2.x.x doesn't properly set load_only or
    # dump_only on Method objects.  This is fixed in 3.0.0
    # https://github.com/marshmallow-code/marshmallow/commit/1b676dd36cbb5cf040da4f5f6d43b0430684325c
    if isinstance(field_obj, marshmallow.fields.Method):
        load_only = bool(field_obj.deserialize_method_name) and not bool(field_obj.serialize_method_name)
        dump_only = bool(field_obj.serialize_method_name) and not bool(field_obj.deserialize_method_name)

    if load_only and context.is_serializing:
        return True
    if dump_only and not context.is_serializing:
        return True
    if context.only and field_name not in context.only:
        return True
    if context.exclude and field_name in context.exclude:
        return True
    return False


def generate_transform_method_body(schema, on_field, context):
    # type: (Schema, FieldSerializer, JitContext) -> IndentedString
    """Generates the method body for a schema and a given field serialization
    strategy.
    """
    required_imports = set()
    if FIELD_PROFILE_ENABLED:
        required_imports.add("time")
    body = IndentedString()
    body += f"def {on_field.__class__.__name__}(obj):"
    with body.indent():
        meta = getattr(schema.__class__, "Meta", None)
        meta_ordered = bool(getattr(meta, "ordered", False)) if meta is not None else False
        if schema.dict_class is dict and not meta_ordered:
            # Declaring dictionaries via `{}` is faster than `dict()` since it
            # avoids the global lookup.
            body += "res = {}"
        else:
            # Use schema-provided dict_class (supports ordered schemas and custom mappings)
            body += "res = dict_class()"
        if not context.is_serializing:
            body += "__res_get = res.get"
        for field_name, field_obj in iteritems(schema.fields):
            if _should_skip_field(field_name, field_obj, context):
                continue

            attr_name, destination = _get_attr_and_destination(context, field_name, field_obj)

            result_key = destination

            field_symbol = field_symbol_name(field_name)
            assignment_template = ""
            value_key = "{0}"

            # If we have to assume any field can be callable we always have to
            # check to see if we need to invoke the method first.
            # We can investigate tracing this as well.
            jit_options = getattr(schema.opts, "jit_options", {})
            no_callable_fields = jit_options.get("no_callable_fields") or not context.is_serializing
            if not no_callable_fields:
                assignment_template = "value = {0}; value = value() if callable(value) else value; "
                value_key = "value"

            # Attempt to see if this field type can be inlined.
            inliner = inliner_for_field(context, field_obj)

            # Optional field-level profiling: start timer
            if FIELD_PROFILE_ENABLED:
                body += "__t0 = time.perf_counter()"

            if inliner and isinstance(inliner, str):
                assignment_template += _generate_inlined_access_template(inliner, result_key, no_callable_fields)
            elif inliner and isinstance(inliner, tuple):
                assignment_template += _generate_inlined_access_template(inliner[0], result_key, no_callable_fields)
                required_imports.update(inliner[1] if isinstance(inliner[1], (list, set, tuple)) else [inliner[1]])

            else:
                assignment_template += _generate_fallback_access_template(
                    context,
                    field_name,
                    field_obj,
                    result_key,
                    value_key,
                )
            if not field_obj._CHECK_ATTRIBUTE:
                # fields like 'Method' expect to have `None` passed in when
                # invoking their _serialize method.
                body += assignment_template.format("None")
                context.namespace["__marshmallow_missing"] = marshmallow.missing
                body += f'if res["{result_key}"] is __marshmallow_missing:'
                with body.indent():
                    body += f'del res["{result_key}"]'

            else:
                serializer = on_field
                if not _VALID_IDENTIFIER.match(attr_name):
                    # If attr_name is not a valid python identifier, it can only
                    # be accessed via key lookups.
                    serializer = DictSerializer(context)

                body += serializer.serialize(attr_name, field_symbol, assignment_template, field_obj)

                if not context.is_serializing and field_obj.data_key:
                    # Marshmallow has a somewhat counter intuitive behavior.
                    # It will first load from the name of the field, then,
                    # should that fail, will load from the field specified in
                    # 'load_from'.
                    #
                    # For example:
                    #
                    # class TestSchema(Schema):
                    #
                    # Works just fine with no errors.
                    #
                    # class TestSchema(Schema):
                    #
                    #
                    # Therefore, we generate code to mimic this behavior in
                    # cases where `load_from` is specified.
                    body += f'if "{result_key}" not in res:'
                    with body.indent():
                        body += serializer.serialize(field_obj.data_key, field_symbol, assignment_template, field_obj)

            # Optional field-level profiling: record elapsed
            if FIELD_PROFILE_ENABLED:
                schema_name = schema.__class__.__name__
                mode = "serialize" if context.is_serializing else "deserialize"
                key_literal = f"{schema_name}|{mode}|{result_key}"
                body += f"__rec = FIELD_PROFILE_STATS.get('{key_literal}')"
                body += "if __rec is None:"
                with body.indent():
                    body += "FIELD_PROFILE_STATS['" + key_literal + "'] = [time.perf_counter() - __t0, 1]"
                body += "else:"
                with body.indent():
                    body += "__rec[0] += (time.perf_counter() - __t0)"
                    body += "__rec[1] += 1"
            if not context.is_serializing:
                if field_obj.required:
                    body += f'if "{result_key}" not in res:'
                    with body.indent():
                        body += "raise ValueError()"
                if getattr(field_obj, "allow_none", False) is not True:
                    body += f'if __res_get("{result_key}", res) is None:'
                    with body.indent():
                        body += "raise ValueError()"
                if field_obj.validators or is_overridden(field_obj._validate, marshmallow.fields.Field._validate):
                    body += f'if "{result_key}" in res:'
                    with body.indent():
                        body += f'{field_symbol}__validate(res["{result_key}"])'

        body += "return res"
    if required_imports:
        body = IndentedString("\n".join([f"import {x}" for x in required_imports]) + "\n" + str(body))
    return body


def _generate_fallback_access_template(context, field_name, field_obj, result_key, value_key):
    field_symbol = field_symbol_name(field_name)
    transform_method_name = "serialize"
    if not context.is_serializing:
        transform_method_name = "deserialize"
    key_name = field_name
    if not context.is_serializing:
        key_name = field_obj.data_key or field_name
    return f'res["{result_key}"] = {field_symbol}__{transform_method_name}({value_key}, "{key_name}", obj)'


def _get_attr_and_destination(context, field_name, field_obj):
    # type: (JitContext, str, marshmallow.fields.Field) -> Tuple[str, str]
    # The name of the attribute to pull off the incoming object
    attr_name = field_name
    # The destination of the field in the result dictionary.
    destination = field_name
    if context.is_serializing:
        destination = field_obj.data_key or field_name
    if field_obj.attribute:
        if context.is_serializing:
            attr_name = field_obj.attribute
        else:
            destination = field_obj.attribute
    return attr_name, destination


def _generate_inlined_access_template(inliner, key, no_callable_fields):
    # type: (str, str, bool) -> str
    """Generates the code to access a field with an inliner."""
    value_key = "value"
    assignment_template = ""
    if not no_callable_fields:
        assignment_template += f"value = {inliner.format(value_key)}; "
    else:
        assignment_template += "value = {0}; "
        value_key = inliner.format("value")
    assignment_template += f'res["{key}"] = {value_key}'
    return assignment_template


def inliner_for_field(context, field_obj):
    # type: (JitContext, marshmallow.fields.Field) -> Optional[str]
    inliners = {
        marshmallow.fields.UUID: UUIDInliner(),
        marshmallow.fields.String: StringInliner(),
        marshmallow.fields.Number: NumberInliner(),
        marshmallow.fields.Boolean: BooleanInliner(),
    }

    # Allow external plugins to contribute additional inliners
    try:  # pragma: no cover
        for ftype, inliner_cls in iter_external_inliners():
            try:
                inliners[ftype] = inliner_cls()
            except Exception:
                continue
    except Exception:
        pass

    if context.use_inliners:
        inliner = None
        for field_type, inliner_class in iteritems(inliners):
            if isinstance(field_obj, field_type):
                inliner = inliner_class.inline(field_obj, context)
                if inliner:
                    break
        if not inliner:
            # Allow factory-based plugins to decide dynamically
            try:  # pragma: no cover
                for factory in iter_external_inliner_factories():
                    inliner = factory(field_obj, context)
                    if inliner:
                        break
            except Exception:
                pass
        return inliner
    return None


def generate_method_bodies(schema, context):
    # type: (Schema, JitContext) -> str
    """Generate 3 method bodies for serializing objects, dictionaries, or hybrid
    objects.
    """
    result = IndentedString()

    result += generate_transform_method_body(schema, InstanceSerializer(context), context)
    result += generate_transform_method_body(schema, DictSerializer(context), context)
    result += generate_transform_method_body(schema, HybridSerializer(context), context)
    return str(result)


class SerializeProxy:
    """Proxy object for calling serializer methods.

    Initially trace calls to serialize and if the number of calls
    of a specific type crosses `threshold` swaps out the implementation being
    used for the most specialized one available.
    """

    def __init__(self, dict_serializer, hybrid_serializer, instance_serializer, threshold=100):
        # type: (Callable, Callable, Callable, int) -> None
        self.dict_serializer = dict_serializer
        self.hybrid_serializer = hybrid_serializer
        self.instance_serializer = instance_serializer
        self.threshold = threshold
        self.dict_count = 0
        self.hybrid_count = 0
        self.instance_count = 0
        self._call = self.tracing_call

        if not threshold:
            self._call = self.no_tracing_call

    def __call__(self, obj):
        return self._call(obj)

    def tracing_call(self, obj):
        # type: (Any) -> Any
        """Dispatcher which traces calls and specializes if possible."""
        try:
            if isinstance(obj, Mapping):
                self.dict_count += 1
                return self.dict_serializer(obj)
            if hasattr(obj, "__getitem__"):
                self.hybrid_count += 1
                return self.hybrid_serializer(obj)
            self.instance_count += 1
            return self.instance_serializer(obj)
        finally:
            non_zeros = [x for x in [self.dict_count, self.hybrid_count, self.instance_count] if x > 0]
            if len(non_zeros) > 1:
                self._call = self.no_tracing_call
            elif self.dict_count >= self.threshold:
                self._call = self.dict_serializer
            elif self.hybrid_count >= self.threshold:
                self._call = self.hybrid_serializer
            elif self.instance_count >= self.threshold:
                self._call = self.instance_serializer

    def no_tracing_call(self, obj):
        # type: (Any) -> Any
        """Dispatcher with no tracing."""
        ret = None
        if isinstance(obj, Mapping):
            ret = self.dict_serializer(obj)
        elif hasattr(obj, "__getitem__"):
            ret = self.hybrid_serializer(obj)
        else:
            ret = self.instance_serializer(obj)
        return ret


def generate_serialize_method(schema, context=None, threshold=100):
    # type: (Schema, JitContext, int) -> Union[SerializeProxy, Callable, None]
    """Generates a function to serialize objects for a given schema.

    :param schema: The Schema to generate a serialize method for.
    :param threshold: The number of calls of the same type to observe before
        specializing the serialize method for that type.
    :return: A Callable that can be used to serialize objects for the schema
    """
    if context is None:
        context = marshmallow.missing

    if is_overridden(schema.get_attribute, marshmallow.Schema.get_attribute):
        # Bail if get_attribute is overridden.  This provides the schema author
        # too much control to reasonably JIT.
        return None

    if context is marshmallow.missing:
        context = JitContext()

    context.namespace = {}
    context.namespace["dict_class"] = lambda: schema.dict_class()  # pylint: disable=unnecessary-lambda

    jit_options = getattr(schema.opts, "jit_options", {})
    # Optional per-schema DFM controls
    dfm_opts = getattr(schema.opts, "dfm", None)
    if isinstance(dfm_opts, dict) and "use_inliners" in dfm_opts:
        context.use_inliners = bool(dfm_opts["use_inliners"])  # type: ignore[assignment]

    context.schema_stack.add(schema.__class__)

    result = generate_method_bodies(schema, context)

    context.schema_stack.remove(schema.__class__)

    namespace = context.namespace
    # Expose profiling stats dict to generated methods if profiling enabled
    if FIELD_PROFILE_ENABLED:
        namespace["FIELD_PROFILE_STATS"] = FIELD_PROFILE_STATS

    for key, value in iteritems(schema.fields):
        if value.attribute and "." in value.attribute:
            # We're currently unable to handle dotted attributes.  These don't
            # seem to be widely used so punting for now.  For more information
            # see
            # https://github.com/marshmallow-code/marshmallow/issues/450
            return None
        namespace[field_symbol_name(key) + "__serialize"] = value._serialize
        namespace[field_symbol_name(key) + "__deserialize"] = value._deserialize
        namespace[field_symbol_name(key) + "__validate_missing"] = value._validate_missing
        namespace[field_symbol_name(key) + "__validate"] = value._validate

        if value.dump_default is not marshmallow.missing:
            namespace[field_symbol_name(key) + "__dump_default"] = value.dump_default

        if value.load_default is not marshmallow.missing:
            namespace[field_symbol_name(key) + "__load_default"] = value.load_default

    exec_(result, namespace)

    proxy = None  # type: Optional[SerializeProxy]
    serialize_method = None  # type: Union[SerializeProxy, Callable, None]
    if not context.is_serializing:
        # Deserialization always expects a dictionary.
        serialize_method = namespace[DictSerializer.__name__]
    elif jit_options.get("expected_serialize_type") in EXPECTED_TYPE_TO_CLASS:
        serialize_method = namespace[EXPECTED_TYPE_TO_CLASS[jit_options["expected_serialize_type"]].__name__]
    else:
        serialize_method = SerializeProxy(
            namespace[DictSerializer.__name__],
            namespace[HybridSerializer.__name__],
            namespace[InstanceSerializer.__name__],
            threshold=threshold,
        )
        proxy = serialize_method

    def serialize(obj, many=False):  # noqa: FBT002
        if many:
            return [serialize_method(x) for x in obj]
        return serialize_method(obj)

    if proxy:
        # Used to allow tests to introspect the proxy.
        serialize.proxy = proxy  # type: ignore
    serialize._source = result  # type: ignore
    return serialize


def generate_deserialize_method(schema, context=None):
    """Generate a deserialization method with input-type guards.

    For JITed deserialization we require a Mapping input when many=False.
    If the input doesn't match, raise to trigger fallback to non-JIT which
    will surface a proper marshmallow ValidationError.
    """
    context = context or JitContext()
    context.is_serializing = False
    deser = generate_serialize_method(schema, context)
    if deser is None:
        return None

    def _guarded_deserialize(obj, many=False):  # noqa: FBT002
        if not many and not isinstance(obj, Mapping):
            raise ValueError("DFM: non-mapping input for deserialization")
        return deser(obj, many=many)

    return _guarded_deserialize

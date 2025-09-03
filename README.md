:fire: Deep-Fried Marshmallow – Makes Marshmallow a Chicken Nugget
==================================================================

I need to be honest with you — I have no idea how to compare the speed of a
marshmallow and the speed of a chicken nugget. I really liked that headline,
though, so let's just assume that a nugget is indeed faster than a
marshmallow. So is this project, Deep-Fried Marshmallow, faster than
vanilla Marshmallow. Or, to be precise, it *makes* Marshmallow faster.

Deep-Fried Marshmallow implements a JIT for Marshmallow that speeds up dumping
objects 3-5x (depending on your schema). Deep-Fried Marshmallow allows you to
have the great API that
[Marshmallow](https://github.com/marshmallow-code/marshmallow) provides
without having to sacrifice performance.
```
    Benchmark Result:
        Original Dump Time: 220.50 usec/dump
        Original Load Time: 536.51 usec/load
        Optimized Dump Time: 58.67 usec/dump
        Optimized Load Time: 118.44 usec/load

        Speed up for dump: 3.76x
        Speed up for load: 4.53x
```

Deep-Fried Marshmallow is a fork of the great
[Toasted Marshmallow](https://github.com/lyft/toasted-marshmallow) project that,
sadly, has been abandoned for years. Deep-Fried Marshmallow introduces many
changes that make it compatible with all latest versions of Marshmallow (3.13+).
It also changes the way the library interacts with Marshmallow, which means
that code of Marshmallow doesn't need to be forked and modified for the JIT
magic to work. That's a whole new level of magic!

## Plugin System

Deep-Fried Marshmallow supports external plugins that can contribute field inliners or custom JIT behaviors without modifying DFM.

- Environment controls:
  - `DFM_DISABLE_AUTO_PLUGINS=1` disables entry-point discovery
  - `DFM_PLUGINS=module:obj,...` registers additional plugins explicitly

A plugin can be either:

- A callable that, when invoked, performs registration via `register_field_inliner(...)` or `register_field_inliner_factory(...)`, or
- A module/object exposing `dfm_register(registry)` which is called with the registry instance.

See `marshmallow_oneofschema.dfm_plugin` in [Kalepa's Marshmallow-FastOneOfSchema](https://github.com/Kalepa/marshmallow-fastoneofschema) fork for a minimal example.

### Per-schema Controls

- Use `class Meta: jit_options = {...}` to configure JIT behavior. In addition, `class Meta: dfm = { 'use_inliners': True|False }` toggles whether field inliners are used for that schema.



## Installing Deep-Fried Marshmallow


```bash
pip install DeepFriedMarshmallow
# or, if your project uses Poetry:
poetry install DeepFriedMarshmallow
```

If your project doesn't have vanilla Marshmallow specified in requirements,
the latest version of it will be installed alongside Deep-Fried Marshmallow.
You are free to pin any version of it that you need, as long as it's
newer than v3.13.


## Enabling Deep-Fried Marshmallow

Enabling Deep-Fried Marshmallow on an existing schema is just one change of code. Change your schemas to inherit from the `JitSchema` class in the `deepfriedmarshmallow` package instead of `Schema` from `marshmallow`.

For example, this block of code:

```python
from marshmallow import Schema, fields

class ArtistSchema(Schema):
    name = fields.Str()

class AlbumSchema(Schema):
    title = fields.Str()
    release_date = fields.Date()
    artist = fields.Nested(ArtistSchema())

schema = AlbumSchema()
```

Should become this:
```python
from marshmallow import fields
from deepfriedmarshmallow import JitSchema

class ArtistSchema(JitSchema):
    name = fields.Str()

class AlbumSchema(JitSchema):
    title = fields.Str()
    release_date = fields.Date()
    artist = fields.Nested(ArtistSchema())

schema = AlbumSchema()
```

And that's it!

### Auto-patching all Marshmallow schemas

If you want to automatically patch all Marshmallow schemas in your project,
Deep-Fried Marshmallow provides a helper function for that. Just call
`deepfriedmarshmallow.deep_fry_marshmallow()` before you start using
Marshmallow schemas, and you're all set. The upmost ``__init__.py`` file of
your project is a good place to do that.

```python
# your_package/__init__.py
from deepfriedmarshmallow import deep_fry_marshmallow

deep_fry_marshmallow()
```

All imports of `marshmallow.Schema` will be automatically replaced with
`deepfriedmarshmallow.Schema` with no other changes to your code. Isn't that
~~sweet~~ extra crispy?

### Custom Schema classes

Deep-Fried Marshmallow also provides a mixin class that you can use to create
or extend custom Schema classes. To use it, just inherit from `JitSchemaMixin`.
Let's take a look at the following example:

```python
from marshmallow import fields

class ClockSchema(MyAwesomeBaseSchema):
    time = fields.DateTime(data_key="Time")
```

If you want to make this schema JIT-compatible, and don't want to modify the
`MyAwesomeBaseSchema` class to inherit from `deepfriedmarshmallow.Schema`,
you can do the following:

```python
from marshmallow import fields
from deepfriedmarshmallow import JitSchemaMixin

class ClockSchema(JitSchemaMixin, MyAwesomeBaseSchema):
    time = fields.DateTime(data_key="Time")
```

### Patcher functions

If all of the above wasn't enough, Deep-Fried Marshmallow also provides two
more ways to patch Marshmallow schemas. Both of them are functions that you
can call to patch either a Schema class, or a Schema instance. Let's take a
look at the following example:

```python
from marshmallow import Schema, fields
from deepfriedmarshmallow import deep_fry_schema

class ArtistSchema(Schema):
    name = fields.Str()

deep_fry_schema(ArtistSchema)
schema = ArtistSchema()
```

The `deep_fry_schema` function will patch the `AlbumSchema` class, and all
instances of it will be JIT-compatible. If you want to patch a specific
instance of a schema, you can use the `deep_fry_schema_object` function:

```python
from marshmallow import Schema, fields
from deepfriedmarshmallow import deep_fry_schema_object

class ArtistSchema(Schema):
    name = fields.Str()

schema = ArtistSchema()
deep_fry_schema_object(schema)
```

This function will patch the `schema` object, and all dumps and loads will
be JIT-compatible. This function is useful if you want to patch a schema
that you don't have control over, for example, a schema that is provided
by a third-party library.

## How it works

Deep-Fried Marshmallow works by generating code at runtime to optimize dumping
objects without going through layers and layers of reflection. The generated
code optimistically assumes the objects being passed in are schematically valid,
falling back to the original Marshmallow code on failure.

For example, taking `AlbumSchema` from above, Deep-Fried Marshmallow will
generate the following methods:

```python
def InstanceSerializer(obj):
    res = {}
    value = obj.title; value = value() if callable(value) else value; value = str(value) if value is not None else None; res["title"] = value
    value = obj.release_date; value = value() if callable(value) else value; res["release_date"] = _field_release_date__serialize(value, "release_date", obj)
    value = obj.artist; value = value() if callable(value) else value; res["artist"] = _field_artist__serialize(value, "artist", obj)
    return res

def DictSerializer(obj):
    res = {}
    if "title" in obj:
        value = obj["title"]; value = value() if callable(value) else value; value = str(value) if value is not None else None; res["title"] = value
    if "release_date" in obj:
        value = obj["release_date"]; value = value() if callable(value) else value; res["release_date"] = _field_release_date__serialize(value, "release_date", obj)
    if "artist" in obj:
        value = obj["artist"]; value = value() if callable(value) else value; res["artist"] = _field_artist__serialize(value, "artist", obj)
    return res

def HybridSerializer(obj):
    res = {}
    try:
        value = obj["title"]
    except (KeyError, AttributeError, IndexError, TypeError):
        value = obj.title
    value = value; value = value() if callable(value) else value; value = str(value) if value is not None else None; res["title"] = value
    try:
        value = obj["release_date"]
    except (KeyError, AttributeError, IndexError, TypeError):
        value = obj.release_date
    value = value; value = value() if callable(value) else value; res["release_date"] = _field_release_date__serialize(value, "release_date", obj)
    try:
        value = obj["artist"]
    except (KeyError, AttributeError, IndexError, TypeError):
        value = obj.artist
    value = value; value = value() if callable(value) else value; res["artist"] = _field_artist__serialize(value, "artist", obj)
    return res
```

Deep-Fried Marshmallow will invoke the proper serializer based upon the input.

Since Deep-Fried Marshmallow generates code at runtime, it's critical you
re-use Schema objects. If you're creating a new Schema object every time you
serialize or deserialize an object, you're likely to experience much worse
performance.

## Special thanks to
 * [@rowillia](https://github.com/rowillia)/[@lyft](https://github.com/lyft) — for creating Toasted Marshmallow
 * [@taion](https://github.com/taion) — for a [PoC](https://github.com/lyft/toasted-marshmallow/pull/16) of injecting the JIT compiler by replacing the marshaller
 * [@Kalepa](https://github.com/Kalepa) — for needing improved Marshmallow performance so that I could actually work on this project 😅

## License
See [LICENSE](/LICENSE) for details.

## Contributing

Contributions, issues and feature requests are welcome!

Feel free to check [existing issues](https://github.com/mLupine/DeepFriedMarshmallow/issues) before reporting a new one.

## Show your support
Give this repository a ⭐️ if this project helped you!

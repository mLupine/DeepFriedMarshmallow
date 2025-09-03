# Changelog

## 1.1.2 (2025-09-03)

### Fixed
- Deserialization: Properly handle `unknown=RAISE` in `JitDeserialize`

## 1.1.1 (2025-09-03)

### Fixed
- Inliners: Prefer `UUIDInliner` over `StringInliner` in `List`, `Tuple`, and `Dict` plugins. This preserves UUID objects during deserialization instead of coercing them to strings.
- Deserialization: Guard non-mapping inputs when `many=False` and fall back to Marshmallow for proper `ValidationError` messages.


## 1.1.0 (2025-09-03)

### Added
- Plugin system: Support external inliners and factories via entry points and `DFM_PLUGINS` env.
- Built-in inliners for `Dict`, `Tuple`, `List`, `Raw`, `Decimal`, `Constant`, `EnumField` (when available), and datetime types (`Date`, `DateTime`, `Time`).
  - `Decimal` inliner only runs on a safe subset:
    - Deserialization: `decimal.Decimal(str(x))` when no `places`/`rounding`/`allow_nan` constraints are set.
    - Serialization: `as_string=True` supported; otherwise falls back to non-JIT behavior.
  - `Constant` inliner inlines only on serialization; deserialization goes through Marshmallow for correctness.
  - `datetime` inliners return plain expressions when no imports are needed.
- Per-schema control: `class Meta: dfm = { 'use_inliners': True|False }` to enable/disable inliners.
- Optional profiling: `DFM_PROFILE` / `DFM_FIELD_PROFILE` to gather hot spots.

### Changed
- Dropped support for Python 3.8–3.10; minimum supported version is now 3.11.

### Fixed
- Logging in patcher uses a correct `__name__` field.

### Tests
- Added coverage for built-in inliners.
- Added tests for plugin discovery, manual registration, and precedence rules.
- Added tests to verify that `Meta.dfm.use_inliners=False` disables built-ins while preserving behavior.

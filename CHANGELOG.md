# Changelog

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

### Fixed
- Logging in patcher uses a correct `__name__` field.

### Tests
- Added coverage for built-in inliners.
- Added tests for plugin discovery, manual registration, and precedence rules.
- Added tests to verify that `Meta.dfm.use_inliners=False` disables built-ins while preserving behavior.

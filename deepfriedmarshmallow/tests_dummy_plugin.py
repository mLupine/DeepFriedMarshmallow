from __future__ import annotations


def dfm_register(registry) -> None:  # pragma: no cover
    def factory(_field_obj, _context) -> str | None:
        return None

    registry.register_field_inliner_factory(factory)

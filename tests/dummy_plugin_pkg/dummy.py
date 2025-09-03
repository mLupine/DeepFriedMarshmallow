from __future__ import annotations

from typing import Optional


def dfm_register(registry) -> None:
    def factory(field_obj, context) -> Optional[str]:  # pragma: no cover - exercised via discovery
        return None

    registry.register_field_inliner_factory(factory)


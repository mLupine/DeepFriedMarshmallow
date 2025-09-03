import importlib
import os

from deepfriedmarshmallow.jit import plugins as dfm_plugins


def test_env_discovery_registers_factory(monkeypatch):
    before = len(list(dfm_plugins.iter_external_inliner_factories()))
    monkeypatch.setenv("DFM_DISABLE_AUTO_PLUGINS", "1")
    monkeypatch.setenv("DFM_PLUGINS", "deepfriedmarshmallow.tests_dummy_plugin")
    dfm_plugins.discover_plugins()
    after = len(list(dfm_plugins.iter_external_inliner_factories()))
    assert after > before


def test_auto_discovery_registers_factory(monkeypatch):
    before = len(list(dfm_plugins.iter_external_inliner_factories()))

    class Ep:
        def load(self):
            import deepfriedmarshmallow.tests_dummy_plugin as mod
            return mod

    class Eps:
        def select(self, group):  # emulate 3.11 API
            if group == "deepfriedmarshmallow.plugins":
                return [Ep()]
            return []

    monkeypatch.delenv("DFM_DISABLE_AUTO_PLUGINS", raising=False)
    monkeypatch.delenv("DFM_PLUGINS", raising=False)
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setattr(dfm_plugins, "entry_points", lambda: Eps(), raising=True)

    dfm_plugins.discover_plugins()
    after = len(list(dfm_plugins.iter_external_inliner_factories()))
    assert after > before


def test_manual_dfm_register():
    before = len(list(dfm_plugins.iter_external_inliner_factories()))
    from deepfriedmarshmallow.tests_dummy_plugin import dfm_register

    # Access registry in tests to simulate manual registration
    dfm_register(dfm_plugins._registry)  # type: ignore[attr-defined]
    after = len(list(dfm_plugins.iter_external_inliner_factories()))
    assert after > before

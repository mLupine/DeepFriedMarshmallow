import importlib
import sys
import types

from deepfriedmarshmallow.log import logger


class MarshmallowImportReplacer:
    def __init__(self):
        logger.debug("Marshmallow import hook created")
        # A flag to prevent recursive importing
        self.is_importing = False

    def find_spec(self, name, path, target=None):
        if name == "marshmallow" and not self.is_importing:
            return importlib.util.spec_from_loader(name, loader=self, origin=path)  # Use self here
        return None

    def create_module(self, spec):
        logger.debug("Marshmallow module created")
        # Set flag to avoid recursive importing
        self.is_importing = True

        # Import original marshmallow and create a new module
        original_marshmallow = importlib.import_module("marshmallow")

        # Manually create a new module instead of using importlib.util.module_from_spec
        new_module = types.ModuleType(spec.name)
        new_module.__dict__.update(original_marshmallow.__dict__)

        # Release flag as import is done
        self.is_importing = False

        # Patch marshmallow module
        return self.patch_marshmallow_module(new_module)

    def exec_module(self, module):
        # No action needed here, as all actions are performed in create_module
        pass

    @staticmethod
    def patch_marshmallow_module(module):
        if hasattr(module, "Schema") and hasattr(module.Schema, "_is_jit") and module.Schema._is_jit:
            # Marshmallow has already been patched, return the module as-is
            return module

        from deepfriedmarshmallow import JitSchema

        module.Schema = JitSchema
        module.__doc__ = "Marshmallow module enhanced with Deep-Fried Marshmallow (Schema class replacement)"
        return module


def deep_fry_marshmallow():
    if "marshmallow" in sys.modules:
        # Marshmallow has already been imported, update the existing module
        logger.info("Marshmallow has already been imported, updating the existing module")
        sys.modules["marshmallow"] = MarshmallowImportReplacer.patch_marshmallow_module(sys.modules["marshmallow"])
    else:
        # Marshmallow has not been imported yet, insert the import hook
        logger.info("Marshmallow has not been imported yet, inserting the import hook")
        sys.meta_path.insert(0, MarshmallowImportReplacer())

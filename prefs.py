import importlib

import bpy

from .catalog.abstract_catalog_generaror import AbstractCatalogGenerator
from .configuration.abstract_configuration_provider import \
    AbstractConfigurationProvider

BUILTIN_GENERATORS = [
    "kitsu",
]

BUILTIN_TAG_PROVIDERS = [
    "rrg",
]

def _get_available_catalog_generators_enum(self, context):
    avaiable_generators = [
        ("DISABLED", "Disabled", "Dont generate catalog path"),
    ]

    for generator in BUILTIN_GENERATORS:
        try:
            importlib.import_module(f'.catalog.{generator}_catalog_generaror', __package__)
        except ImportError as e:
            continue
        else:
            avaiable_generators.insert(0, (generator.upper(), generator.capitalize(), f"Use information from {generator}"))
    return avaiable_generators


def _get_default_catalog_generator():
    generator_name = _get_available_catalog_generators_enum(None, None)[0][0].lower()
    if generator_name == "disabled":
        return None
    else:
        return getattr(importlib.import_module(f'.catalog.{generator_name}_catalog_generaror', __package__), f'{generator_name.capitalize()}CatalogGenerator')()

def _update_catalog_generator(self, context):
    generator_name = self.catalog_path_generator_method.lower()
    if generator_name == "disabled":
        self.catalog_generator = None
        return
    else:
        self.catalog_generator = getattr(importlib.import_module(f'.catalog.{generator_name}_catalog_generaror', __package__), f'{generator_name.capitalize()}CatalogGenerator')()
    

def _get_available_configuration_provider_enum(self, context):
    avaiable_providers = [
        ("DISABLED", "Disabled", "Dont provide extra configuration"),
    ]

    for config_provider in BUILTIN_TAG_PROVIDERS:
        try:
            importlib.import_module(f'.configuration.{config_provider}_configuration_provider', __package__)
        except ImportError as e:
            continue
        else:
            avaiable_providers.insert(0, (config_provider.upper(), config_provider.capitalize(), f"Use information from {config_provider}"))
    return avaiable_providers


def _get_default_configuration_provider():
    provider_name = _get_available_configuration_provider_enum(None, None)[0][0].lower()
    if provider_name == "disabled":
        return None
    else:
        return getattr(importlib.import_module(f'.configuration.{provider_name}_configuration_provider', __package__), f'{provider_name.capitalize()}ConfigurationProvider')()

def _update_config_provider(self, context):
    generator_name = self.configuration_provider_name.lower()
    if generator_name == "disabled":
        self.catalog_generator = None
        return
    else:
        self.catalog_generator = getattr(importlib.import_module(f'.configuration.{generator_name}_catalog_generaror', __package__), f'{generator_name.capitalize()}ConfigurationProvider')()
    


class AnimationLibraryPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    catalog_path_generator_method: bpy.props.EnumProperty(
        name="Method",
        items=_get_available_catalog_generators_enum,
        update=_update_catalog_generator,
    ) # type: ignore
    catalog_generator: AbstractCatalogGenerator = _get_default_catalog_generator()
    configuration_provider_name: bpy.props.EnumProperty(
        name="Configuration provider",
        items=_get_available_configuration_provider_enum,
        update=_update_config_provider,
    ) # type: ignore
    configuration_provider: AbstractConfigurationProvider = _get_default_configuration_provider()


    def draw(self, context):
        layout = self.layout
        layout.row().prop(self, "catalog_path_generator_method", text="Automatic catalog creation")
        layout.row().prop(self, "configuration_provider_name", text="Configuration provider")


def get_preferences():
    return bpy.context.preferences.addons[__package__].preferences


CLASSES = [
    AnimationLibraryPreferences
]


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
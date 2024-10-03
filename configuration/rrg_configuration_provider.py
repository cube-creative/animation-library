from .abstract_configuration_provider import AbstractConfigurationProvider

from blender3.modules.shot import shot_info_getter
import ronaldreglages.api

class RrgConfigurationProvider(AbstractConfigurationProvider):
    def get_default_tags(self):
        shot_info = shot_info_getter.get_shot_scene_info()
        config =  ronaldreglages.api.get_config(
            project= shot_info["project_name"],
            section='animation_library'
        )
        return config.get('default_tags')
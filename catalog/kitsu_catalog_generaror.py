import gazu
import ronaldreglages
from shot import shot_info_getter


def _connect_to_kitsu(project_name):
    credentials = ronaldreglages.api.get_config(project_name, section='kitsu', config_name="project_config")
    if credentials is None:
        raise ValueError(f"Can't found Zou credentials for '{project_name}'.")
    host = credentials.get("host")
    pseudo = credentials.get('user')
    password = credentials.get('pwd')
    try:
        client = gazu.client.set_host(host)
        gazu.log_in(pseudo, password)
    except gazu.exception.RouteNotFoundException:
        raise ConnectionError(f"The URL {host} is not a valid Zou instance API.")
    except gazu.exception.AuthFailedException:
        raise ConnectionError(f"Invalid credentials for target {host}.")
    return client


class KitsuCatalogGenerator():
    def generate_entry_path(self)->str:
        """ Generate a path for a new entry
        """
        shot_info = shot_info_getter.get_shot_scene_info()
        project_name = shot_info["project_name"]
        episode_name = shot_info["episode_name"]
        sequence_name = shot_info["sequence_name"]
        shot_name = shot_info["shot_name"]

        _connect_to_kitsu(project_name=shot_info["project_name"])

        # Retrieve production tracker information
        project = gazu.project.get_project_by_name(project_name)
        episode = gazu.shot.get_episode_by_name(project, episode_name)
        sequence = gazu.shot.get_sequence_by_name(project, sequence_name, episode) 
        shot = gazu.shot.get_shot_by_name(sequence, shot_name)

        sequence_description = ''

        # Try to get first the description from the shot_data
        # TODO: Ask the production to stop using the shot description in the shot_data
        shot_data = shot.get('data')
        if shot_data is not None and 'description' in shot_data:
            shot_description = shot_data.get('description')
        elif shot['description'] != '': 
            shot_description = shot.get('description', '')
        else:
            shot_description = shot_name

        sequence_description = sequence.get('description', '')
        if sequence_description == '':
            sequence_description = sequence_name

        return f"{sequence_description}/{shot_description}"
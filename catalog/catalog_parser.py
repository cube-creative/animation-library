import os


BLENDER_ASSET_CATALOGS_FILE_NAME = "blender_assets.cats.txt"

def _parse_catalog_file(file_path: str) -> list:
    catalogs = []
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()  # Remove leading/trailing whitespace
            # Ignore empty lines and comments
            if not line or line.startswith('#'):
                continue
            if line.startswith('VERSION'):
                continue
            # Extract catalog data
            uuid, path, simple_name = line.split(':')
            catalogs.append({
                'uuid': uuid,
                'path': path,
                'simple_name': simple_name,
            })
    return catalogs


def parse_library_catalogs(library_path: str):
    """ Parse the library catalogs file

    Args:
        library_path (str): Library path to parse the catalogs file from
    
    Returns:
        list[dict]: A list of dictionaries containing the catalog entries {'uuid': ... , 'path': ... , 'simple_name': ...}
    
    """
    catalog_file_path = library_path + "\\" + BLENDER_ASSET_CATALOGS_FILE_NAME
    catalogs = _parse_catalog_file(catalog_file_path)
    return catalogs


def get_path_from_uuid(library_path: str, uuid: str):
    """ Get the path from a given uuid

    Args:
        library_path (str): Library path to parse the catalogs file from
        uuid (str): The uuid to search for
    
    Returns:
        str: The path associated with the given uuid
    
    """
    catalogs = parse_library_catalogs(library_path)
    for catalog in catalogs:
        if catalog['uuid'] == uuid:
            return catalog['path']
    return None

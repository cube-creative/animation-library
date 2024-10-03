import os
from uuid import NAMESPACE_URL, uuid4

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

def add_entry(catalog_path, catalog_file_path):
    simple_name = catalog_path.replace("/","-")
    # Get the path to the catalog file
    catalog_file_path = catalog_file_path+"\\"+BLENDER_ASSET_CATALOGS_FILE_NAME

    # Parse the catalog file
    catalogs = _parse_catalog_file(catalog_file_path)

    # check if the catalog already exists
    for catalog in catalogs:
        if catalog_path == catalog["path"]:
            catalog_uuid = catalog["uuid"]
            return catalog_uuid
        
    # Create a new catalog entry
    uuid = str(uuid4())

    # Check if the catalog file exists
    if not os.path.exists(catalog_file_path):
        os.makedirs(os.path.dirname(catalog_file_path), exist_ok=True)

    # Write the updated catalog file
    with open(catalog_file_path, 'w') as file:
        file.write(f'VERSION 1\n')
        for catalog in catalogs:
            file.write(f'{catalog["uuid"]}:{catalog["path"]}:{catalog["simple_name"]}\n')     
        file.write(f'{uuid}:{catalog_path}:{simple_name}\n')

    return uuid

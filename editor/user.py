import bpy
from copy import copy
import getpass
import json
import os

FILE_NAME = "users_rights.json"

def _get_users_rights_file():
    added_libaries = [library.name for library in bpy.context.preferences.filepaths.asset_libraries]
    asset_library_ref = bpy.context.area.spaces.active.params.asset_library_ref
    if asset_library_ref not in added_libaries: 
        return ""
    library_path = copy(bpy.context.preferences.filepaths.asset_libraries.get(asset_library_ref).path).replace('\\', '/')
    return f"{library_path}/{FILE_NAME}"

def _load_rights_config():
    users_rights_file = _get_users_rights_file()
    if not os.path.exists(users_rights_file):
        return {}
    with open(users_rights_file, 'r') as file:
        data = json.load(file)
        return data

def _get_config_field (key: str) -> list:
    data = _load_rights_config().get(key)
    if not data:
        return []
    else:
        return data

def _get_super_usernames() -> list:
    return _get_config_field('super_users')
    
def _get_creators() -> list:
    return _get_config_field('creators')

def is_super_user() -> bool:
    return getpass.getuser().lower() in _get_super_usernames()

def author_is_current_user(author: str) -> bool:
    return author.lower() == getpass.getuser().lower()

def is_creator() -> bool:
    return getpass.getuser().lower() in _get_creators()

def can_edit(author: str) -> bool:
    return (is_super_user() or author_is_current_user(author)) or not rights_file_exists()

def can_create() -> bool:
    return (is_super_user() or is_creator()) or not rights_file_exists()

def rights_file_exists() -> bool:
    users_rights_file = _get_users_rights_file()
    if not os.path.exists(users_rights_file):
        return False
    return True
    
def rights_file_not_found_warning():
    added_libaries = [library.name for library in bpy.context.preferences.filepaths.asset_libraries]
    asset_library_ref = bpy.context.area.spaces.active.params.asset_library_ref
    if asset_library_ref not in added_libaries: 
        return f"{asset_library_ref} selected (please selected a bank)"
    return f"Rights file not found: {_get_users_rights_file()}"
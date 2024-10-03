from enum import Enum
import bpy

class SelectMode(Enum):
    NONE = 'NONE'
    SINGLE = 'SINGLE'
    MULTI = 'MULTI'

def asset_selection_type():
    try:
        selected_asset_files = bpy.context.selected_asset_files
    except:
        return SelectMode.NONE
    if selected_asset_files  is None:
        return SelectMode.NONE
    elif len(selected_asset_files ) == 1:
        return SelectMode.SINGLE
    elif len(selected_asset_files ) > 1:
        return SelectMode.MULTI
    
def object_selection_type():
    selected_objects = bpy.context.selected_objects
    if selected_objects is None:
        return SelectMode.NONE
    elif len(selected_objects) == 1:
        return SelectMode.SINGLE
    elif len(selected_objects) > 1:
        return SelectMode.MULTI
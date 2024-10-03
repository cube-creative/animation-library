from enum import Enum
import bpy

class AssetType(Enum):
    POSE = "POSE"
    ANIMATION = "ANIMATION"
    UNKNOWN = "UNKNOWN"

def get_asset_type(asset_file_handle: bpy.types.FileSelectEntry)-> AssetType:
    if asset_file_handle is None or not hasattr(asset_file_handle, "asset_data"):
        return AssetType.UNKNOWN

    if 'POSE' in asset_file_handle.asset_data.tags:
        return AssetType.POSE
    elif 'ANIMATION' in asset_file_handle.asset_data.tags:
        return AssetType.ANIMATION
    return AssetType.UNKNOWN

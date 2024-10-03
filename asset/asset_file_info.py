import bpy
import os

from datetime import datetime

def get_asset_path(context, asset) -> str:
    asset_path = bpy.types.AssetHandle.get_full_library_path(asset_file_handle=asset)
    return asset_path.replace('\\', '/')

def get_created_date(context, asset) -> str:
    asset_path = get_asset_path(context, asset)
    creation_time =  os.path.getctime(asset_path)
    readable_date = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
    return readable_date
import bpy
import logging

def get_selected_assets():
    selection = dict()
    for asset in bpy.context.selected_asset_files:
        if not asset.asset_data.get("armature"):
            logging.warning(f"Asset {asset.name} will not be applied, no armature field")
            continue
        if selection.get(asset.asset_data["armature"]):
            logging.warning(f"Asset {asset.name} not added to selection, already an asset for armature name : {asset.asset_data['armature']}")
            continue 
        selection[asset.asset_data["armature"]] = asset
    return selection
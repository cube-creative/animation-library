import bpy

from ..preview.thumbnail import get_asset_thumbnail

BLENDER_ASSET_CATALOGS_FILE_NAME = "blender_assets.cats.txt"


def push_asset(asset: bpy.types.Object, asset_file_path: str) -> None:
    """
    Pushes the given asset and related images to a specified asset file path.

    Args:
        asset (bpy.types.Object): The asset to be pushed.
        asset_file_path (str): The file path where the asset will be pushed.
    Returns:
        None
    """
    assets_to_push = set()
    assets_to_push.add(asset)
    try:
        thumbnail = get_asset_thumbnail(asset.name, asset_path=None)
    except FileNotFoundError:
        thumbnail = None
    if thumbnail:
        assets_to_push.add(thumbnail.image)
    bpy.data.libraries.write(asset_file_path, assets_to_push, compress=True)



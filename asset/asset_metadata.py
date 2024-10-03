from dataclasses import dataclass
from typing import List


@dataclass
class AssetMetadata:
    catalog_id: str
    tags: List[str]
    description: str
    armature: str
    author: str


def update_asset_metadata(asset_metadata, new_asset):
    new_asset.asset_data.catalog_id = asset_metadata.catalog_id
    # Add tags
    for tag in asset_metadata.tags:
        new_asset.asset_data.tags.new(
            tag.name,
            skip_if_exists=True
        )
    # Assign description
    new_asset.asset_data.description = asset_metadata.description
    # Assign armature
    new_asset.asset_data["armature"] = asset_metadata.armature
    # Assign author
    new_asset.asset_data.author = asset_metadata.author
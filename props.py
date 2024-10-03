import bpy
from bpy.app.handlers import persistent

from .catalog.catalog_parser import parse_library_catalogs
from .prefs import get_preferences


def get_asset_enum_tags(self, context, edit_text):
    prefs = get_preferences()
    if prefs.configuration_provider:
        tags = prefs.configuration_provider.get_default_tags()
    else:
        tags = []
    tags.append(edit_text)
    return tags
    
# group collection property
class AssetPredefinedTags(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name",
        default="Tag"
    ) # type: ignore


def _stamp_asset_type_as_tag(self, context):
    if self.export_type == "POSE":
        indice_to_remove = self.tags.find("ANIMATION")
    else:
        indice_to_remove = self.tags.find("POSE")

    if indice_to_remove != -1:
        self.tags.remove(indice_to_remove)
    
    if self.tags.find(self.export_type) == -1:
        tag = self.tags.add()
        tag.name = self.export_type
    return None


def _get_catalogs_paths(self, context, edit_text):
    asset_library_ref = context.area.spaces.active.params.asset_library_ref
    library_path = context.preferences.filepaths.asset_libraries.get(asset_library_ref).path
    catalogs_path =  [ catalog['path'] for catalog in parse_library_catalogs(library_path)]
    catalogs_path.append(edit_text)
    return catalogs_path


class NewAssetMetadata(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name",
        default="Asset Name"
    ) # type: ignore
    tags: bpy.props.CollectionProperty(
        type=AssetPredefinedTags
    ) # type: ignore
    active_tag_index: bpy.props.IntProperty() # type: ignore
    export_type: bpy.props.EnumProperty(
        name="Export mode",
        items=[
            ("POSE", "POSE", "Export pose asset"),
            ("ANIMATION", "ANIMATION", "Export animation asset"),
        ],
        update=_stamp_asset_type_as_tag
    ) # type: ignore
    export_selection: bpy.props.EnumProperty(
        name="Export mode",
        items=[
            ("SELECTION", "Selected Controllers", "Export selected bones"),
            ("ALL", "All Controllers", "Export all asset's bones"),
        ],
    ) # type: ignore
    range_start: bpy.props.IntProperty(
        default=-1,
        name="Start"
    ) # type: ignore
    range_end: bpy.props.IntProperty(
        default=-1,
        name="End"
    ) # type: ignore
    generate_preview: bpy.props.BoolProperty(
        name="Generate preview",
        default=True
    ) # type: ignore


class EditedAssetMetadata(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name",
        default=""
    ) # type: ignore
    catalog: bpy.props.StringProperty(
        name="Catalog",
        default="",
        search=_get_catalogs_paths,
    ) # type: ignore
    tags: bpy.props.CollectionProperty(
            type=AssetPredefinedTags
        ) # type: ignore
    active_tag_index: bpy.props.IntProperty() # type: ignore


class AnimationPreview(bpy.types.PropertyGroup):
    preview_buffer: bpy.props.StringProperty(
        name="Animation preview",
        subtype='BYTE_STRING',
    ) # type: ignore
    preview_buffer_size: bpy.props.IntProperty(
        name="Animation preview buffer size",
        default=0
    ) # type: ignore
    frames_total: bpy.props.IntProperty(
        name="Total frames number in preview",
        default=0
    ) # type: ignore
    frames_rows: bpy.props.IntProperty(
        name="Rows",
        default=0
    ) # type: ignore
    frame_size: bpy.props.IntProperty(
        name="Frame pixel size",
        default=128
    ) # type: ignore


@persistent
def initialize_asset_metadata(scene):
    context = bpy.context
    wm = context.window_manager
    # Set default tags
    wm.new_asset_metadata.tags.clear()
    _stamp_asset_type_as_tag(wm.new_asset_metadata, context)

    # Set export range
    wm.new_asset_metadata.range_start = context.scene.frame_start
    wm.new_asset_metadata.range_end = context.scene.frame_end

CLASSES = (
    AssetPredefinedTags,
    NewAssetMetadata,
    EditedAssetMetadata,
    AnimationPreview
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    
    bpy.types.WindowManager.asset_tags = bpy.props.StringProperty(
        name="Asset tag",
        search=get_asset_enum_tags,
        search_options={'SORT'},
    )
    bpy.types.WindowManager.new_asset_metadata = bpy.props.PointerProperty(type=NewAssetMetadata)
    bpy.types.WindowManager.edited_asset_metadata = bpy.props.PointerProperty(type=EditedAssetMetadata)
    bpy.app.handlers.load_post.append(initialize_asset_metadata)
    bpy.types.Action.animation_preview = bpy.props.PointerProperty(
        type=AnimationPreview,
        name="Animation Preview",
        description="Asset animation preview",
        options={'HIDDEN'},
    ) # type: ignore

def unregister():
    del bpy.types.WindowManager.asset_tags
    del bpy.types.WindowManager.new_asset_metadata
    del bpy.types.WindowManager.edited_asset_metadata
    del bpy.types.Action.animation_preview
    for cls in CLASSES:
        bpy.utils.unregister_class(cls)
    
    bpy.app.handlers.load_post.remove(initialize_asset_metadata)
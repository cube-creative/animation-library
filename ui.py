import bl_app_override
import bpy
from bl_app_override.helpers import AppOverrideState
from bpy_extras import asset_utils

from .asset.asset_file_info import get_created_date
from .asset.asset_type import AssetType, get_asset_type
from .ops import (ASSETLIB_OP_AddAssetPredefinedTag, ASSETLIB_OP_ApplyAsset,
                  ASSETLIB_OP_CreateAsset, ASSETLIB_OP_EditActiveAssetMetadata,
                  ASSETLIB_OP_RemoveAssetTag, display_apply_warning,
                  display_no_rights_file_warning)
from .preview.player import ASSET_AnimationPreviewPlayer


episodic_path = ""
official_path = ""
user_path = ""


def get_library_paths(self,context):
    libraries = []
    prefs = bpy.context.preferences
    filepaths = prefs.filepaths
    asset_libraries = filepaths.asset_libraries
    for asset_library in asset_libraries:
        library_name = asset_library.name
        library_path = asset_library.path
        libraries.append((library_path, library_name, ""))
    return libraries


class ASSET_UL_tags(bpy.types.UIList):
    """ Tags list display for quick asset creation panel
    """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item:
                layout.label(text=item.name)
            else:
                layout.label(text="", translate=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.label(text=item.name)

class ArmatureNameProperties(bpy.types.PropertyGroup):
    armature_name: bpy.props.StringProperty(
        name="Armature",
        description="Name of the armature",
        default=""
    ) # type: ignore

class CreatedTimeProperties(bpy.types.PropertyGroup):
    created_time: bpy.props.StringProperty(
        name="Created Time",
        description="Time of creation",
        default=""
    ) # type: ignore

class ASSETBROWSER_PT_infos(asset_utils.AssetBrowserPanel, bpy.types.Panel):
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Asset Metadata"
    bl_options = {'HIDE_HEADER'}

    @staticmethod
    def metadata_prop(layout, asset_data, propname):
        """
        Only display properties that are either set or can be modified (i.e. the
        asset is in the current file). Empty, non-editable fields are not really useful.
        """
        if getattr(asset_data, propname):
            layout.prop(asset_data, propname)

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager
        asset_file_handle = context.asset_file_handle
        preview_player_registered = hasattr(context.window_manager, "animation_preview_widget")

        is_animation_asset = asset_file_handle is not None and get_asset_type(asset_file_handle) == AssetType.ANIMATION
        if is_animation_asset and preview_player_registered:
            layout.separator(factor=23.0)

        if asset_file_handle is None:
            layout.label(text="No active asset", icon='INFO')
            return

        if ASSETLIB_OP_EditActiveAssetMetadata.is_editing():
            asset_edited_data = wm.edited_asset_metadata
            name_row = layout.row(align=True)
            name_row.prop(asset_edited_data, "name")
            if is_animation_asset:
                name_row.enabled = False
            catalog_row = layout.row(align=True)
            catalog_row.prop(asset_edited_data, "catalog", text="Catalog")

            asset_data = asset_file_handle.asset_data

            self.metadata_prop(layout, asset_data, "description")
            self.metadata_prop(layout, asset_data, "license")
            self.metadata_prop(layout, asset_data, "copyright")
            self.metadata_prop(layout, asset_data, "author")

            wm.created_time_properties.created_time = get_created_date(context, asset_file_handle)
            row = layout.row(align=True)
            row.prop(wm.created_time_properties, "created_time", text="Created Time", icon='TIME')
            row.enabled = False

            wm.armature_name_properties.armature_name = asset_data.get("armature", "")
            row = layout.row(align=True)
            row.prop(wm.armature_name_properties, "armature_name", text="Armature", icon='ARMATURE_DATA')
            row.enabled = False

            if is_animation_asset and preview_player_registered and context.window_manager.animation_preview_widget:
                animation_frame = layout.row(align=True)
                animation_frame.label(text=f"Length: {str(context.window_manager.animation_preview_widget.active_animation_length)}")

            layout.label(text="Tags:")
            row = layout.row()
            row.template_list(
                "ASSET_UL_tags",
                "", 
                asset_edited_data, "tags", 
                asset_edited_data, "active_tag_index",
            )
            col = row.column(align=True)
            add_tag_op = col.operator(ASSETLIB_OP_AddAssetPredefinedTag.bl_idname, icon='ADD', text="")
            add_tag_op.tag_property_path = "edited_asset_metadata.tags"
            rm_tag_op = col.operator(ASSETLIB_OP_RemoveAssetTag.bl_idname, icon='REMOVE', text="")
            rm_tag_op.tag_property_path = "edited_asset_metadata.tags"
            rm_tag_op.active_tag_index = asset_edited_data.active_tag_index

            layout.separator()
            message_box = layout.box()
            message_box.label(text="After saving, refresh to see any changes", icon='QUESTION')
            row = layout.row()
            confirm_op = row.operator(ASSETLIB_OP_EditActiveAssetMetadata.bl_idname, icon='FILE_TICK', text="Save")
            confirm_op.commit_changes = True
            cancel_op = row.operator(ASSETLIB_OP_EditActiveAssetMetadata.bl_idname, icon='CANCEL', text="Cancel")
            cancel_op.commit_changes = False
        else:
            name_row = layout.row(align=True)
            name_row.prop(asset_file_handle, "name")
            catalog_row = layout.row(align=True)
            catalog_row.enabled = False
            catalog_row.prop(asset_file_handle.asset_data, "catalog_id", text="Catalog")

            asset_data = asset_file_handle.asset_data

            self.metadata_prop(layout, asset_data, "description")
            self.metadata_prop(layout, asset_data, "license")
            self.metadata_prop(layout, asset_data, "copyright")
            self.metadata_prop(layout, asset_data, "author")
            
            wm.created_time_properties.created_time = get_created_date(context, asset_file_handle)
            row = layout.row(align=True)
            row.prop(wm.created_time_properties, "created_time", text="Created Time", icon='TIME')
            row.enabled = False

            wm.armature_name_properties.armature_name = asset_data.get("armature", "")
            row = layout.row(align=True)
            row.prop(wm.armature_name_properties, "armature_name", text="Armature", icon='ARMATURE_DATA')
            row.enabled = False

            if is_animation_asset and preview_player_registered and context.window_manager.animation_preview_widget:
                animation_frame = layout.row(align=True)
                animation_frame.label(text=f"Length: {str(context.window_manager.animation_preview_widget.active_animation_length)}")

            row = layout.row()
            row.label(text="Tags:")
            row = layout.row()
            row.template_list(
                "ASSETBROWSER_UL_metadata_tags",
                "asset_tags",
                asset_data,
                "tags",
                asset_data,
                "active_tag",
            )

            layout.separator()
            row = layout.row()
            row.operator(ASSETLIB_OP_EditActiveAssetMetadata.bl_idname, icon='GREASEPENCIL')


class OBJECT_PT_QuickAssetCreationPanel(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOLS"
    bl_category = "Animation"
    bl_label = "Create asset"

    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        return space_data and space_data.browse_mode == 'ASSETS'

    def draw(self, context):
        layout = self.layout
        metadatas = context.window_manager.new_asset_metadata

        # Asset tag list
        layout.prop(metadatas, "export_type", expand=True)
        layout.separator()
        row = layout.row(align=True)
        row.prop(metadatas, "export_selection", text="Export")
        layout.prop(metadatas, "name")
        if metadatas.export_type == "ANIMATION":
            row = layout.row(align=True)
            row.label(text="Render preview:")
            row.prop(metadatas, "generate_preview", text="")
            row = layout.row(align=True)
            row.label(text="Frame range:")
            row.prop(metadatas, "range_start")
            row.prop(metadatas, "range_end")
            
        layout.label(text="Tags:")
        row = layout.row()
        row.template_list("ASSET_UL_tags", "", metadatas, "tags", metadatas, "active_tag_index", type='GRID', columns=2, rows=2)
        col = row.column(align=True)
        add_tag = col.operator(ASSETLIB_OP_AddAssetPredefinedTag.bl_idname, icon='ADD', text="")
        add_tag.tag_property_path = "new_asset_metadata.tags"
        rm_tag_op = col.operator(ASSETLIB_OP_RemoveAssetTag.bl_idname, icon='REMOVE', text="")
        rm_tag_op.tag_property_path = "new_asset_metadata.tags"
        rm_tag_op.active_tag_index = metadatas.active_tag_index

        create_asset_row = layout.row()
        create_asset_op = create_asset_row.operator(
            ASSETLIB_OP_CreateAsset.bl_idname,
            text=f"CREATE {metadatas.export_type}"
        )

        if display_no_rights_file_warning():
            warning = layout.row()
            warning.label(text=display_no_rights_file_warning(), icon='ERROR')

        if not metadatas.name:
            create_asset_op.apply_method = metadatas.export_selection


class OBJECT_PT_QuickAssetLoadPanel(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOLS"
    bl_category = "Animation"
    bl_label = "Apply asset"

    def draw(self, context):
        layout = self.layout
        metadatas = context.window_manager.new_asset_metadata

        # Asset tag list
        row = layout.row(align=True)
        row.prop(metadatas, "export_selection", text="")
        selected_asset = context.asset_file_handle
        multiselection = len(bpy.context.selected_asset_files) > 1 if bpy.context.selected_asset_files else False
        create_asset_row = layout.row()
        if selected_asset is None:
            create_asset_row.enabled = False
            apply_text = "Select an asset to apply"
        else:
            create_asset_row = layout.row()
            apply_text = f"APPLY {get_asset_type(selected_asset).value}" if not multiselection else "APPLY SELECTION"
        create_asset_row.scale_y = 2
        operator = create_asset_row.operator(
            ASSETLIB_OP_ApplyAsset.bl_idname,
            text=apply_text,
        )

        if display_apply_warning():
            warning = layout.row()
            warning.label(text=display_apply_warning(), icon='ERROR')
        operator.apply_method = metadatas.export_selection

class OBJECT_PT_RemoveAssetPanel(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOLS'
    bl_category = "Animation"
    bl_label = "Remove Asset"
    
    @classmethod
    def poll(cls, context):
        space_data = context.space_data
        # can be None when save/reload with a file selector open
        if space_data.params is None:
            return False
        return space_data and space_data.type == 'FILE_BROWSER' and space_data.browse_mode == 'ASSETS'
    
    def draw(self, context):
        self.layout.operator(
            "cube.remove_asset_validation",
            text="delete asset",
            icon="FILE"
        )


class AssetBrowserUIOverrideState(AppOverrideState):
    """ A class to store UI overrides
    """

    def addons(self):
        return [
            "pose_library",
        ]

    @staticmethod
    def class_ignore():
        classes = []
        classes.extend(
            bl_app_override.class_filter(
                bpy.types.Panel,
                # Match any of these values
                bl_space_type={
                    "FILE_BROWSER",
                },
                # Keeps these panels
                blacklist={
                    "ASSETBROWSER_PT_filter",
                    "ASSETBROWSER_PT_display",
                    "ASSETBROWSER_PT_infos",
                    "OBJECT_PT_QuickAssetCreationPanel",
                    "OBJECT_PT_QuickAssetLoadPanel",
                    "OBJECT_PT_RemoveAssetPanel",
                    "FILEBROWSER_PT_bookmarks_volumes",
                    "FILEBROWSER_PT_bookmarks_system",
                    "FILEBROWSER_PT_directory_path",
                    "FILEBROWSER_PT_display",
                    "FILEBROWSER_PT_filter",
                    "FILEBROWSER_PT_bookmarks_favorites"
                },
            ),
        )
        return classes


classes = (
    ASSET_UL_tags,
    ArmatureNameProperties,
    CreatedTimeProperties,
    OBJECT_PT_QuickAssetCreationPanel,
    OBJECT_PT_QuickAssetLoadPanel,
    OBJECT_PT_RemoveAssetPanel,
    ASSETBROWSER_PT_infos,
)

@bpy.app.handlers.persistent
def on_file_open(dummy):
    bpy.context.window_manager.animation_preview_widget.unregister()
    bpy.context.window_manager.animation_preview_widget.register()


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.app.handlers.load_post.append(on_file_open)

    bpy.types.WindowManager.animation_preview_widget = ASSET_AnimationPreviewPlayer()
    bpy.context.window_manager.animation_preview_widget.register()

    bpy.types.WindowManager.armature_name_properties = bpy.props.PointerProperty(type=ArmatureNameProperties)
    bpy.types.WindowManager.created_time_properties = bpy.props.PointerProperty(type=CreatedTimeProperties)
    

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    
    bpy.context.window_manager.animation_preview_widget.unregister()
    del bpy.types.WindowManager.animation_preview_widget
    bpy.app.handlers.load_post.remove(on_file_open)
    del bpy.types.WindowManager.armature_name_properties
    del bpy.types.WindowManager.created_time_properties



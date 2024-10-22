import getpass
import logging
import os
import re
from copy import copy

import bpy

from .asset import asset_editor
from .asset.asset_metadata import AssetMetadata, update_asset_metadata
from .asset.asset_type import AssetType, get_asset_type
from .catalog import catalog_editor
from .catalog.catalog_parser import get_path_from_uuid
from .context import (active_asset, bones_selected, get_viewport_context,
                      local_asset_library_context, thumbnail_settings)
from .editor.user import (can_create, can_edit, rights_file_exists,
                          rights_file_not_found_warning)
from .importer.action_importer import blend_action
from .prefs import get_preferences
from .preview import overlay, thumbnail
from .selection.assets_getter import get_selected_assets
from .selection.selection_mode import (SelectMode, asset_selection_type,
                                       object_selection_type)


ASSET_LIBRARIES_TO_IGNORE = ['LOCAL', 'ALL', 'ESSENTIALS']


def _get_filtered_bones(context, method: str) -> list[bpy.types.PoseBone]:
        if method == "SELECTION":
            return [bone for bone in context.selected_pose_bones_from_active_object]
        elif method == "ALL":
            return [bone for bone in context.object.pose.bones]
        return []


def _create_animation_asset(src_action,name, range_start, range_end, frame_offset, included_bones):
    # Create the asset
    new_asset = bpy.data.actions.new(name)
    try:
        blend_action(
            src_action=src_action,
            dst_action=new_asset,
            src_range=(range_start, range_end),
            frame_offset=frame_offset,
            included_bones=included_bones
        )
    except Exception as e:
        bpy.data.actions.remove(new_asset)

    new_asset.asset_mark()
    new_asset.name = name
    return new_asset


def create_multi_pose_asset(prefix, apply_method):
    new_assets = {}
    selected_armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
    is_multiselection = len(selected_armatures) > 1

    for armature in selected_armatures:
        short_armature_name = armature.name.split('.')[0]
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')

        with(
             bones_selected(bpy.context, _get_filtered_bones(bpy.context,apply_method))
        ):
            pose_name = f"{prefix}_{short_armature_name}" if is_multiselection else prefix
            try:
                bpy.ops.poselib.create_pose_asset(
                    pose_name=pose_name, 
                    activate_new_action=False
                )
            except Exception as e:
                logging.error(f"POSE : Action {pose_name} not correctly created in current file")
                if bpy.data.actions.get(pose_name) is not None:                
                    bpy.data.actions.remove(bpy.data.actions.get(pose_name))
                logging.warning(f"POSE : Cleaning data from last created actions ...")
                for new_asset in new_assets.values():
                    bpy.data.actions.remove(new_asset)
                    logging.warning(f"POSE : {new_asset} removed")
                return {'CANCELLED'}

            created_action = bpy.data.actions[pose_name]   
            created_action.asset_data["armature"] = armature.name
            new_assets[pose_name] = created_action
        
        logging.info(f"POSE : Action {pose_name} created in current file")

    return new_assets


def create_multi_animation_asset(apply_method, prefix, range_start, range_end, frame_offset):
    new_assets = {}
    selected_armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
    is_multiselection = len(selected_armatures) > 1
    for armature in selected_armatures:
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='POSE')
        
        src_action = bpy.context.active_object.animation_data.action
        
        included_bones = _get_filtered_bones(bpy.context, apply_method)
        
        short_armature_name = armature.name.split('.')[0]
        anim_name = f"{prefix}_{short_armature_name}" if is_multiselection else prefix

        bpy.ops.object.mode_set(mode='POSE')
        
        try:
            created_action = _create_animation_asset(
                src_action, 
                anim_name, 
                range_start, 
                range_end, 
                frame_offset, 
                included_bones)
        except Exception as e:
            logging.error(f"ANIMATION : Action {anim_name} not correctly created in current file")
            logging.warning(f"ANIMATION : Cleaning data from last created actions ...")
            for new_asset in new_assets.values():
                bpy.data.actions.remove(new_asset)
                logging.warning(f"ANIMATION : {new_asset} removed")
            return {'CANCELLED'}
        
        created_action.asset_data["armature"] = armature.name
        
        new_assets[anim_name] = created_action

        logging.info(f"ANIMATION : Action {anim_name} created in current file")

    return new_assets

        
def _get_active_library_path(context):
    asset_library_ref = context.area.spaces.active.params.asset_library_ref
    return copy(context.preferences.filepaths.asset_libraries.get(asset_library_ref).path)


def assets_have_armatured_field():
    for asset in bpy.context.selected_asset_files:
        if not asset.asset_data.get("armature"):
            return False
    return True


def assets_have_same_armature_field():
    armatures = []
    if bpy.context.selected_asset_files is not None:
        for asset in bpy.context.selected_asset_files:
            if asset.asset_data["armature"] in armatures:
                return True
            armatures.append(asset.asset_data["armature"])
    return False


def display_apply_warning():
    if asset_selection_type()==SelectMode.MULTI:
        if not assets_have_armatured_field():
            return f"Multiselection will not be applied, no armature field specified"
        elif assets_have_same_armature_field():
            return f"At least two selected assets have the same armature field."
        elif object_selection_type()=='SINGLE':
            return "Several assets selected can't be applied on a single object"
    elif asset_selection_type()==SelectMode.SINGLE:
        if object_selection_type()=='MULTI' and not assets_have_armatured_field():
            return "1 asset selected (without armature field to match) can't be applied on several selected objects"
    return ""


def display_no_rights_file_warning():
    if not rights_file_exists():
        return rights_file_not_found_warning()
    return ""


def apply_single_asset(context, apply_method, action=None):
    selected_asset = action or context.asset_file_handle
    asset_type = get_asset_type(selected_asset)
    logging.info(f"Applying {asset_type.value} asset {selected_asset.name}")

    match asset_type:
        case AssetType.POSE:
            with bones_selected(context, _get_filtered_bones(context,apply_method)):
                bpy.ops.poselib.apply_pose_asset()
        case AssetType.ANIMATION:
            bpy.ops.assetlib.apply_animation_asset(
                apply_method=apply_method
            )
    return {'FINISHED'}


def apply_multi_selection_asset(context, apply_method):
    selected_actions = get_selected_assets()
    selected_armatures = [obj for obj in bpy.context.selected_objects if obj.type == 'ARMATURE']
    for armature in selected_armatures:
        if armature.name in selected_actions.keys():
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            applied_action = selected_actions[armature.name]
            asset_type = get_asset_type(applied_action)
            with active_asset(applied_action):
                apply_single_asset(context, apply_method, applied_action)


class ASSETLIB_OP_CreateAsset(bpy.types.Operator):
    bl_idname = "object.create_asset"
    bl_label = "Create asset"
    bl_options = {'REGISTER', 'UNDO'}

    # TODO: Add a warning message if the pose already exists
    apply_method: bpy.props.EnumProperty(
        items=[
            ("SELECTION", "Selected Controllers", "Apply selected bones"),
            ("ALL", "All Controllers", "Apply all asset's bones"),
        ],
        default="SELECTION"
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        asset_metadata = bpy.context.window_manager.new_asset_metadata
        # Check pose existence
        if can_create() is False:
            return False
        if asset_metadata.name == "":
            return False
        if asset_metadata.name in bpy.data.actions.keys():
            return False
        if context.mode != 'POSE':
            return False
        asset_library_ref = None
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                selected_pose_bone = _get_filtered_bones(context, context.window_manager.new_asset_metadata.export_selection)
                if len(selected_pose_bone) == 0:
                    return False
                
                if asset_metadata.export_type == 'POSE':
                    continue
                for pose_bone in selected_pose_bone:
                    if pose_bone.id_data.animation_data is None or pose_bone.id_data.animation_data.action is None:
                        return False
                    continue

            if area.ui_type == 'ASSETS':
                if asset_library_ref is None:
                    asset_library_ref = area.spaces.active.params.asset_library_ref
                if asset_library_ref in ASSET_LIBRARIES_TO_IGNORE:
                    return False
                library_path = copy(context.preferences.filepaths.asset_libraries.get(asset_library_ref).path)
                # Check if the asset already exists according multislection or not
                if len(context.selected_objects) > 1:
                    for object in context.selected_objects:
                        object_name = object.name.split('.')[0]
                        file_path = f'{library_path}/{asset_metadata.name}_{object_name}.blend'
                        if os.path.exists(file_path):
                            return False        
                file_path = f'{library_path}/{asset_metadata.name}.blend'
                if os.path.exists(file_path):
                    return False
        return True

    def execute(self, context):
        asset_metadata = bpy.context.window_manager.new_asset_metadata
        library_path = None
        asset_library_ref = context.area.spaces.active.params.asset_library_ref
        library_path = copy(context.preferences.filepaths.asset_libraries.get(asset_library_ref).path)
        asset_file_path = None
        window, screen, area3d, region3d, space3d = get_viewport_context()
        with (
            local_asset_library_context(),
            bpy.context.temp_override(window=window,screen=screen,area=area3d,region=region3d,space_data=space3d),
            thumbnail_settings(context)
            ):
            range_start=asset_metadata.range_start if asset_metadata.range_start != -1 else context.scene.frame_start
            range_end=asset_metadata.range_end if asset_metadata.range_end != -1 else context.scene.frame_end
            match asset_metadata.export_type:
                case "POSE":
                    new_assets = create_multi_pose_asset(asset_metadata.name, self.apply_method)
                case "ANIMATION":
                    new_assets = create_multi_animation_asset( 
                        self.apply_method, 
                        asset_metadata.name,
                        range_start, 
                        range_end, 
                        -asset_metadata.range_start)
                case _:
                    return {'CANCELLED'}
            
            for key, value in new_assets.items():
                if value is None:
                    self.report({'ERROR'}, f"Asset {value} not created")
                    return {'CANCELLED'}
                # Generate the asset preview
                self.generate_thumbnail(context,value,range_start,range_end)
                
                # Create the asset catalog
                catalog_uuid = None
                prefs = get_preferences()
                if prefs.catalog_generator:
                    entry_path = prefs.catalog_generator.generate_entry_path()
                    catalog_parent_path = entry_path.split('/')[0]
                    catalog_editor.add_entry(catalog_parent_path, library_path)
                    catalog_uuid = catalog_editor.add_entry(entry_path, library_path)
                asset_file_path = f'{library_path}\\{key}.blend'
                armature = value.asset_data["armature"]
                
                # Update the asset metadata
                action_asset_metadata = AssetMetadata(
                    catalog_id=catalog_uuid,
                    tags=asset_metadata.tags,
                    description=f"Controllers: {str(self.get_asset_controllers_count(value))}",
                    armature=armature,
                    author=getpass.getuser(),
                )
                update_asset_metadata(action_asset_metadata, value)  
                # Push the asset
                bpy.data.libraries.write(asset_file_path, {value}, compress=True, fake_user=True)
                logging.info(f"Asset {key} created in {asset_file_path}")
                
                # clean up
                bpy.data.actions.remove(value)

        # Refresh the asset library
        bpy.ops.asset.library_refresh()
        return {'FINISHED'}

    @property
    def asset_metadata():
        return bpy.context.window_manager.new_asset_metadata
    
    def get_asset_controllers_count(self,asset):
        controllers = set()
        for fcurve in asset.fcurves:
            match = re.search(r'\["(.*?)"\]', fcurve.data_path)
            if match:
                controllers.add(match.group(1))
        return len(controllers)
    
    def generate_thumbnail(self,context,asset,range_start,range_end):
        asset_metadata = bpy.context.window_manager.new_asset_metadata
        if asset_metadata.generate_preview and asset_metadata.export_type == "ANIMATION":
            # Generate the asset preview
            thumbnail.asset_generate_animation_preview(
                asset,
                context,
                frame_range=(range_start, range_end)
            )

        thumbnail.asset_generate_preview(
            asset,
            context
        )

        # Add overlay
        overlay.generate(
            overlay.AVAIABLE_OVERLAYS[asset_metadata.export_type],
            asset
        )


class ASSETLIB_OP_AddAssetPredefinedTag(bpy.types.Operator):
    bl_idname = "object.add_asset_tag"
    bl_label = "Add asset tag"
    bl_options = {'REGISTER', 'UNDO'}
    
    tag_property_path: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        wm = context.window_manager
        tag_property = wm.path_resolve(self.tag_property_path)
        if wm.asset_tags not in tag_property.keys():
            tag = tag_property.add()
            tag.name = wm.asset_tags
        else:
            self.report({'ERROR'}, "Tag already exists")
            return {'CANCELLED'}
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(context.window_manager, "asset_tags", text="")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_popup(self, event)


class ASSETLIB_OP_RemoveAssetTag(bpy.types.Operator):
    bl_idname = "object.remove_asset_tag"
    bl_label = "Remove asset tag"
    bl_options = {'REGISTER', 'UNDO'}

    tag_property_path: bpy.props.StringProperty() # type: ignore
    active_tag_index: bpy.props.IntProperty() # type: ignore

    def execute(self, context):
        wm = context.window_manager
        tag_property = wm.path_resolve(self.tag_property_path)
        active_tag = tag_property[self.active_tag_index]
        if active_tag.name in [AssetType.ANIMATION.value, AssetType.POSE.value]:
            self.report({'ERROR'}, "Cannot remove predefined tag")
            return {'CANCELLED'}
        tag_property.remove(self.active_tag_index)
        return {'FINISHED'}


class ASSETLIB_OP_ApplyAnimationAsset(bpy.types.Operator):
    bl_idname = "assetlib.apply_animation_asset"
    bl_label = "Apply animation asset"
    bl_options = {'REGISTER', 'UNDO'}

    apply_method: bpy.props.EnumProperty(
        items=[
            ("SELECTION", "Selected Controllers", "Apply selected bones"),
            ("ALL", "All Controllers", "Apply all asset's bones"),
        ],
        default="SELECTION"
    )  # type: ignore

    @classmethod
    def poll(cls, context):
        return context.object.animation_data is not None and \
            context.mode == 'POSE'

    def execute(self, context):
        selected_asset = context.asset_file_handle
        if selected_asset.name not in bpy.data.actions.keys():
            library_path = bpy.types.AssetHandle.get_full_library_path(asset_file_handle=selected_asset)

            with bpy.data.libraries.load(library_path, link=True, assets_only=True) as (data_from, data_to):
                data_to.actions = [selected_asset.name]

        src_action = bpy.data.actions[selected_asset.name]
        src_action.use_fake_user = False

        if bpy.context.object.animation_data is None or bpy.context.object.animation_data.action is None:
            bpy.context.object.animation_data_create()
            bpy.context.object.animation_data.action = bpy.data.actions.new(bpy.context.object.name)

        dst_action = bpy.context.object.animation_data.action

        bones = _get_filtered_bones(context, self.apply_method)
        blend_action(
            src_action,
            dst_action,
            frame_offset=context.scene.frame_current,
            included_bones=bones
        )

        return {'FINISHED'}


class ASSETLIB_OP_ApplyAsset(bpy.types.Operator):
    bl_idname = "assetlib.apply_asset"
    bl_label = "Apply animation asset"
    bl_options = {'REGISTER', 'UNDO'}

    apply_method: bpy.props.EnumProperty(
        items=[
            ("SELECTION", "Selected Controllers", "Apply selected bones"),
            ("ALL", "All Controllers", "Apply all asset's bones"),
        ],
        default="SELECTION"
    )  # type: ignore
    
    @classmethod
    def poll(self, context):
        if asset_selection_type()==SelectMode.MULTI:
            if not assets_have_armatured_field():
                return False
            elif assets_have_same_armature_field():
                return False
            elif object_selection_type()=='SINGLE':
                return False
        elif asset_selection_type()==SelectMode.SINGLE:
            if object_selection_type()=='MULTI' and not assets_have_armatured_field():
                return False
            elif object_selection_type()=='SINGLE':
                return True
        selected_asset = context.asset_file_handle
        return selected_asset is not None and context.area.ui_type == 'ASSETS'


    def execute(self, context):
        if asset_selection_type()==SelectMode.SINGLE and object_selection_type()==SelectMode.SINGLE:
            logging.info("Asset Library : 1 asset selected in ASSET BROWSER and 1 object selected in 3D VIEW")
            logging.info("Asset Library : Applying asset without checking armature name...")
            apply_single_asset(context, self.apply_method)
        elif (asset_selection_type()==SelectMode.SINGLE or asset_selection_type()==SelectMode.MULTI) and object_selection_type()==SelectMode.MULTI:
            apply_multi_selection_asset(context, self.apply_method)
        return {'FINISHED'}


class ASSETLIB_OP_BlendAsset(bpy.types.Operator):
    bl_idname = "assetlib.blend_asset"
    bl_label = "Blend animation asset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_asset = context.asset_file_handle
        asset_type = get_asset_type(selected_asset)
        logging.info(f"Blending asset {selected_asset.name}")

        match asset_type:
            case AssetType.POSE:
                bpy.ops.poselib.blend_pose_asset('INVOKE_DEFAULT')
            case AssetType.ANIMATION:
                # TODO: Implement animation blending ?
                pass
        return {'FINISHED'}


class Cancel(bpy.types.Operator):
    bl_idname = "cube.cancel"
    bl_label = "Do nothing"

    def execute(self, context):
        return {"CANCELLED"}


class ASSETLIB_OP_RemoveSelectedAsset(bpy.types.Operator):
    bl_idname = "cube.remove_asset"
    bl_label = "Launch remove asset"

    def execute(self, context):
        # Remove the asset
        for asset in bpy.context.selected_asset_files:
            # Get the current library name and library path
            filepath = bpy.types.AssetHandle.get_full_library_path(asset_file_handle=asset)
            # Construct the file path and convert backslashes to forward slashes
            filepath = str(filepath).replace("\\", "/")
            os.remove(filepath)
    
        # Refresh the asset library and record the end time
        bpy.ops.asset.library_refresh()
            # Return the 'FINISHED' status
        return {'FINISHED'}


class ASSETLIB_OP_RemoveAssetValidation(bpy.types.Operator):
    """Launch file explorer in a specified resource directory"""
    bl_idname = "cube.remove_asset_validation"
    bl_label = "Launch file explorer in a specified resource directory"

    @classmethod
    def poll(cls, context):
        if bpy.context.selected_asset_files:
            for asset in bpy.context.selected_asset_files:
                asset_author = asset.asset_data.author
                if not can_edit(asset_author):
                    return False
        asset_library_ref = None
        for area in context.screen.areas:
            if area.ui_type == 'ASSETS':
                asset_library_ref = area.spaces.active.params.asset_library_ref
                break
        if asset_library_ref in ASSET_LIBRARIES_TO_IGNORE:
            return False
        return True

    def execute(self, context):
        remove_asset_validation()
        return {"FINISHED"}


def remove_asset_validation():
    def draw(self, context):
        self.layout.label(text="Are you sure you want to delete the asset?")
        row = self.layout.row()
        row.operator("cube.remove_asset", text="OK")
        row = self.layout.row()
        row.operator("cube.cancel", text="Cancel")

    bpy.context.window_manager.popup_menu(draw, title="Remove Asset", icon='INFO')


class ASSETLIB_OP_EditActiveAssetMetadata(bpy.types.Operator):
    bl_idname = "assetlib.edit_active_asset"
    bl_label = "Edit asset"
    
    active_asset: bpy.props.StringProperty() # type: ignore
    commit_changes: bpy.props.BoolProperty(default=False) # type: ignore
    cancel_changes: bpy.props.BoolProperty() # type: ignore
    _handler = None

    editing_field_datapath = {
        'catalog': 'asset_data.catalog_id',
        'tags': 'asset_data.tags',
        'name': 'name',
    }

    @classmethod
    def poll(cls, context):
        # Example condition to enable/disable the operator
        asset = context.asset_file_handle
        author = asset.asset_data.author
        if not can_edit(author):
            return False
        return True


    def load_editing_fields(self, context):
        editing_fields = context.window_manager.edited_asset_metadata
        asset = context.asset_file_handle
        library_path = _get_active_library_path(context)
        editing_fields.name = asset.name

        catalogs_path = get_path_from_uuid(library_path, asset.asset_data.catalog_id)
        editing_fields.catalog =f"{catalogs_path}"
        editing_fields.tags.clear()
        for tag in asset.asset_data.tags:
            tag_item = editing_fields.tags.add()
            tag_item.name = tag.name

    @classmethod
    def is_editing(cls):
        return cls._handler is not None

    def invoke(self, context, event):
        cls = self.__class__

        if cls._handler:
            if self.commit_changes:
                asset = context.asset_file_handle
                asset_library_ref = context.area.spaces.active.params.asset_library_ref
                library_path = copy(context.preferences.filepaths.asset_libraries.get(asset_library_ref).path)
                fields_to_commit = []

                # Resolve the metadata new values to commit
                for field_name, datapath in cls.editing_field_datapath.items():
                    field_value = getattr(context.window_manager.edited_asset_metadata, field_name)
                    if datapath == 'asset_data.tags':
                        field_value = ",".join([item.name for item in field_value])
                    if datapath == 'asset_data.catalog_id':
                        field_value = catalog_editor.add_entry(field_value, library_path)
                    fields_to_commit.append((datapath, field_value))                    

                if asset.local_id is not None:
                    asset_editor.set_local_asset_properties(
                        asset.name,
                        asset.id_type,
                        fields_to_commit
                    )
                else:
                    asset_filepath = bpy.types.AssetHandle.get_full_library_path(asset_file_handle=asset)
                    asset_editor.set_shared_asset_properties(
                        asset_filepath,
                        asset.name,
                        asset.id_type,
                        fields_to_commit
                    )
                self.cancel(context)

                return {'FINISHED'}
            else:
                self.cancel(context)            
                return {'CANCELLED'}
        elif context.asset_file_handle is not None and context.area.ui_type == 'ASSETS':
            self.active_asset = context.asset_file_handle.name
            context.window_manager.modal_handler_add(self)
            cls._handler = self

            # Load edited metadata fields
            self.load_editing_fields(context)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Bad context")
            return {'CANCELLED'}

    def modal(self, context, event):
        if context.asset_file_handle is None or self.active_asset != context.asset_file_handle.name:
            self.cancel(context)
            return {'CANCELLED'}

        return {'PASS_THROUGH'}
    

    def cancel(self, context):
        cls = self.__class__
        cls._handler = None


classes = (
    Cancel,
    ASSETLIB_OP_RemoveAssetValidation,
    ASSETLIB_OP_CreateAsset,
    ASSETLIB_OP_AddAssetPredefinedTag,
    ASSETLIB_OP_RemoveAssetTag,
    ASSETLIB_OP_RemoveSelectedAsset,
    ASSETLIB_OP_ApplyAsset,
    ASSETLIB_OP_BlendAsset,
    ASSETLIB_OP_ApplyAnimationAsset,
    ASSETLIB_OP_EditActiveAssetMetadata
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

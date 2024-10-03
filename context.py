import bpy
import contextlib
import logging

def get_viewport_context():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                return (window, window.screen, area, region, area.spaces[0])


@contextlib.contextmanager
def bones_selected(context: bpy.types.Context, bones: list[bpy.types.PoseBone]) -> None:
    """Temporarily change the bone selection.

    Args:
        context (bpy.types.Context): Context to change the selection in
        bones (list[str]): List of bones to select
    """
    bone_names = [bone.name for bone in bones]
    original_selection = [bone.name for bone in context.selected_pose_bones_from_active_object]
    for bone in context.object.pose.bones:
        bone.bone.select = bone.name in bone_names

    try:
        yield

    finally:
        for bone in context.object.pose.bones:
            bone.bone.select = bone.name in original_selection


@contextlib.contextmanager
def local_asset_library_context():
    """Change the asset library setting."""
    current_area = None
    for area in bpy.context.screen.areas:
        if area.ui_type == 'ASSETS':
            current_area = area.spaces.active.params.asset_library_ref
            area.spaces.active.params.asset_library_ref = 'LOCAL'
            break
    try:
        yield

    finally:
        def defer():
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.ui_type == 'ASSETS':
                        area.spaces.active.params.asset_library_ref = current_area
        bpy.app.timers.register(defer, first_interval=0.1)


@contextlib.contextmanager
def thumbnail_settings(context: bpy.types.Context):
    """Temporarily change the scene camera.

    Args:
        obj (bpy.types.Object): Object to un-hide
        scene (bpy.types.Scene): Scene Object is in
    """
    scene = context.scene
    _, _, _, _, space3d = get_viewport_context()
    use_existing_camera = space3d.region_3d.view_perspective == 'CAMERA'
    space3d.overlay.show_overlays = False

    if not use_existing_camera:
        original_camera = scene.camera
        camera = bpy.data.cameras.new("AssetCaptureCamera")
        camera_obj = bpy.data.objects.new("AssetCaptureCamera", camera)

    try:
        if not use_existing_camera:
            scene.camera = camera_obj
            bpy.ops.view3d.camera_to_view()

        yield

    finally:
        if not use_existing_camera:
            bpy.data.objects.remove(camera_obj)
            bpy.data.cameras.remove(camera)
            scene.camera = original_camera

        space3d.overlay.show_overlays = True


@contextlib.contextmanager
def active_asset(action):
    areas = [area for window in bpy.context.window_manager.windows for area in window.screen.areas if area.ui_type == 'ASSETS']

    for area in areas:
        for space in area.spaces:
            if space.type == 'FILE_BROWSER':
                asset_space = space                            
                break

    if asset_space:
        asset_space.activate_file_by_relative_path(relative_path=action.relative_path)
    try:
        yield
    finally:
        logging.info(f"Active asset set to {action.name}")
            
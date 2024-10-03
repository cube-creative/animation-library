import bpy

KEYMAP_NAME = "File Browser Main"
KEYMAP_SPACE_TYPE = "FILE_BROWSER"

def register() -> None:
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon is None:
        # This happens when Blender is running in the background.
        return
    
    km = wm.keyconfigs.addon.keymaps.get(
        KEYMAP_NAME,
        wm.keyconfigs.addon.keymaps.new(name=KEYMAP_NAME, space_type=KEYMAP_SPACE_TYPE)
    )
    
    # Remove existing poselib shortcut
    kmip = km.keymap_items.get("poselib.apply_pose_asset")
    if kmip:
        km.keymap_items.remove(kmip)

    # DblClick to apply pose.
    kmi = km.keymap_items.new("assetlib.apply_asset", "LEFTMOUSE", "DOUBLE_CLICK")


def unregister() -> None:
    wm = bpy.context.window_manager
    if wm.keyconfigs.addon is None:
        # This happens when Blender is running in the background.
        return

    km = wm.keyconfigs.addon.keymaps.get(
        KEYMAP_NAME,
        None
    )
    if km is None:
        return

    # Clear shortcuts from the keymap.
    # Remove existing poselib shortcut
    kmip = km.keymap_items.get('assetlib.apply_asset')
    if kmip:
        km.keymap_items.remove(kmip)


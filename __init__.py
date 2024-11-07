bl_info = {
    "name": "Animation Library",
    "description": "Cube Animation Library",
    "category": "Cube Animation",
    "author": "Cube",
    "blender": (3, 1, 0),
    "version": (1, 10, 7),
}


from . import ui, props, ops, keymaps, prefs


# Overide the default 
assetbrowser_ui_override = ui.AssetBrowserUIOverrideState()


def register():
    prefs.register()
    props.register()
    ops.register()
    ui.register()
    assetbrowser_ui_override.setup()
    keymaps.register()


def unregister():
    keymaps.unregister()
    assetbrowser_ui_override.teardown()
    ui.unregister()
    ops.unregister()
    props.unregister()
    prefs.unregister()
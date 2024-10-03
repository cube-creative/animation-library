import logging

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from ..asset.asset_type import AssetType, get_asset_type
from . import thumbnail

THUMBNAIL_FRAME_RATE = 24


def _get_asset_browser_tool_props_region():
    for window in bpy.data.window_managers[0].windows:
        for area in window.screen.areas:
            if area.type == 'FILE_BROWSER' and area.spaces[0].browse_mode == 'ASSETS':
                return area.regions[4]
    return None

def _get_assetbrowser_panel_elements():
    """ Retrieve assetbrowser panels elements

        Returns:
            List[Tuple(Area, Tool Props Region)]: List of assetbrowser's elements as tuples (Area, Tool Props Region) 
    """
    assetbrowser_ui = []
    for window in bpy.data.window_managers[0].windows:
        for area in window.screen.areas:
            if area.type == 'FILE_BROWSER' and area.spaces[0].browse_mode == 'ASSETS':
                assetbrowser_ui.append((area, area.regions[4]))
    return assetbrowser_ui

class ASSET_AnimationPreviewPlayer:
    def __init__(self):
        self.player_position = [10,10]
        self.active_frame_uvs = ((0, 0), (.1, 0), (.1, .1), (0, .1))
        self.spritesheet_frame_dimension = 1
        self.preview_texture = []
        self.active_thumbnail = None
        self.thumbnail_frame_current = 0
        self.active_selection = None
        self.shader = gpu.shader.from_builtin('IMAGE')
    
    def register(self):
        self._draw_handler = bpy.types.SpaceFileBrowser.draw_handler_add(self._draw_animation_preview, (), 'TOOL_PROPS', 'POST_PIXEL')
        self._timer = bpy.app.timers.register(self._update_thumbnail_frame)

    def unregister(self):
        bpy.types.SpaceFileBrowser.draw_handler_remove(self._draw_handler, 'TOOL_PROPS')
        if bpy.app.timers.is_registered(self._timer):
            bpy.app.timers.unregister(self._timer)

    @property
    def active_animation_length(self)->str:
        if self.active_thumbnail is not None:
            return self.active_thumbnail.frames_total
        return 0

    def _update_thumbnail_frame(self):
        """ Refresh the thumbnail frame according to THUMBNAIL_FRAME_RATE
        """
        try:
            # get height from the context
            asset_browsers_areas_info = _get_assetbrowser_panel_elements()
            _, default_region = next(iter(asset_browsers_areas_info), (None, None))
            if default_region is not None:
                self.player_position[1] = default_region.height - thumbnail.THUMBNAIL_SIZE - 10
                self.player_position[0] = default_region.width/2 - thumbnail.THUMBNAIL_SIZE/2
            if self.active_thumbnail is None:
                return 1/THUMBNAIL_FRAME_RATE

            if self.thumbnail_frame_current >= self.active_thumbnail.frames_total - 1:
                self.thumbnail_frame_current = 0
            else:
                self.thumbnail_frame_current += 1

            x, y = thumbnail.get_frame_coordinates(
                self.thumbnail_frame_current-1,
                self.active_thumbnail,
                remap_to_range=(0, 1)
            )
            spritesheet_frame_dimension = 1/self.active_thumbnail.frames_rows

            self.active_frame_uvs = (
                (x, y), 
                (x+spritesheet_frame_dimension, y), 
                (x+spritesheet_frame_dimension, y+spritesheet_frame_dimension), 
                (x, y+spritesheet_frame_dimension)
            )


            for area, region in asset_browsers_areas_info:
                area.tag_redraw()
        except Exception as e:
            logging.error(e)

        return 1/THUMBNAIL_FRAME_RATE

    def _clear_thumbnail_cache(self):
        self.preview_texture = None
        self.active_thumbnail = None

    def _generate_tumbnail_cache(self):
        """ Generate the thumbnail cache (Gpu texture) for the active selection
        """
        # Begin cache update
        if self.active_selection is None:
            return

        try:
            library_path = bpy.types.AssetHandle.get_full_library_path(self.active_selection)
            self.active_thumbnail = thumbnail.get_asset_thumbnail(
                self.active_selection.name,
                asset_path=library_path
            )
        except FileNotFoundError as e:
            logging.warning(e)
            return
        else:
            self.preview_texture =  gpu.texture.from_image(self.active_thumbnail.image)


    def _draw_animation_preview(self):
        """ Draw the animation preview in the asset browser
        """
        selected_asset = bpy.context.asset_file_handle

        if selected_asset is None or get_asset_type(selected_asset) != AssetType.ANIMATION:
            self._clear_thumbnail_cache()
            self.active_selection = None
            return

        if self.active_selection != selected_asset:
            self.thumbnail_frame_current = 0
            self.active_selection = selected_asset
            self._clear_thumbnail_cache()
            self._generate_tumbnail_cache()
        
        if self.preview_texture is None:
            return

        self.batch = batch_for_shader(
            self.shader, 'TRI_FAN',
            {
                "pos": (
                    (self.player_position[0], self.player_position[1]),
                    (self.player_position[0]+thumbnail.THUMBNAIL_SIZE, self.player_position[1]),
                    (self.player_position[0]+thumbnail.THUMBNAIL_SIZE, self.player_position[1]+thumbnail.THUMBNAIL_SIZE),
                    (self.player_position[0], self.player_position[1]+thumbnail.THUMBNAIL_SIZE)),
                "texCoord": self.active_frame_uvs,
            },
        )

        self.shader.bind()
        self.shader.uniform_sampler("image", self.preview_texture)
        self.batch.draw(self.shader)
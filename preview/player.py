import logging
import threading
from ..asset.asset_type import AssetType, get_asset_type
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from queue import Queue, Empty

from . import thumbnail

THUMBNAIL_FRAME_RATE = 24


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
        self.active_thumbnail: thumbnail.AnimationPreviewMetadata = None
        self.active_preview_texture: gpu.types.GPUTexture = None
        self.thumbnail_frame_current = 0
        self.active_selection = None
        self.shader = gpu.shader.from_builtin('IMAGE')
        self.loaded_preview_queue = Queue()

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
            if self.active_thumbnail is None or self.active_preview_texture is None:
                try:
                    loaded_thumbnail = self.loaded_preview_queue.get(block=False)
                except Empty:
                    pass
                else:
                    self.active_thumbnail = loaded_thumbnail
                    image_width = self.active_thumbnail.frames_rows * thumbnail.THUMBNAIL_SIZE
                    self.active_preview_texture  = gpu.types.GPUTexture(
                        (image_width,image_width),
                        layers=0,
                        is_cubemap=False,
                        format='RGBA8',
                        data=self.active_thumbnail.buffer,
                    )
                return 1/THUMBNAIL_FRAME_RATE

            if self.thumbnail_frame_current >= self.active_thumbnail.frames_total - 1:
                self.thumbnail_frame_current = 0
            else:
                self.thumbnail_frame_current += 1

            x, y = thumbnail.get_frame_coordinates(
                self.thumbnail_frame_current-1,
                self.active_thumbnail.frames_rows,
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
        if self.active_thumbnail is not None:
            del self.active_thumbnail.buffer
            self.active_thumbnail = None
        if self.active_preview_texture is not None:
            del self.active_preview_texture
            self.active_preview_texture = None

    def _is_cache_cleared(self):
        return self.active_thumbnail is None

    def _generate_tumbnail_cache(self):
        """ Generate the thumbnail cache (Gpu texture) for the active selection
        """
        # Begin cache update
        if self.active_selection is None:
            return

        library_path = bpy.types.AssetHandle.get_full_library_path(self.active_selection)
        threading.Thread(
            target=thumbnail.load_thumbnail,
            args=(
                self.loaded_preview_queue,
                self.active_selection.name,
                library_path
            ),
        ).start()

    def _draw_animation_preview(self):
        """ Draw the animation preview in the asset browser
        """
        selected_asset = bpy.context.asset_file_handle

        if selected_asset is None or get_asset_type(selected_asset) != AssetType.ANIMATION:
            self.active_selection = None
            if not self._is_cache_cleared():
                self._clear_thumbnail_cache()
            return

        if self.active_selection != selected_asset:
            self.thumbnail_frame_current = 0
            self.active_selection = selected_asset
            self._clear_thumbnail_cache()
            self._generate_tumbnail_cache()
        
        if self.active_thumbnail is None or self.active_preview_texture is None:
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
        self.shader.uniform_sampler("image", self.active_preview_texture)
        self.batch.draw(self.shader)
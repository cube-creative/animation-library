from dataclasses import dataclass
import logging
import re
import time
import bpy 
import gpu
from gpu_extras.batch import batch_for_shader
import math
from mathutils import Matrix
import numpy


THUMBNAIL_NAME_REGEX = re.compile("(?P<asset_name>.+)_THUMBNAIL_(?P<frame_number>\d+)")
THUMBNAIL_SIZE = 128


@dataclass
class Thumbnail:
    asset_name: str
    image: bpy.types.Image
    frames_total: int
    frames_rows: int


def _find_asset_thumbnail( asset_name: str, images_names: list[str]):
        for image_name in images_names:
            match = THUMBNAIL_NAME_REGEX.match(image_name)
            if match is None:
                continue
            metadata = match.groupdict()
            if metadata["asset_name"] == asset_name:
                return (image_name, match.groupdict())
        return (None, None)


def _link_asset_thumbnail(asset_name, asset_path: str):
        start = time.time()
        # Try to append preview image
        with bpy.data.libraries.load(asset_path, link=True) as (data_from, data_to):
            thumb_name, _ = _find_asset_thumbnail(asset_name, data_from.images)
            data_to.images = [thumb_name]
        
        logging.info(f"Thumbnail loaded in {time.time()-start} ms")


def get_asset_thumbnail(
          asset_name: str,
          asset_path: str=None)-> Thumbnail:
    """Get the thumbnail image for the given asset name.

    Args:
        asset_name (str): The name of the asset to get the thumbnail for
        create (bool, optional): If True, create a new thumbnail if none is found. Defaults to True.
        asset_path (str, optional): The path to the asset to load the thumbnail from. Defaults to None.

    Raises:
        FileNotFoundError: If no thumbnail is found and create is False

    Returns:
        bpy.types.Image: The thumbnail image
    """
    
    name, info = _find_asset_thumbnail(asset_name, bpy.data.images.keys())

    if name is None and asset_path not in [None, ""]:
        _link_asset_thumbnail(asset_name, asset_path)
        name, info = _find_asset_thumbnail(asset_name, bpy.data.images.keys())
    if name is not None:
        thumbnail_image = bpy.data.images[name]
        frame_total = int(info["frame_number"])
        return Thumbnail(
            asset_name=asset_name,
            image=thumbnail_image,
            frames_total=frame_total,
            frames_rows=thumbnail_image.size[0]/THUMBNAIL_SIZE
        )
    else:
        return None


def asset_generate_animation_preview(
        asset: bpy.types.ID,
        context: bpy.types.Context,
        frame_range: tuple[int, int] = (1, 50),
    ):
    """Capture the viewport and store it in the image buffer.

    Args:
        context (bpy.types.Context): The context to capture the viewport from
        framebuffer_image (bpy.types.Image): The image buffer to store the captured viewport
        frame_range (tuple[int, int], optional): The range of frames to capture. Defaults to (1, 50).

    Returns:
        bpy.types.Image: The image buffer containing the captured animation
    """
    animation_preview = get_asset_thumbnail(asset.name)
    if animation_preview is not None:
        bpy.data.images.remove(animation_preview.image)
    animation_preview = create_thumbnail(asset, frame_range=frame_range)
    # Check if the total number of frames has changed
    width = height = THUMBNAIL_SIZE
    canvas_width = canvas_height = animation_preview.image.size[0]

    preview_spritesheet = gpu.types.GPUOffScreen(
        canvas_width,
        canvas_height
    )
    img_size = 2/animation_preview.frames_rows
    shader = gpu.shader.from_builtin('IMAGE')

    for frame in range(frame_range[0], frame_range[1]):
        remaped_frame = numpy.interp(frame, [frame_range[0], frame_range[1]], [0, animation_preview.frames_total])
        bpy.context.scene.frame_current= frame
        capture = _capture_viewport(context)
        captured_viewport = gpu.types.GPUTexture((width, height), data=capture)
        x, y = get_frame_coordinates(
            remaped_frame-1,
            animation_preview,
            remap_to_range=(-1, 1)
        )
        pos = (
            (x, y), 
            (x+img_size, y), 
            (x+img_size, y+img_size), 
            (x, y+img_size)
        )

        #  Render the frame to the spritesheet
        with preview_spritesheet.bind():
            # Optionnally set scissor test
            # gpu.state.scissor_test_set(True)
            # gpu.state.scissor_set(0,0, 128, 128)

            fb = gpu.state.active_framebuffer_get()
            
            with gpu.matrix.push_pop():
                # reset matrices -> use normalized device coordinates [-1, 1]
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(Matrix.Identity(4))
                
                
                batch = batch_for_shader(
                    shader, 'TRI_FAN',
                    {
                        "pos": pos,
                        "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
                    },
                )
                shader.uniform_sampler("image", captured_viewport)
                batch.draw(shader)

    # export result        
    with preview_spritesheet.bind():
        pixelBuffer = fb.read_color(0, 0, canvas_width, canvas_height, 4, 0, 'FLOAT')
        pixelBuffer.dimensions = canvas_width * canvas_height * 4

    # thumbnail.image.scale(canvas_width, canvas_height)
    animation_preview.image.pixels.foreach_set(pixelBuffer)
    animation_preview.image.pack()
    preview_spritesheet.free()

    return animation_preview

 
def get_frame_coordinates(
        frame:int, 
        thumbnail: Thumbnail,
        remap_to_range: tuple[float, float] = None):
    """Get the coordinates of the frame in the thumbnail image.

    Args:
        frame (int): The frame number
        thumbnail (Thumbnail): The thumbnail to get the coordinates for
        remap_to_range (tuple[float, float], optional): The range to remap the coordinates to. Defaults to None.

    Returns:
        tuple[int, int]: The row and column coordinates
    """
    # temporary fix for negative frame
    if frame < 0:
        frame = 0
    row = frame // thumbnail.frames_rows
    col = frame % thumbnail.frames_rows
    # TODO: Handle case where frame is out of bounds

    if remap_to_range is not None:
        row = numpy.interp(row, [0, thumbnail.frames_rows], remap_to_range)
        col = numpy.interp(col, [0, thumbnail.frames_rows], remap_to_range)

    return row, col


def _capture_viewport(
        context: bpy.types.Context,
    ):
    """Capture the viewport and store it in the asset preview.

    Args:
        context (bpy.types.Context): The context to capture the viewport from
        asset_name (str): The name of the asset to generate the preview for
    """
    preview_with = THUMBNAIL_SIZE
    preview_height = THUMBNAIL_SIZE
    preview_buffer_dimensions = preview_with * preview_height * 4
    preview_offscreen_render = gpu.types.GPUOffScreen(preview_with, preview_height)
    # Setup Render Buffer
    viewport_render_width = bpy.context.scene.render.resolution_x
    viewport_render_height = bpy.context.scene.render.resolution_y
    viewport_render = gpu.types.GPUOffScreen(viewport_render_width, viewport_render_height)

    with viewport_render.bind():
        fb = gpu.state.active_framebuffer_get()
        scene = context.scene
        view_matrix = scene.camera.matrix_world.inverted()
        projection_matrix = scene.camera.calc_matrix_camera(
            context.evaluated_depsgraph_get(),
            x=viewport_render_width,
            y=viewport_render_height,
            scale_x=1.0,
            scale_y=1.0)

        # Another possibility to get the view matrix and projection matrix
        # space3d.region_3d.view_matrix,
        # space3d.region_3d.window_matrix,

        fb.clear(color=(1.0, 0.0, 0.0, 1.0))
        viewport_render.draw_view3d(
            scene,
            context.view_layer,
            context.space_data,
            context.region,
            view_matrix,
            projection_matrix,
            do_color_management=True,
            draw_background=True)

        # Read the pixels from the render buffer
        viewport_render_buffer = fb.read_color(
            int((viewport_render_width-viewport_render_height)/2), 0, 
            viewport_render_height, viewport_render_height, 
            4, 
            0,
            'FLOAT'
        )
    
    viewport_render.free()
    viewport_render_buffer.dimensions = viewport_render_height * viewport_render_height * 4
    render_texture = gpu.types.GPUTexture((viewport_render_height, viewport_render_height), data=viewport_render_buffer)

    with preview_offscreen_render.bind():
        fb = gpu.state.active_framebuffer_get()
        with gpu.matrix.push_pop():
            gpu.matrix.load_matrix(Matrix.Identity(4))
            gpu.matrix.load_projection_matrix(Matrix.Identity(4))
            shader = gpu.shader.from_builtin('IMAGE')
            batch = batch_for_shader(
                shader, 'TRI_FAN',
                {
                    "pos": ((-1, -1), (1, -1), (1, 1), (-1, 1)),
                    "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
                },
            )
            shader.uniform_sampler("image", render_texture)
            batch.draw(shader)
            
            # Read the pixels from the render buffer
            pixelBuffer = fb.read_color(0, 0, preview_with, preview_height, 4, 0, 'FLOAT')
    
    preview_offscreen_render.free()
    pixelBuffer.dimensions = preview_buffer_dimensions

    return pixelBuffer            
            

def asset_generate_preview(
        asset: bpy.types.ID,
        context: bpy.types.Context,
    ):
    # Setup ID Preview
    preview = asset.preview_ensure()
    preview.image_size = (THUMBNAIL_SIZE, THUMBNAIL_SIZE)
    preview_pixels = _capture_viewport(context)

    # Save the image buffer back to the ID preview
    preview.image_pixels_float[:] = preview_pixels

def create_thumbnail(
        asset: bpy.types.ID,
        frame_range: tuple[int, int] = (1, 50)
    ):
    frame_count = frame_range[1]-frame_range[0]
    frame_in_row = math.ceil(math.sqrt(frame_count))
    image_width = THUMBNAIL_SIZE*frame_in_row
    thumbnail_image = bpy.data.images.new(
        f"{asset.name}_THUMBNAIL_{frame_count}",
        image_width,
        image_width,
        float_buffer=True
    )
    animation_preview = Thumbnail(
    asset_name=asset.name,
    image=thumbnail_image,
    frames_total=frame_count,
    frames_rows=thumbnail_image.size[0]/THUMBNAIL_SIZE
    )
    return animation_preview
from dataclasses import dataclass
import re
import bpy 
import gpu
from gpu_extras.batch import batch_for_shader
import math
from mathutils import Matrix
import numpy
import struct
from queue import Queue


THUMBNAIL_NAME_REGEX = re.compile("(?P<asset_name>.+)_THUMBNAIL_(?P<frame_number>\d+)")
THUMBNAIL_SIZE = 128

@dataclass
class AnimationPreviewMetadata:
    """Dataclass to store loaded metadata of an animation preview.
    """
    asset_name: str
    buffer: gpu.types.Buffer
    frames_total: int
    frames_rows: int


def load_thumbnail(queue:Queue, asset_name, asset_path):
    animation_preview_texture = None
    if asset_path not in [None, ""]:
        # Use temporary data to load the asset to avoid datablock linking persistence
        with bpy.data.temp_data(filepath=asset_path) as tmp_data:
            # Load asset data
            with tmp_data.libraries.load(asset_path, link=False) as (data_from, data_to):
                data_to.actions = data_from.actions
            
            asset = tmp_data.actions.get(asset_name)
            anim_preview = asset.animation_preview
            if anim_preview is not None:
                buffer_data = gpu.types.Buffer(
                    'FLOAT',
                    anim_preview.preview_buffer_size,
                    struct.unpack(
                        f'{anim_preview.preview_buffer_size}f',
                        asset.animation_preview.preview_buffer
                    )
                )
                animation_preview_texture = buffer_data
            if animation_preview_texture is not None:
                queue.put(
                    AnimationPreviewMetadata(
                        asset_name=asset_name,
                        buffer=animation_preview_texture,
                        frames_total=anim_preview.frames_total,
                        frames_rows=anim_preview.frames_rows
                    ),
                    block=False
                )
    #TODO: Put default image

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
    # Create thumbnail image 
    frame_count = frame_range[1]-frame_range[0]
    frame_in_row = math.ceil(math.sqrt(frame_count))
    image_width = THUMBNAIL_SIZE*frame_in_row
    
    # Check if the total number of frames has changed
    width = height = THUMBNAIL_SIZE
    canvas_width = canvas_height = image_width

    preview_spritesheet = gpu.types.GPUOffScreen(
        canvas_width,
        canvas_height
    )
    img_size = 2/frame_in_row
    shader = gpu.shader.from_builtin('IMAGE')

    for frame in range(frame_range[0], frame_range[1]):
        remaped_frame = numpy.interp(frame, [frame_range[0], frame_range[1]], [0, frame_count])
        bpy.context.scene.frame_current= frame
        capture = _capture_viewport(context)
        captured_viewport = gpu.types.GPUTexture((width, height), data=capture)
        x, y = get_frame_coordinates(
            remaped_frame-1,
            frame_in_row,
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

    with preview_spritesheet.bind():
        pixelBuffer = fb.read_color(0, 0, canvas_width, canvas_height, 4, 0, 'FLOAT')
        buffer_dimension = canvas_width * canvas_height * 4
        pixelBuffer.dimensions = buffer_dimension

        # export result        
        asset.animation_preview.preview_buffer = struct.pack(f'{buffer_dimension}f', *pixelBuffer)
        asset.animation_preview.preview_buffer_size = buffer_dimension
        asset.animation_preview.frames_total = frame_count
        asset.animation_preview.frames_rows = frame_in_row
        asset.animation_preview.frame_size = THUMBNAIL_SIZE
 

def get_frame_coordinates(
        frame:int, 
        square_size:int,
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
    row = frame // square_size
    col = frame % square_size
    # TODO: Handle case where frame is out of bounds

    if remap_to_range is not None:
        row = numpy.interp(row, [0, square_size], remap_to_range)
        col = numpy.interp(col, [0, square_size], remap_to_range)

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
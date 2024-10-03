import uuid
from pathlib import Path
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix
from pathlib import Path

AVAIABLE_OVERLAYS = {
    'POSE': Path(__file__).parent.joinpath('pose_overlay.png'),
    'ANIMATION': Path(__file__).parent.joinpath('animation_overlay.png'),
}


def generate(overlay_image_path: Path, datablock: bpy.types.ID):
    """Draw an overlay on the datablock preview image

    Args:
        overlay_image (Path): The path to the overlay image
        datablock (bpy.types.ID): The datablock to draw the overlay on
    """
    preview = datablock.preview_ensure()
    
    preview_with = preview.image_size[0]
    preview_height = preview.image_size[1]
    buffer_dimensions = preview_with * preview_height * 4
    preview_overlay_render = gpu.types.GPUOffScreen(preview_with, preview_height)


    # Load the preview image to the GPU
    preview_buffer = gpu.types.Buffer('FLOAT', buffer_dimensions, preview.image_pixels_float[:])
    preview_texture = gpu.types.GPUTexture((preview_with, preview_height), data=preview_buffer)

    # Load the overlay image to the GPU
    overlay_image = bpy.data.images.load(str(overlay_image_path))
    overlay_texture = gpu.texture.from_image(overlay_image)

    with preview_overlay_render.bind():
        fb = gpu.state.active_framebuffer_get()
        gpu.matrix.load_matrix(Matrix.Identity(4))
        gpu.matrix.load_projection_matrix(Matrix.Identity(4))
        shader = gpu.shader.from_builtin('IMAGE')
        # gpu.state.depth_mask_set(False)
        gpu.state.blend_set('ALPHA')
        batch = batch_for_shader(
            shader, 'TRI_FAN',
            {
                "pos": ((-1, -1), (1, -1), (1, 1), (-1, 1)),
                "texCoord": ((0, 0), (1, 0), (1, 1), (0, 1)),
            },
        )
        shader.uniform_sampler("image", preview_texture)
        batch.draw(shader)
        # Draw the overlay on the top of the preview
        shader.uniform_sampler("image", overlay_texture)
        batch.draw(shader)

        # Read the pixels from the render buffer
        pixelBuffer = fb.read_color(0, 0, preview_with, preview_height, 4, 0, 'FLOAT')
        pixelBuffer.dimensions = buffer_dimensions
        
        # Save the image buffer back to the ID preview
        preview.image_pixels_float.foreach_set(pixelBuffer)

    preview_overlay_render.free()
    bpy.data.images.remove(overlay_image)

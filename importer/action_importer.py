import bpy

IGNORED_ATTRIBUTES = ["co", "co_ui", "select_control_point", "select_left_handle", "select_right_handle"]


def blend_action(
    src_action: bpy.types.Action,
    dst_action: bpy.types.Action,
    src_range: tuple[int, int] = None,
    frame_offset: int = 0,
    included_bones: list[bpy.types.PoseBone] = None,
):    
    def _is_keyframe_in_range(keyframe: bpy.types.Keyframe):
        return src_range is None or src_range[0] <= keyframe.co[0] <= src_range[1]

    for src_fcurve in src_action.fcurves:
        included_bone_names = [bone.name for bone in included_bones]
        match_bone_selection = included_bones is None or bool([bone for bone in included_bone_names if f'"{bone}"' in src_fcurve.data_path])
        if not match_bone_selection:
            continue

        # Ensure fcurve exists in destination action
        dst_fcurve = dst_action.fcurves.find(
            data_path=src_fcurve.data_path,
            index=src_fcurve.array_index,
        )
        if dst_fcurve is None:
            dst_fcurve = dst_action.fcurves.new(
                data_path=src_fcurve.data_path,
                index=src_fcurve.array_index,
            )

        # Tranfert keyframe points attributes
        for src_keyframe in filter(_is_keyframe_in_range, src_fcurve.keyframe_points):
            dst_frame = int(src_keyframe.co[0]) + frame_offset
            dst_keyframe = dst_fcurve.keyframe_points.insert(
                dst_frame,
                src_keyframe.co[1],
                options={"FAST", "REPLACE"},
                keyframe_type = src_keyframe.type
            )
    
            for property in src_keyframe.bl_rna.properties:
                if property.is_readonly or property.identifier in IGNORED_ATTRIBUTES:
                    continue
                
                setattr(
                    dst_keyframe,
                    property.identifier, 
                    getattr(src_keyframe, property.identifier)
                )


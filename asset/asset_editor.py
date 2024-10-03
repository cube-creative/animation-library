import argparse
import logging
import subprocess
import sys
import bpy

logging.basicConfig(level=logging.INFO)


ROOT_FROM_ID_TYPE = {
    'ACTION': 'actions',
}


def _get_extra_args():
    """ Get Blender extra args

    Returns:
        Given the sys.argv as a list of strings, this method returns the
        sublist right after the '--' element (if present, otherwise returns
        an empty list).

    """
    try:
        return sys.argv[sys.argv.index('--') + 1:]
    except ValueError as e:
        return list()


def _parse_args():
    """ Parse blender launch arguments

    Returns:
        Returns a dict containing the generate render flags given from the command line 
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--asset-id-type",
        help="Asset type to edit within the blender file",
        type=str,
        choices=ROOT_FROM_ID_TYPE.keys(),
        required=True
    )

    parser.add_argument(
        "--asset-name",
        help="Asset name to edit within the blender file",
        type=str,
        required=True
    )

    parser.add_argument(
        "--property",
        help="Asset property path and value to edit within the blender file",
        type=str,
        action='append',
        nargs=2,
        metavar=('path','value')
    )
    args, _ = parser.parse_known_args(_get_extra_args())
    return args


def _set_property(
        root,
        property_path: str,
        property_value: str
):
    path_elems = property_path.split('.')
    edited_prop = root.path_resolve(path_elems[0])
    if len(path_elems) == 1:
        if isinstance(edited_prop, (int, float, str, bool)):
            logging.info(f"Setting property {property_path} to {property_value}")
            setattr(root, property_path, property_value)
        elif isinstance(edited_prop, bpy.types.bpy_prop_collection):
            for item in edited_prop:
                edited_prop.remove(item)
            for value in property_value.split(','):
                edited_prop.new(value)
            logging.info(f"Setting property {property_path} to {property_value}")
        else:
            logging.warning(f"Property {property_path} type not supported for editing.")
    else:
        subpath = '.'.join(path_elems[1:])
        _set_property(
            edited_prop,
            subpath,
            property_value
        )


def set_local_asset_property(
        asset_name: str,
        id_type: str,
        property_path: str,
        property_value: str
    ):
    """ Set a local asset property

    Args:
        asset_name (str): Asset name to edit within the blender file
        id_type (str): Asset type to edit within the blender file
        property_path (str): Asset property path to edit within the blender file
        property_value (str): Asset property value to edit within the blender file
    """
    id_root = getattr(bpy.data, ROOT_FROM_ID_TYPE.get(id_type, None))
    if id_root is None:
        logging.error(f"Asset type {id_type} not supported for editing.")
        return
    asset_databkock = id_root.get(asset_name)
    _set_property(
        asset_databkock,
        property_path,
        property_value
    )


def set_local_asset_properties(
        asset_name: str,
        id_type: str,
        properties: list[tuple[str, str]]
    ):
    """ Set a local asset properties

    Args:
        asset_name (str): Asset name to edit within the blender file
        id_type (str): Asset type to edit within the blender file
        properties (list[tuple[str, str]]): Asset properties to edit within the blender file
    """
    for property_path, property_value in properties:
        set_local_asset_property(
            asset_name=asset_name,
            id_type=id_type,
            property_path=property_path,
            property_value=property_value
        )


def set_shared_asset_properties(
        asset_filepath: str,
        asset_name: str,
        id_type: str,
        properties: list[tuple[str, str]]
    ):
    """ Set a shared asset properties

    Args:
        asset_filepath (str): Asset filepath to edit
        asset_name (str): Asset name to edit within the blender file
        id_type (str): Asset type to edit within the blender file
        properties (list[tuple[str, str]]): Asset properties to edit within the blender file
    """
    args = [
        bpy.app.binary_path,
        asset_filepath,
        "--factory-startup",
        "--background",
        "--python", f"{__file__}",
        "--",
        "--asset-id-type", id_type,
        "--asset-name", asset_name,
    ]

    for property_path, property_value in properties:
        args.extend(["--property", property_path, property_value])
    
    logging.info(f"Running command: {' '.join(args)}")

    return subprocess.run(
        args
    )

if __name__ == "__main__":
    editing_args = _parse_args()

    for property_path, property_value in editing_args.property:
        set_local_asset_property(
            asset_name=editing_args.asset_name,
            id_type=editing_args.asset_id_type,
            property_path=property_path,
            property_value=property_value
        )

    bpy.ops.wm.save_mainfile()

    sys.exit(0)
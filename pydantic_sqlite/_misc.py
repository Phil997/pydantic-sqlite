import os
from typing import Any, get_args


def get_unique_filename(filename: str) -> str:
    """
    Generate a unique filename by appending a counter if the file already exists.

    Args:
        filename (str): The desired filename.

    Returns:
        str: A unique filename that does not exist in the current directory.
    """
    name, ext = os.path.splitext(filename)
    counter = 1
    unique_filename = filename
    while os.path.exists(unique_filename):
        unique_filename = f"{name}({counter}){ext}"
        counter += 1
    return unique_filename


def convert_value_into_union_types(union_type: Any, value: Any) -> Any:
    """
    Attempt to convert a value to one of the types in a Union type.

    Args:
        union_type (Any): The Union type to attempt conversion to.
        value (Any): The value to convert.

    Returns:
        Any: The value converted to the first matching type in the Union.
    """
    if type(None) in get_args(union_type) and value is None:
        return None
    for t in get_args(union_type):
        try:
            return t(value)
        except Exception:
            continue
    return value

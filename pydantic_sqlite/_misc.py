import os
from typing import Any, get_args


def get_unique_filename(filename: str):
    name, ending = os.path.splitext(filename)
    counter = 1

    while os.path.exists(filename):
        filename = f"{name}({str(counter)}){ending}"
        counter += 1

    return filename


def convert_value_into_union_types(union_type, value: Any) -> Any:
    if type(None) in get_args(union_type) and value is None:
        return None
    for t in get_args(union_type):
        try:
            return t(value)
        except Exception:
            ...
    return value

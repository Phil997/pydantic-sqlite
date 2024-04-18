import os
from typing import Any, get_args


def uniquify(path):
    filename, extension = os.path.splitext(path)
    counter = 1

    while os.path.exists(path):
        path = filename + "_(" + str(counter) + ")" + extension
        counter += 1

    return path


def convert_value_into_union_types(union_type, value: Any) -> Any:
    if type(None) in get_args(union_type) and value is None:
        return None
    for t in get_args(union_type):
        try:
            return t(value)
        except Exception:
            ...
    return value

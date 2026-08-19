import json


def row_foreign_ids(row: dict, column: str) -> list[str]:
    """
    Returns the referenced foreign row ids of the given column.
    List values are stored as JSON text and get parsed; dict values store the
    foreign ids as the dict values and only those are returned.

    Args:
        row (dict): The row data as a dictionary.
        column (str): The name of the foreign key column.

    Returns:
        list[str]: The referenced foreign row ids.
    """
    value = row.get(column)
    if value is None:
        return []
    if isinstance(value, str) and (value.startswith("[") or value.startswith("{")):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return list(parsed.values())
        return parsed
    return [value]

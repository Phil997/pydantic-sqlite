
class ModelLoadError(Exception):
    """
    Raised when a stored model class cannot be resolved from the metadata.

    This happens when the metadata references a module or class that is not
    importable and has not been registered in the in-process model registry.
    """

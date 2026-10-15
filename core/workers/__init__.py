__all__ = ["FileWorker"]


def __getattr__(name):
    if name == "FileWorker":
        from .file_worker import FileWorker

        return FileWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

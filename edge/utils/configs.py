from watchdog.events import FileSystemEvent, FileSystemEventHandler


class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, on_modified: any, on_deleted: any) -> None:
        self._on_modified = on_modified
        self._on_deleted = on_deleted
        return

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._on_modified is not None:
            self._on_modified(event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._on_deleted is not None:
            self._on_deleted(event.src_path)

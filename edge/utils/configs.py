from watchdog.events import FileSystemEvent, FileSystemEventHandler
from typing import Any, List
import shlex


class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, on_modified: any) -> None:
        self._on_modified = on_modified
        return

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if self._on_modified is not None:
            self._on_modified(event.src_path)
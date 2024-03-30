import logging
import os
import threading
from collections import deque
from typing import Deque


class LogPipe(threading.Thread):
    def __init__(self, log_name: str):
        threading.Thread.__init__(self)
        self.logger = logging.getLogger(log_name)
        self.level = logging.WARNING
        self.deque: Deque[str] = deque(maxlen=1000)
        self.fd_read, self.fd_write = os.pipe()
        self.pipe_reader = os.fdopen(self.fd_read)
        self.start()

    def fileno(self) -> int:
        return self.fd_write

    def run(self) -> None:
        for line in iter(self.pipe_reader.readline, ''):
            self.deque.append(line)
        self.pipe_reader.close()

    def dump(self) -> None:
        while len(self.deque) > 0:
            self.logger.log(self.level, self.deque.popleft())

    def close(self) -> None:
        os.close(self.fd_write)

from collections import deque
from multiprocessing import shared_memory
from typing import Any

import numpy as np


class SharedMemoryFrameManager:
    def __init__(self) -> None:
        self.shm_store = {}
        self.closed = deque()
        self.closed_count = 0
        self.stopped = False

    def create(self, name: str, size) -> Any:
        if self.stopped:
            return None
        shm = shared_memory.SharedMemory(name=name, create=True, size=size)
        self.shm_store[name] = shm
        return shm.buf

    def get(self, name: str, shape):
        if name not in self.shm_store:
            shm = shared_memory.SharedMemory(name=name)
            self.shm_store[name] = shm
        else:
            shm = self.shm_store[name]
        return np.ndarray(shape=shape, dtype=np.uint8, buffer=shm.buf)

    def close(self, name: str):
        if name in self.shm_store:
            shm: shared_memory.SharedMemory = self.shm_store[name]
            shm.close()
            del self.shm_store[name]

    def delete(self, name: str):
        if name in self.shm_store:
            shm: shared_memory.SharedMemory = self.shm_store[name]
            shm.close()
            shm.unlink()
            del self.shm_store[name]

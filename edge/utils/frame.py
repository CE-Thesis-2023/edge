from abc import ABC, abstractmethod
from typing import AnyStr
from multiprocessing import shared_memory
from loguru import logger
import numpy as np


class FrameManager(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def create(self, name: str, size) -> AnyStr:
        pass

    @abstractmethod
    def get(self, name: str, shape):
        pass

    @abstractmethod
    def close(self, name: str):
        pass

    @abstractmethod
    def delete(self, name: str):
        pass


class SharedMemoryFrameManager(FrameManager):
    def __init__(self) -> None:
        self.shm_store = {}
        self.stopped = False

    def create(self, name: str, size) -> AnyStr:
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

    # Another process might need the shared memory, use close
    def close(self, name: str):
        if name in self.shm_store:
            shm: shared_memory.SharedMemory = self.shm_store[name]
            shm.close()
            del self.shm_store[name]

    # Delete the shared memory, use delete
    def delete(self, name: str):
        if name in self.shm_store:
            shm: shared_memory.SharedMemory = self.shm_store[name]
            shm.close()
            shm.unlink()
            del self.shm_store[name]

    def clean(self):
        self.stopped = True
        for shm in self.shm_store.values():
            shm.close()
            shm.unlink()
            logger.debug(f"Shared memory {shm.name} unlinked")
        self.shm_store.clear()

from abc import ABC, abstractmethod
from typing import AnyStr
from multiprocessing import shared_memory
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

    def create(self, name: str, size) -> AnyStr:
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
            self.shm_store[name].close()
            del self.shm_store[name]

    # Delete the shared memory, use delete
    def delete(self, name: str):
        if name in self.shm_store:
            self.shm_store[name].close()
            self.shm_store[name].unlink()
            del self.shm_store[name]

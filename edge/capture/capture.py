import multiprocessing as mp
import time
from typing import Dict

import numpy as np
import picologging as logging

from edge.helpers.frame import SharedMemoryFrameManager
from edge.settings import get_ffmpeg_cmd


def run_capture(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    with_settings(
        name=name,
        settings=settings)

    manager = SharedMemoryFrameManager()

    while not stopper.is_set():
        try:
            key = f"{time.time()}"
            frame_queue.put(key,
                            block=False)
            buffer = manager.create(name=key, size=9)
            buffer[:] = np.zeros((3, 3), dtype=np.uint8).tobytes()
            manager.close(name=key)
        except Exception as err:
            logging.error(f"Error putting frame into manager: {err}")
        time.sleep(0.2)
    return


def with_settings(
        name: str,
        settings: Dict):
    source = settings['source']
    ffmpeg_cmd = get_ffmpeg_cmd(source)
    logging.debug(f"Capturer {name}: FFmpeg command: {ffmpeg_cmd}")

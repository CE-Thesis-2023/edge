import multiprocessing as mp
import queue
from typing import Dict

import picologging as logging

from edge.helpers.frame import SharedMemoryFrameManager


def run_process(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
        event_queue: mp.Queue,
):
    with_settings(
        name=name,
        settings=settings,
    )

    manager = SharedMemoryFrameManager()

    detect = settings['detect']
    frame_shape = (detect['width'], detect['height'])

    while not stopper.is_set():
        try:
            key = frame_queue.get(timeout=1, block=False)
            if key is None:
                continue
            value = manager.get(name=key, shape=frame_shape)
            logging.info(f"Processor received value: {value.shape}")
            manager.delete(name=key)
        except queue.Empty:
            continue
        except Exception as err:
            logging.exception(err)
            logging.error(f"Failed to read key and frame from Capturer: {err}")
    return


def with_settings(name: str, settings: Dict):
    detect = settings['detect']
    logging.debug(f"Processor {name}: {detect}")

import picologging as logging
import multiprocessing as mp
import time
from typing import Dict

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

    while not stopper.is_set():
        try:
            key = frame_queue.get(timeout=1, block=False)
            if key is None:
                continue
            value = manager.get(name=key, shape=(3, 3))
            logging.info(f"Processor received value: {value}")

            manager.delete(name=key)
        except Exception as err:
            logging.error(f"Failed to read key and frame from Capturer: {err}")
        time.sleep(0.2)
    return


def with_settings(name: str, settings: Dict):
    detect = settings['detect']
    logging.debug(f"Processor {name}: {detect}")

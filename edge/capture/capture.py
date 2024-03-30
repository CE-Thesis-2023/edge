import multiprocessing as mp
import time
from typing import Dict

import picologging as logging


def run_capture(
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            frame_queue.put("Capture")
            logging.info("Capture")
        except Exception:
            continue
        time.sleep(1)
    return

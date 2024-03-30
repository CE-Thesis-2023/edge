import multiprocessing as mp

import picologging as logging


def run_event_capture(
        stopper: mp.Event,
        event_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            res = event_queue.get(timeout=1)
            logging.info(res)
        except Exception:
            continue
    return

import logging
import multiprocessing as mp


def run_process(
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            res = frame_queue.get(timeout=1, block=False)
            if res is not None:
                logging.debug(res)
        except Exception:
            continue
    return

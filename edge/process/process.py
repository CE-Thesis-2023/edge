import logging
import multiprocessing as mp

from typing import Dict


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
    while not stopper.is_set():
        try:
            res = frame_queue.get(timeout=1, block=False)
            if res is not None:
                logging.debug(res)
            event_queue.put(f"Event {res}")
        except Exception:
            continue
    return


def with_settings(name: str, settings: Dict):
    detect = settings['detect']
    logging.debug(f"Processor {name}: {detect}")

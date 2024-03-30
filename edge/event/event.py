import multiprocessing as mp
from typing import Dict

import picologging as logging


def run_event_capture(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        event_queue: mp.Queue,
):
    with_settings(
        name=name,
        settings=settings,
    )

    while not stopper.is_set():
        try:
            res = event_queue.get(timeout=1)
            logging.info(res)
        except Exception:
            continue
    return


def with_settings(name: str, settings: Dict):
    mqtt = settings.get('mqtt', None)
    if mqtt is None:
        logging.debug(f"Event Capture for {name} is disabled, fallback to Stdout")
    else:
        logging.debug(f"Event Capture {name}: MQTT Settings: {mqtt}")

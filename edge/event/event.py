import multiprocessing as mp


def run_event_capture(
        stopper: mp.Event,
        event_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            event_queue.get(timeout=1)
        except Exception:
            continue
    return

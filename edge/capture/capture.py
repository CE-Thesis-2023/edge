import multiprocessing as mp


def run_capture(
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            frame_queue.put("Capture")
        except Exception:
            continue
    return

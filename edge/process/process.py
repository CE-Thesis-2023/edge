import multiprocessing as mp


def run_process(
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    while not stopper.is_set():
        try:
            res = frame_queue.get(timeout=1)
            print(res)
        except Exception:
            continue
    return

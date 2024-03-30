import multiprocessing as mp
import signal
import time


def run():
    q = mp.Queue(maxsize=2)
    produser = mp.Process(target=run_produser, args=(q,))
    consumer = mp.Process(target=run_consumer, args=(q,))

    produser.start()
    consumer.start()

    stop = mp.Event()
    signal.signal(signal.SIGINT, lambda *args: stop.set())
    signal.signal(signal.SIGTERM, lambda *args: stop.set())
    while not stop.is_set():
        time.sleep(1)

    produser.join()
    consumer.join()


def run_produser(q):
    stop = mp.Event()
    signal.signal(signal.SIGINT, lambda *args: stop.set())
    signal.signal(signal.SIGTERM, lambda *args: stop.set())
    while not stop.is_set():
        try:
            q.put(1, timeout=1)
        except mp.queues.Full:
            pass
        time.sleep(1)
    print("Stop producer")


def run_consumer(q):
    stop = mp.Event()
    signal.signal(signal.SIGINT, lambda *args: stop.set())
    signal.signal(signal.SIGTERM, lambda *args: stop.set())
    while not stop.is_set():
        try:
            res = q.get(timeout=1)
            print(res)
        except mp.queues.Empty:
            pass
        time.sleep(1)
    print("Stop consumer")


if __name__ == "__main__":
    run()

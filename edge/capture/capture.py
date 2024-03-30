import multiprocessing as mp
import queue
import subprocess as sp
import threading
import time
from typing import Dict, Tuple

import picologging as logging

from edge.capture.ffmpeg import start_or_restart_ffmpeg
from edge.helpers.fps import FPS
from edge.helpers.frame import SharedMemoryFrameManager
from edge.helpers.log_pipe import LogPipe
from edge.settings import get_ffmpeg_cmd, get_frame_size_fps


def run_capture(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    with_settings(
        name=name,
        settings=settings)
    provider = VideoStreamProvider(
        name=name,
        settings=settings,
        frame_queue=frame_queue,
        event=stopper,
    )
    provider.start()
    if provider.is_alive():
        provider.join()
    logging.debug(f"{name} Capturer stopped")
    return


def with_settings(
        name: str,
        settings: Dict):
    source = settings['source']
    ffmpeg_cmd = get_ffmpeg_cmd(source)
    logging.debug(f"Capturer {name}: FFmpeg command: {ffmpeg_cmd}")


class VideoStreamProvider(threading.Thread):
    def __init__(self,
                 name: str,
                 settings: Dict,
                 event: mp.Event,
                 frame_queue: mp.Queue):
        threading.Thread.__init__(self)
        self.name = name
        self.settings = settings
        self.frame_queue = frame_queue
        self.capturer = None
        self.log_pipe = LogPipe(log_name=f"ffmpeg-{name}.provider")
        specs = get_frame_size_fps(self.settings['detect'])
        self.frame_size = specs[0] * specs[1]
        self.frame_shape = (specs[0], specs[1])
        self.fps = specs[2]
        self.fps_counter = FPS(max_events=100)
        self.manager = SharedMemoryFrameManager()
        self.ffmpeg_pid = None
        self.ffmpeg_proc = None
        self._stopped = event
        return

    def start(self):
        self.start_all()
        self.watch()
        self.stop()
        return

    def watch(self):
        time.sleep(2)
        while not self._stopped.is_set():
            if not self.capturer.is_alive():
                logging.error(f"{self.name} Capturer has stopped")
                self.log_pipe.dump()
                logging.debug(f"{self.name} Restarting Capturer")
                self.start_all()
            time.sleep(2)
        return

    def start_all(self):
        self.start_ffmpeg()
        self.start_capturer()

    def start_ffmpeg(self):
        cmd = get_ffmpeg_cmd(self.settings['source'])
        self.ffmpeg_proc = start_or_restart_ffmpeg(
            ffmpeg_cmd=cmd,
            log_pipe=self.log_pipe,
            frame_size=self.frame_size,
            ffmpeg_process=self.ffmpeg_proc,
        )
        self.ffmpeg_pid = self.ffmpeg_proc.pid
        return

    def start_capturer(self):
        collector = FrameCollector(
            fps=self.fps_counter,
            shape=self.frame_shape,
            frames=self.frame_queue,
            name=self.name,
            manager=self.manager,
            ffmpeg_proc=self.ffmpeg_proc,
            stop_event=self._stopped,
        )
        self.capturer = FrameCollectorThread(collector=collector)
        self.capturer.start()
        return

    def stop(self):
        self.capturer: FrameCollectorThread
        self.log_pipe.close()
        if self.capturer.is_alive():
            self.capturer.join(timeout=30)
        return


class FrameCollector:
    def __init__(self,
                 fps: FPS,
                 ffmpeg_proc: sp.Popen,
                 shape: Tuple[int, int],
                 name: str,
                 frames: mp.Queue,
                 stop_event: mp.Event,
                 manager: SharedMemoryFrameManager):
        self.fps = fps
        self.ffmpeg_proc = ffmpeg_proc
        self.shape = shape
        self.name = name
        self.manager = manager
        self.size = shape[0] * shape[1]
        self.frames = frames
        self._stopped = stop_event
        return

    def run(self):
        logging.debug(f"{self.name} FrameCollector starting")
        self.fps.start()
        while not self._stopped.is_set():
            logging.debug(f"{self.name} FPS: {self.fps.fps()}")
            key = f"{self.name}_{time.time()}"
            buf = self.manager.create(name=key, size=self.size)
            try:
                buf[:] = self.ffmpeg_proc.stdout.read(self.size)
            except Exception as err:
                if self._stopped:
                    logging.debug(f"{self.name} FrameCollector stopping on error and request")
                    break
                logging.exception(err)
                if self.ffmpeg_proc.poll() is not None:
                    logging.error(f"{self.name} FFmpeg process has stopped")
                    break
                continue
            self.fps.update()
            try:
                self.frames.put(key, block=False)
                self.manager.close(name=key)
            except queue.Full:
                logging.error(f"{self.name} FrameCollector queue is full")
                self.manager.delete(name=key)
        logging.debug(f"{self.name} FrameCollector stopped")
        return


class FrameCollectorThread(threading.Thread):
    def __init__(self, collector: FrameCollector):
        threading.Thread.__init__(self)
        self.collector = collector

    def run(self):
        self.collector.run()
        return

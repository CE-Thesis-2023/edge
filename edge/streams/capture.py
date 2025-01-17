from edge.streams.ffmpeg import start_or_restart_ffmpeg, stop_ffmpeg
import signal
from edge.utils.events import EventsPerSecond
from edge.streams.api import StreamProviderAPI
import time
import multiprocessing as mp
from loguru import logger
import multiprocessing as mp
import subprocess as sp
from typing import Tuple
import datetime
import threading
from edge.config import CameraConfig

from edge.utils.frame import FrameManager, SharedMemoryFrameManager
from edge.utils.pipe import LogPipe

import queue


class FrameCollector():
    # Registers the frame in a buffer then reads the output from FFmpeg
    def __init__(self,
                 ffmpeg_process: sp.Popen,
                 source_name: str,
                 frame_shape: Tuple[int, int],
                 frame_queue: mp.Queue,
                 fps: mp.Value,  # shared memory
                 frame_manager: FrameManager,
                 skipped_fps: mp.Value,
                 current_frame: mp.Value,
                 stop_event: mp.Event) -> None:
        self.ffmpeg_process = ffmpeg_process
        self.source_name = source_name
        self.frame_size = frame_shape[0] * frame_shape[1]
        self.frame_queue = frame_queue
        self.fps: mp.Value = fps
        self.skipped_fps: mp.Value = skipped_fps
        self.current_frame: mp.Event = current_frame
        self.stop_event = stop_event
        self.fm: FrameManager = frame_manager
        self.frame_counter = EventsPerSecond(max_events=1000)
        self.skipped_frame_counter = EventsPerSecond(max_events=1000)
        self.fc = 0

    def run(self) -> None:
        logger.info(f"Starting frame collector for {self.source_name}")
        self.frame_counter.start()
        self.skipped_frame_counter.start()
        while not self.stop_event.is_set():
            self.fps.value = self.frame_counter.eps()
            self.skipped_fps.value = self.skipped_frame_counter.eps()
            self.current_frame.value = datetime.datetime.now().timestamp()
            logger.info(f"FPS: {self.fps.value}")
            logger.info(f"Frames: {self.fc}")

            frame_name = f"{self.source_name}{self.current_frame.value}"
            buffer = self.fm.create(name=frame_name, size=self.frame_size)
            try:
                buffer[:] = self.ffmpeg_process.stdout.read(self.frame_size)
            except Exception as e:
                # shutdown has been initiated
                if self.stop_event.is_set():
                    logger.info(
                        f"Frame collector exit requested for source {self.source_name}")
                    break
                logger.error(
                    f"Error reading frame from FFmpeg process for source {self.source_name}: {e}")
                if self.ffmpeg_process.poll() is not None:
                    logger.error(
                        f"FFmpeg process has exited for {self.source_name}")
                    self.fm.delete(name=frame_name)
                    break
                # just a corrupted frame, skip it
                continue
            self.frame_counter.update()
            try:
                self.frame_queue.put(obj=self.current_frame.value, block=False)
                self.fm.close(name=frame_name)
            except queue.Full:
                logger.error(
                    f"Error putting frame in queue for {self.source_name}")
                self.skipped_frame_counter.update()
                self.fm.delete(name=frame_name)
            self.fc += 1
        logger.info(f"Frame collector exited for {self.source_name}")
        return


class FrameCapturer(threading.Thread):
    # Runs the FrameCollector in a separate thread
    def __init__(
            self,
            source_name: str,
            frame_shape: Tuple[int, int],  # (width, height)
            frame_queue: mp.Queue,
            fps: mp.Value,
            ffmpeg_process: sp.Popen,
            skipped_fps: mp.Value,
            stop_event: mp.Event) -> None:
        threading.Thread.__init__(self)
        self.source_name = source_name
        self.frame_shape = frame_shape
        self.frame_queue = frame_queue
        self.fps: mp.Value = fps
        self.fm = SharedMemoryFrameManager()
        self.stop_event = stop_event
        self.ffmpeg_process = ffmpeg_process
        self.current_frame: mp.Value = mp.Value('d', 0.0)
        self.skipped_fps: mp.Value = skipped_fps

    def run(self) -> None:
        c = FrameCollector(
            ffmpeg_process=self.ffmpeg_process,
            source_name=self.source_name,
            frame_shape=self.frame_shape,
            frame_queue=self.frame_queue,
            fps=self.fps,
            frame_manager=self.fm,
            skipped_fps=self.skipped_fps,
            current_frame=self.current_frame,
            stop_event=self.stop_event
        )
        c.run()

    def stop(self) -> None:
        self.fm.clean()
        logger.debug(f"FrameCapturer cleaed its SharedMemoryFrameManager")


class PreRecordedProvider(StreamProviderAPI, threading.Thread):
    # Runs and manages the lifecycle of the FFmpeg process
    # Initialize the Capturer thread
    def __init__(self,
                 source_name: str,
                 camera_fps: mp.Value,
                 skipped_fps: mp.Value,
                 stop_event: mp.Event,
                 ffmpeg_pid: int,
                 configs: CameraConfig,
                 frame_queue: mp.Queue) -> None:
        threading.Thread.__init__(self)
        self.frame_queue = frame_queue
        self.source_name = source_name
        self.camera_fps = camera_fps
        self.skipped_fps = skipped_fps
        self.stop_event = stop_event
        self.capturer_thread = None
        self.ffmpeg_provider_process = None
        self.log_pipe = LogPipe(log_name=f"ffmpeg:{source_name}.provider")
        self.ffmpeg_pid = ffmpeg_pid
        ##################################
        self.frame_shape = configs.frame_shape_yuv
        ##################################
        self.frame_size = self.frame_shape[0] * self.frame_shape[1]
        self.retry_interval = configs.source.ffmpeg.retry_interval
        self.configs = configs

    def run(self) -> None:
        logger.info("PreRecordedProvider: Starting")
        self.start_ffmpeg()

        time.sleep(self.retry_interval)
        while not self.stop_event.wait(timeout=self.retry_interval):
            now = datetime.datetime.now().timestamp()

            if not self.capturer_thread.is_alive():
                self.camera_fps.value = 0
                logger.error(
                    f"Capturer thread has unexpectedly stopped for {self.source_name}")
                logger.error(
                    "Displaying the last 100 lines of the FFmpeg log")
                self.log_pipe.dump()
                logger.info(f"Restarting FFmpeg for {self.source_name}")
                self.start_ffmpeg()
            elif now - self.capturer_thread.current_frame.value > 20:
                self.camera_fps.value = 0
                logger.error(
                    f"Capturer thread has stopped producing frames for 20 seconds for {self.source_name}")
                self.ffmpeg_provider_process.terminate()
                try:
                    logger.info("Waiting for FFmpeg process to finish")
                    self.ffmpeg_provider_process.communicate(timeout=30)
                except sp.TimeoutExpired:
                    logger.info("Timeout expired, killing FFmpeg process")
                    self.ffmpeg_provider_process.kill()
                    self.ffmpeg_provider_process.communicate()
            elif self.camera_fps.value >= 30 + 10:
                self.camera_fps.value = 0
                logger.error(
                    f"Capturer thread is producing more than 40 frames per second for {self.source_name}")
                self.ffmpeg_provider_process.terminate()
                try:
                    logger.info("Waiting for FFmpeg process to finish")
                    self.ffmpeg_provider_process.communicate(timeout=30)
                except sp.TimeoutExpired:
                    logger.info("Timeout expired, killing FFmpeg process")
                    self.ffmpeg_provider_process.kill()
                    self.ffmpeg_provider_process.communicate()
        
        self.stop()

    def start_ffmpeg(self) -> None:
        logger.info(f"Starting FFmpeg for {self.source_name}")
        ffmpeg_cmd = self.configs.ffmpeg_cmd
        self.ffmpeg_provider_process = start_or_restart_ffmpeg(
            ffmpeg_cmd=ffmpeg_cmd,
            logger=logger,
            log_pipe=self.log_pipe,
            frame_size=self.frame_size
        )
        self.ffmpeg_pid = self.ffmpeg_provider_process.pid
        self.capturer_thread = FrameCapturer(
            source_name=self.source_name,
            frame_shape=self.frame_shape,
            frame_queue=self.frame_queue,
            fps=self.camera_fps,
            ffmpeg_process=self.ffmpeg_provider_process,
            skipped_fps=self.skipped_fps,
            stop_event=self.stop_event
        )
        self.capturer_thread.start()
        logger.info(f"Started Capturer thread for {self.source_name}")

    def stop(self) -> None:
        self.capturer_thread.stop()
        while not self.frame_queue.empty():
            self.frame_queue.get()
            logger.info("Emptied frame queue")
        self.log_pipe.close()
        stop_ffmpeg(
            logger=logger,
            ffmpeg_process=self.ffmpeg_provider_process)
        logger.info("PreRecordedProvider stopped")

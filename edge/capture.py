from edge.config import CameraConfig
import multiprocessing as mp
from loguru import logger
import signal
from edge.streams.capture import PreRecordedProvider


def run_capturer(
        name: str,
        config: CameraConfig,
        frame_queue: mp.Queue,
        camera_fps: mp.Value,
        skipped_fps: mp.Value,
        ffmpeg_pid: mp.Value):
    logger.info("Capturer process started")

    exit_signal = mp.Event()

    def on_exit(_, __):
        exit_signal.set()
        logger.info("Capturer process exiting")

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    capturer = PreRecordedProvider(
        source_name=name,
        configs=config,
        stop_event=exit_signal,
        frame_queue=frame_queue,
        camera_fps=camera_fps,
        skipped_fps=skipped_fps,
        ffmpeg_pid=ffmpeg_pid,
    )

    capturer.start()
    capturer.join()

    logger.info("Capturer process exited")

import multiprocessing as mp
import time
from typing import Dict

import picologging as logging

from edge.settings import get_ffmpeg_cmd


def run_capture(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
):
    with_settings(settings)

    while not stopper.is_set():
        try:
            frame_queue.put("Capture")
            logging.info("Capture")
        except Exception:
            continue
        time.sleep(1)
    return


def with_settings(settings: Dict):
    source = settings['source']
    ffmpeg_cmd = get_ffmpeg_cmd(source)
    logging.debug(f"Capturer FFmpeg command: {ffmpeg_cmd}")

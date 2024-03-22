import multiprocessing as mp
import subprocess as sp
from edge.utils.pipe import LogPipe
import logging
from logging import Logger

logger = logging.getLogger(__name__)


def stop_ffmpeg(logger: Logger, ffmpeg_process: sp.Popen):
    logger.info("Stopping ffmpeg process")
    ffmpeg_process.terminate()
    try:
        logger.debug("Waiting for ffmpeg process to finish")
        ffmpeg_process.communicate(timeout=30)
    except sp.TimeoutExpired:
        logger.info("Timeout expired, killing ffmpeg process")
        ffmpeg_process.kill()
        ffmpeg_process.communicate()
    logger.info("FFmpeg process stopped")
    return None


def start_or_restart_ffmpeg(
        ffmpeg_cmd: str,
        logger: Logger,
        log_pipe: LogPipe,
        frame_size=None,
        ffmpeg_process=None):
    if ffmpeg_process is not None:
        ffmpeg_process = stop_ffmpeg(
            logger=logger, ffmpeg_process=ffmpeg_process)

    if frame_size is None:
        # FFmpeg is probably not going to output any frames
        process = sp.Popen(
            ffmpeg_cmd,
            stdout=sp.DEVNULL,
            stderr=log_pipe,
            stdin=sp.DEVNULL,
            start_new_session=True
        )
    else:
        process = sp.Popen(
            ffmpeg_cmd,
            stdout=sp.PIPE,
            stderr=log_pipe,
            stdin=sp.DEVNULL,
            bufsize=frame_size * 10,
            start_new_session=True
        )
    return process
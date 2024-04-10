import subprocess as sp

import picologging as logging


def stop_ffmpeg(ffmpeg_process: sp.Popen):
    logging.info("Stopping FFmpeg process")
    ffmpeg_process.terminate()
    try:
        logging.info("Waiting for FFmpeg process to finish")
        ffmpeg_process.communicate(timeout=5)
    except sp.TimeoutExpired:
        logging.info("Timeout expired, killing FFmpeg process")
        ffmpeg_process.kill()
        ffmpeg_process.communicate()
    logging.info("FFmpeg process stopped")
    return None


def start_or_restart_ffmpeg(
        ffmpeg_cmd: str,
        log_pipe,
        frame_size=None,
        ffmpeg_process=None):
    if ffmpeg_process is not None:
        stop_ffmpeg(ffmpeg_process=ffmpeg_process)
    logging.info(f"Starting FFmpeg with command: {ffmpeg_cmd}")
    args = ffmpeg_cmd.split(' ')
    if frame_size is None:
        process = sp.Popen(
            args,
            stdout=sp.DEVNULL,
            stderr=log_pipe,
            stdin=sp.DEVNULL,
            start_new_session=True
        )
    else:
        process = sp.Popen(
            args,
            stdout=sp.PIPE,
            stderr=log_pipe,
            stdin=sp.DEVNULL,
            bufsize=frame_size * 20,
            start_new_session=True
        )
    return process

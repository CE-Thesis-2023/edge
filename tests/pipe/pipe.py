import ffmpeg
import cv2
import numpy as np

height = 320
width = 480

args = {"rtsp_transport": "tcp", "avoid_negative_ts": "make_zero", "skip_frame": "nokey"}
out = (
    ffmpeg
    .input('rtsp://localhost:8554/debug-stream', **args)
    .output('pipe:', format='rawvideo', pix_fmt='yuv420p', s='{}x{}'.format(width, height), r=5)
    .overwrite_output()
    .run_async(pipe_stdout=True)
)

# loop and read 1 frame at a time, save them to a jpeg at debug/frames/frame_{i}.jpeg

i = 0
while True:
    buf = out.stdout.read(width * height)
    frame = np.frombuffer(buf, np.uint8).reshape([height, width])
    cv2.imwrite('debug/frames/frame_{}.jpeg'.format(i), frame)
    i += 1

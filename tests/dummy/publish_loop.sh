#!/bin/bash

ffmpeg -re -stream_loop -1 -i ../src/static.mp4 -c copy -rtsp_transport tcp -f rtsp rtsp://localhost:8554/debug_stream

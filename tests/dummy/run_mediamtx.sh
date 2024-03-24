#!/bin/bash

docker run --rm -it \
    -e MTX_PROTOCOLS=tcp \
    -e MTX_WEBRTCADDITIONALHOSTS=192.168.x.x \
    -p 8554:8554 \
    -p 1935:1935 \
    -p 8888:8888 \
    -p 8889:8889 \
    -p 8890:8890/udp \
    -p 8189:8189/udp \
    --name debug_source \
    -v $PWD/mediamtx.yml:/mediamtx.yml \
    bluenviron/mediamtx

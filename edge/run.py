from hanging_threads import start_monitoring
from loguru import logger
import os
from edge.streams.capture import run_capturer
from edge.motion.default import DefaultMotionDetector, MotionDetectionProcess, run_motion_detector
import multiprocessing as mp
import signal
import time
import sys
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from edge.utils.configs import ConfigChangeHandler
from edge.config import EdgeConfig

DEFAULT_CONFIG_FILE = "./config.yaml"

start_monitoring(seconds_frozen=10, test_interval=100)


class EdgeProcessor:
    def __init__(self) -> None:
        logger.remove()
        logger.add(sys.stdout, colorize=False)
        return

    def start(self) -> None:
        def on_exit():
            logger.info("EdgeProcessor: Requested exiting")
            self.stop()
            logger.info("EdgeProcessor: Going to sys.exit")
            sys.exit()

        self.configure()

        self.init_observers()
        self.init_signaler(on_exit)

        while not self.is_shutdown():
            self.reload_event.clear()

            self.read_configs()

            self.init_detectors()
            self.init_capturers()

            self.start_capturers()
            self.start_detectors()

            while not self.is_reload():
                time.sleep(2)
            self.reload()

        self.stop_observers()
        logger.info("Edge processor exited")

    def read_configs(self) -> None:
        self.configs = EdgeConfig.parse_file(config_file=DEFAULT_CONFIG_FILE)
        self.capturer_info = dict()

        for name, config in self.configs.cameras.items():
            self.capturer_info[name] = {
                "camera_fps": mp.Value("d", 0.0),
                "skipped_fps": mp.Value("d", 0.0),
                "ffmpeg_pid": mp.Value("i", 0),
                "frame_queue": mp.Queue(maxsize=50),
                "capturer_process": None,
                "camera_config": config,
            }

    def init_observers(self) -> None:
        self.reload_event = mp.Event()

        def on_modified(src_path: str):
            print(f"Config file {src_path} has been modified")
            self.reload_event.set()

        handler = ConfigChangeHandler(
            on_modified=on_modified,
        )

        self.observer = Observer()
        self.observer.schedule(
            event_handler=handler,
            path=DEFAULT_CONFIG_FILE)

    def start_observers(self) -> None:
        self.observer.start()

    def init_signaler(self, handler: any) -> None:
        self.shutdown_event = mp.Event()

        def on_shutdown(_, __):
            self.shutdown_event.set()
            handler()

        signal.signal(signal.SIGINT, on_shutdown)
        signal.signal(signal.SIGTERM, on_shutdown)

    def is_reload(self) -> bool:
        return self.reload_event.is_set()

    def is_shutdown(self) -> bool:
        return self.shutdown_event.is_set()

    def stop_observers(self):
        self.reload_event.clear()
        self.observer.stop()
        self.observer.join()

    def init_detectors(self) -> None:
        # motion = DefaultMotionDetector()
        # self.motion = MotionDetectionProcess(fq=self.capturer_info.[
        #                                      0]["frame_queue"], detector=motion)
        return

    def init_capturers(self) -> None:
        for name, camera in self.configs.cameras.items():
            if not camera.enabled:
                logger.info(f"Camera {name} is disabled, skipping")
                continue
            i = self.capturer_info[name]
            proc = mp.Process(
                target=run_capturer,
                name=f"capturer:{name}",
                args=(name, camera,
                      i["frame_queue"],
                      i["camera_fps"],
                      i["skipped_fps"],
                      i["ffmpeg_pid"])
            )
            proc.daemon = True
            self.capturer_info[name]["capturer_process"] = proc
            logger.info(f"Initialized capturer process {name}")

    def start_capturers(self) -> None:
        for name, info in self.capturer_info.items():
            p = info["capturer_process"]
            p.start()
            logger.info(f"Capturer started for camera {name} PID={p.pid}")

    def stop_capturers(self) -> None:
        for name, info in self.capturer_info.items():
            p = info["capturer_process"]
            p.terminate()
            logger.info(f"Capturer stopped for camera {name} PID={p.pid}")

    def start_detectors(self) -> None:
        # self.motion_proc = mp.Process(
        #     name="edge.MotionDetector",
        #     target=run_motion_detector,
        #     args=(self.motion,))
        # self.motion_proc.start()
        return

    def stop_detectors(self) -> None:
        # self.motion_proc.terminate()
        return

    def reload(self) -> None:
        self.stop_capturers()
        self.stop_detectors()

        self.stop()

    def stop(self) -> None:
        for name, capturer in self.capturer_info.items():
            proc = capturer["capturer_process"]
            q: mp.Queue = capturer["frame_queue"]
            if q is not None:
                while not q.empty():
                    q.get_nowait()
            q.close()
            logger.info(f"EdgeProcessor: Queue for process {name} cleared")
            if proc is not None:
                logger.info(
                    f"EdgeProcessor: Waiting for process {name} to exit")
                proc.join()
            logger.info(f"EdgeProcessor: Capturer process {name} stopped")

    def configure(self) -> None:
        if not os.path.exists(DEFAULT_CONFIG_FILE):
            raise FileNotFoundError(
                f"Config file {DEFAULT_CONFIG_FILE} not found")

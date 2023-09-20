import io, sys
from threading import Condition
from picamera2 import MappedArray, Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import cv2
# from producer_config import config, delivery_report
# from confluent_kafka import Producer
import time


class StreamingOutput(io.BufferedIOBase):

    def __init__(self):
        self.frame = None
        self.ts = None
        self.condition = Condition()

    def write(self, buf, ts=None):
        with self.condition:
            self.frame = buf
            self.ts = int(time.time() * 1000) if ts is None else ts
            self.condition.notify_all()

    def save(self, data):
        # This method will mimic the file write operation
        self.write(data)


class CameraManager:

    def __init__(self, source=None):
        self.picam2 = None
        self.webcam = None
        self.output_high = StreamingOutput()
        self.output_low = StreamingOutput()
        self.webcam_review = io.BytesIO()

        # self.producer = Producer(config)
        self.name = "camera1"
        self.start_time = time.time()
        self.webcam_start_time = time.time()
        self.frame_count = 0
        self.web_frame_count = 0
        self.fps = 0
        self.webcam_fps = 0
        self.source = source if source else 0

    def setup_camera(self, resolution=(640, 360)):
        if not self.picam2:
            self.picam2 = Picamera2(0)
            config = self.picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"},
                                                            lores={"size": resolution, "format": "YUV420"},
                                                            controls={"FrameDurationLimits": (33333, 33333)}
                                                            )
            self.picam2.configure(config)
            self.picam2.start_recording(MJPEGEncoder(), FileOutput(self.output_high))
            self.picam2.start_recording(MJPEGEncoder(), FileOutput(self.output_low), name="lores")
            self.picam2.pre_callback = self.apply_timestamp
            self.picam2.set_controls({"FrameDurationLimits": (33333, 33333)})

    def setup_webcam(self):
        if not self.webcam:
            self.webcam = Picamera2(1)
            # config = self.webcam.create_video_configuration(main={"size": resolution, "format": "MJPEG"})
            config = self.webcam.create_video_configuration(main={"size": (1080, 720), "format": "MJPEG"})
            self.webcam.configure(config)
            self.webcam.start()

    def stop(self):
        if self.picam2:
            self.picam2.stop_recording()
            self.picam2.close()
            self.webcam.stop_recording()
            self.webcam.close()

    def reboot(self):
        self.stop()
        self.setup_camera()
        self.setup_webcam()

    def preview(self):

        # For FPS calculation
        # print(f'720,{self.fps}')

        with self.output_low.condition:
            self.output_low.condition.wait()
            frame = self.output_low.frame

            return frame

    def get_frame(self):
        # For FPS calculation
        # print(f'1080,{self.fps}')

        with self.output_high.condition:
            self.output_high.condition.wait()
            frame = self.output_high.frame
            ts = self.output_high.ts
            # self.send_frame(frame, ts)
            return frame, ts

    def get_webcam_frame(self):
        curr_time = time.time()
        if curr_time - self.webcam_start_time >= 1:
            self.webcam_fps = self.web_frame_count
            self.web_frame_count = 0
            self.webcam_start_time = curr_time
            print(f'720,{self.webcam_fps}')
        else:
            self.web_frame_count += 1
        self.webcam.capture_file(self.webcam_review, format='jpeg')
        self.webcam_review.seek(0)
        cur = self.webcam_review.read()
        self.webcam_review.seek(0)
        self.webcam_review.truncate()
        return cur, int(time.time() * 1000) 


    def fps(self, fps):
        self.picam2.framerate = fps

    def apply_timestamp(self, request):
        timestamp = time.strftime("%Y-%m-%d %X")
        curr_time = time.time()
        if curr_time - self.start_time >= 1:
            self.fps = self.frame_count
            self.frame_count = 0
            self.start_time = curr_time
        else:
            self.frame_count += 1
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(m.array, f"FPS: {self.fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
                        cv2.LINE_AA)
        with MappedArray(request, "lores") as m:
            cv2.putText(m.array, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(m.array, f"FPS: {self.fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
                        cv2.LINE_AA)

    # def send_frame(self, frame, ts):
    #
    #     self.producer.produce(
    #         topic="frames",
    #         key=str.encode(self.name),
    #         value=frame,
    #         on_delivery=delivery_report,
    #         timestamp=ts,
    #     )
    #     self.producer.poll(0)

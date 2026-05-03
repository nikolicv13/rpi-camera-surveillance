#!/usr/bin/env python3
"""MJPEG streaming output buffer"""

import io
import threading

class StreamingOutput(io.BufferedIOBase):
    """Buffer for MJPEG stream"""

    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)

    def get_frame(self):
        with self.condition:
            return self.frame
#!/usr/bin/env python3
"""Camera system management and control"""

import os
import time
import threading
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput

from config import *
from streaming import StreamingOutput
from file_utils import get_organized_path, get_stream_resolution
from video_converter import convert_in_background

from motion_detection import MotionDetector

class CameraSystem:
    """Camera management"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.camera = None
        self.streaming_output = None
        self.jpeg_encoder = None
        
        self.is_recording = False
        self.h264_encoder = None
        self.h264_output = None
        self.current_video_path = None
        self.recording_start_time = None
        
        self._lock = threading.Lock()
        self._initialized = True
        
        self.current_resolution = RESOLUTION       # e.g. (1280, 720)
        self.current_bitrate = VIDEO_BITRATE
        
        self.is_247_recording_active = False
        self._247_thread = None
        
        # Initialize motion detector
        self.motion_detector = MotionDetector(self, events_folder=EVENTS_FOLDER)
        self.mqtt_handler = None
    
    def initialize(self):
        """Initialize camera"""
        print("[CAMERA] Initializing...")
        
        os.makedirs(SAVE_FOLDER, exist_ok=True)
        os.makedirs(EVENTS_FOLDER, exist_ok=True)
        
        self.camera = Picamera2()
        
        stream_res = get_stream_resolution(self.current_resolution)
        print(f"[CAMERA] Main: {self.current_resolution}, Stream: {stream_res}")

        config = self.camera.create_video_configuration(
            main={"size": self.current_resolution, "format": "RGB888"},
            lores={"size": stream_res, "format": "YUV420"},  # 👈 Use calculated resolution
            encode="lores"
        )
        self.camera.configure(config)
        
        self.streaming_output = StreamingOutput()
        
        self.jpeg_encoder = JpegEncoder(q=JPEG_QUALITY)
        self.h264_encoder = H264Encoder(bitrate=VIDEO_BITRATE)
        
        self.camera.start()
        time.sleep(1)
        
        self.camera.start_encoder(
            self.jpeg_encoder,
            FileOutput(self.streaming_output),
            name="lores"
        )
        
        print("[CAMERA] ✓ Streaming active!")
    
    def close(self):
        """Close camera"""
        with self._lock:
            if self.is_recording:
                self._stop_recording_internal()
            
            if self.camera:
                try:
                    self.camera.stop_encoder(self.jpeg_encoder)
                except:
                    pass
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
                self.camera = None
        
        print("[CAMERA] Closed.")
    
    def get_frame(self):
        """Get current frame"""
        if self.streaming_output:
            return self.streaming_output.get_frame()
        return None
    
    def wait_for_frame(self, timeout=5.0):
        """Wait for new frame"""
        if self.streaming_output:
            with self.streaming_output.condition:
                self.streaming_output.condition.wait(timeout=timeout)
                return self.streaming_output.frame
        return None
    
    def take_snapshot(self):
        """Take a snapshot"""
        with self._lock:
            if not self.camera:
                return None, "Camera not initialized"
            
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"snapshot_{timestamp}.jpg"
                
                filepath = get_organized_path(SAVE_FOLDER, filename)
                
                self.camera.capture_file(filepath)
                
                with open(filepath, 'rb') as f:
                    frame = f.read()
                
                print(f"[CAMERA] 📷 Snapshot: {filename}")
                return frame, filename
                    
            except Exception as e:
                print(f"[CAMERA] Snapshot error: {e}")
                return None, str(e)
    
    def start_recording(self,trigger="manual"):
        """Start recording"""
        
        if trigger == "manual" and self.is_247_recording_active:
            return False, "Cannot start manual recording while 24/7 mode is active."
        
        with self._lock:
            if not self.camera:
                return False, "Camera not initialized"
            
            if self.is_recording:
                return False, "Recording already in progress"
                
                
            
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix="mot" if trigger=="motion" else "rec"
                filename = f"{prefix}_{timestamp}.h264"
                
                self.current_video_path = get_organized_path(SAVE_FOLDER, filename)
                
                self.h264_output = FileOutput(self.current_video_path)
                
                self.camera.start_encoder(
                    self.h264_encoder,
                    self.h264_output,
                    name="main"
                )
                
                self.is_recording = True
                self.recording_start_time = datetime.now()
                
                print(f"[CAMERA] 🔴 Recording: {filename}")
                return True, filename
                
            except Exception as e:
                print(f"[CAMERA] Recording start error: {e}")
                self.is_recording = False
                self.current_video_path = None
                return False, str(e)
    
    def stop_recording(self):
        """Stop recording"""
        with self._lock:
            if self.is_247_recording_active:
                return False, "Cannot manually stop recording during 24/7 mode. Disable 24/7 recording from Settings."
            
            return self._stop_recording_internal()
    
    def _stop_recording_internal(self):
        """Internal stop method"""
        if not self.is_recording:
            return False, "Not recording"
        
        try:
            self.camera.stop_encoder(self.h264_encoder)
            
            filepath = self.current_video_path
            filename = os.path.basename(filepath)
            filesize = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            
            duration = 0
            if self.recording_start_time:
                duration = (datetime.now() - self.recording_start_time).total_seconds()
            
            self.is_recording = False
            self.current_video_path = None
            self.h264_output = None
            self.recording_start_time = None
            
            print(f"[CAMERA] ⏹ Recording stopped: {filename} ({filesize} bytes, {duration:.1f}s)")
            
            convert_in_background(filepath)
            
            return True, {"filename": filename, "size": filesize, "duration": duration}
            
        except Exception as e:
            print(f"[CAMERA] Recording stop error: {e}")
            self.is_recording = False
            return False, str(e)
            
    
    def start_247_recording(self):
        """Starts the 24/7 recording background management thread."""
        with self._lock:
            if self.is_247_recording_active:
                return False, "24/7 recording is already active."

            if self.is_recording:
                # If a manual recording is in progress, stop it first.
                self._stop_recording_internal()
            
            self.is_247_recording_active = True
            self._247_thread = threading.Thread(target=self._247_recording_loop, daemon=True)
            self._247_thread.start()
            
            print("[REC 24/7] ▶️ Mode activated. Starting background manager.")
            # The background thread will handle publishing status via MQTT
            if self.mqtt_handler:
                self.mqtt_handler.publish_status()
                
            return True, "24/7 recording mode activated."

    def stop_247_recording(self):
        """Stops the 24/7 recording mode and the current recording segment."""
        with self._lock:
            if not self.is_247_recording_active:
                return False, "24/7 recording is not active."

            self.is_247_recording_active = False
            print("[REC 24/7] ⏹️ Mode deactivating. The current segment will be stopped.")

            # The loop will naturally exit, and the _stop_recording_internal will be called.
            # We don't need to join the thread because it's a daemon.
            
            if self.mqtt_handler:
                self.mqtt_handler.publish_status()
                
            return True, "24/7 recording mode deactivated."

    def _247_recording_loop(self):
        """The core background loop that manages continuous recording segments."""
        
        # 23 hours, 55 minutes = 86100 seconds
        RECORDING_DURATION_SECONDS = 86100 
        
        while self.is_247_recording_active:
            print("[REC 24/7] Starting new segment...")
            
            # Start a new recording. The 'trigger' helps identify it.
            success, result = self.start_recording(trigger="247")
            
            if not success:
                print("[REC 24/7] ❌ Failed to start new segment. Retrying in 60 seconds...")
                time.sleep(60)
                continue # Try again
            
            # Wait for the recording duration, but check for stop signal every second
            for _ in range(RECORDING_DURATION_SECONDS):
                if not self.is_247_recording_active:
                    break # Exit the wait loop if the mode was disabled
                time.sleep(1)

            # Stop the current recording segment
            print("[REC 24/7] Segment duration reached. Stopping and restarting...")
            self.stop_recording() 
            
            # Small delay to ensure file handles are closed before starting the next one
            time.sleep(5)
            
        # After the loop exits (because is_247_recording_active became false)
        # make sure any final recording is stopped.
        if self.is_recording:
            print("[REC 24/7] Final segment cleanup.")
            self.stop_recording()
            
        print("[REC 24/7] Background manager has stopped.")        
            
    def update_camera_config(self, resolution: str = None, bitrate: int = None):
        """
        Restart the camera encoders with new settings.
        Must stop encoders, reconfigure, then restart them.
        """
        with self._lock:
            if not self.camera:
                return False, "Camera not initialized"

            if self.is_recording:
                return False, "Cannot change config while recording. Stop recording first."

            try:
                print("[CAMERA] 🔄 Updating camera config...")

                # --- Parse new resolution ---
                new_resolution = self.current_resolution
                if resolution:
                    RESOLUTION_MAP = {
                        "480p":  (854, 480),
                        "720p":  (1280, 720),
                        "1080p": (1920, 1080),
                    }
                    if resolution in RESOLUTION_MAP:
                        new_resolution = RESOLUTION_MAP[resolution]
                    else:
                        return False, f"Unknown resolution: {resolution}"

                # --- Parse new bitrate ---
                # App sends bitrate in Kbps (e.g. 8000), camera needs bps (e.g. 8000000)
                new_bitrate = self.current_bitrate
                if bitrate is not None:
                    new_bitrate = int(bitrate) * 1000
                    
                new_stream_res = get_stream_resolution(new_resolution)
                print(f"[CAMERA] New main: {new_resolution}, New stream: {new_stream_res}")    

                # --- Step 1: Stop existing JPEG encoder ---
                print("[CAMERA] Stopping encoders...")
                try:
                    self.camera.stop_encoder(self.jpeg_encoder)
                except Exception as e:
                    print(f"[CAMERA] Warning stopping jpeg encoder: {e}")

                # --- Step 2: Stop the camera ---
                try:
                    self.camera.stop()
                except Exception as e:
                    print(f"[CAMERA] Warning stopping camera: {e}")
                    
                    
                lores_width = min(new_resolution[0], 1280)
                lores_height = min(new_resolution[1], 720)    

                # --- Step 3: Reconfigure with new settings ---
                print(f"[CAMERA] Reconfiguring: {new_resolution}, {new_bitrate}bps")
                config = self.camera.create_video_configuration(
                    main={"size": new_resolution, "format": "RGB888"},
                    lores={"size": new_stream_res, "format": "YUV420"},
                    encode="lores"
                )
                self.camera.configure(config)

                # --- Step 4: Create new encoders with updated settings ---
                self.jpeg_encoder = JpegEncoder(q=JPEG_QUALITY)
                self.h264_encoder = H264Encoder(bitrate=new_bitrate)

                # --- Step 5: Restart camera and encoders ---
                self.camera.start()
                time.sleep(1)  # Give the camera time to warm up

                self.camera.start_encoder(
                    self.jpeg_encoder,
                    FileOutput(self.streaming_output),
                    name="lores"
                )

                # --- Step 6: Save the new values ---
                self.current_resolution = new_resolution
                self.current_bitrate = new_bitrate

                res_str = f"{new_resolution[0]}x{new_resolution[1]}"
                print(f"[CAMERA] ✅ Config updated: {res_str} @ {new_bitrate}bps")
                return True, f"Config updated: {res_str}"

            except Exception as e:
                print(f"[CAMERA] ❌ Config update error: {e}")
                return False, str(e)  
            
    
    def get_status(self):
        """Get camera status"""
        recording_duration = 0
        if self.is_recording and self.recording_start_time:
            recording_duration = (datetime.now() - self.recording_start_time).total_seconds()
            
        res = self.current_resolution
        resolution_str = f"{res[0]}x{res[1]}"    
        
        return {
            "initialized": self.camera is not None,
            "streaming": self.jpeg_encoder is not None,
            "recording": self.is_recording,
            "recording_duration": round(recording_duration, 1),
            "current_video": os.path.basename(self.current_video_path) if self.current_video_path else None,
            "resolution": f"{self.current_resolution[0]}x{self.current_resolution[1]}",
            "motion_detecting": self.motion_detector.state['detecting'],
            "is_247_recording_active": self.is_247_recording_active,
        }

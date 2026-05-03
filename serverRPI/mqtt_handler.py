#!/usr/bin/env python3
"""MQTT communication handler"""

import json
import time
import threading
import paho.mqtt.client as mqtt
from datetime import datetime
from config import *

class MQTTHandler:
    """MQTT communication"""
    
    def __init__(self, camera_system):
        self.camera = camera_system
        self.client = mqtt.Client(client_id=MQTT_CLIENT_ID)
        self.running = False
        
        # Topics for publishing
        self.TOPIC_COMMAND = "camera/command"
        self.TOPIC_STATUS = "camera/status"
        self.TOPIC_SNAPSHOT = "camera/snapshot"
        self.TOPIC_RESPONSE = "camera/response"
        self.TOPIC_HEARTBEAT = "camera/heartbeat"
        self.TOPIC_MOTION = "camera/motion"
        self.TOPIC_RECORDING = "camera/recording"
        self.TOPIC_FILES = "camera/files"
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Connected!")
            client.subscribe(self.TOPIC_COMMAND)
            self.publish_status()
        else:
            print(f"[MQTT] Error: {rc}")
    
    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode('utf-8').strip().lower()
        print(f"[MQTT] Command: {payload}")
        
        if payload == "snapshot":
            self.cmd_snapshot()
        elif payload == "record_start":
            self.cmd_record_start()
        elif payload == "record_stop":
            self.cmd_record_stop()
        elif payload == "motion_start":
            self.cmd_motion_start()
        elif payload == "motion_stop":
            self.cmd_motion_stop()
        elif payload == "status":
            self.cmd_status()
        else:
            self.send_response("error", f"Unknown: {payload}")
    
    def cmd_snapshot(self):
        frame, result = self.camera.take_snapshot()
        if frame:
            self.publish_snapshot_taken(result)
            self.send_response("success", f"Snapshot: {result}")
        else:
            self.send_response("error", result)
    
    def cmd_record_start(self):
        success, result = self.camera.start_recording()
        if success:
            self.publish_recording_started(result)
            self.send_response("success", f"Recording: {result}")
        else:
            self.send_response("error", result)
    
    def cmd_record_stop(self):
        success, result = self.camera.stop_recording()
        if success:
            self.publish_recording_stopped(result)
            self.send_response("success", "Recording stopped", result)
        else:
            self.send_response("error", result)
    
    def cmd_motion_start(self):
        success, msg = self.camera.motion_detector.start()
        self.send_response("success" if success else "error", msg)
        self.publish_status()
    
    def cmd_motion_stop(self):
        success, msg = self.camera.motion_detector.stop()
        self.send_response("success" if success else "error", msg)
        self.publish_status()
    
    def cmd_status(self):
        self.publish_status()
    
    def publish_status(self):
        """Publish current status"""
        status = self.camera.get_status()
        status["timestamp"] = datetime.now().isoformat()
        status["online"] = True
        
        self.client.publish(self.TOPIC_STATUS, json.dumps(status), retain=True, qos=1)
    
    def publish_motion_detected(self, confidence, filename):
        """Publish when motion is detected"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "type": "motion_detected",
            "confidence": confidence,
            "snapshot": filename
        }
        self.client.publish(self.TOPIC_MOTION, json.dumps(payload), qos=1)
        print(f"[MQTT] Published motion alert")
    
    def publish_recording_started(self, filename):
        """Publish when recording starts"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "type": "recording_started",
            "filename": filename
        }
        self.client.publish(self.TOPIC_RECORDING, json.dumps(payload), qos=1)
        self.publish_status()
    
    def publish_recording_stopped(self, data):
        """Publish when recording stops"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "type": "recording_stopped",
            "filename": data.get("filename"),
            "duration": data.get("duration"),
            "size": data.get("size")
        }
        self.client.publish(self.TOPIC_RECORDING, json.dumps(payload), qos=1)
        self.publish_status()
    
    def publish_snapshot_taken(self, filename):
        """Publish when snapshot is taken"""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "type": "snapshot_taken",
            "filename": filename
        }
        self.client.publish(self.TOPIC_SNAPSHOT, json.dumps(payload), qos=1)
    
    def send_response(self, status, message, data=None):
        response = {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "message": message
        }
        if data:
            response["data"] = data
        self.client.publish(self.TOPIC_RESPONSE, json.dumps(response))
    
    def heartbeat_loop(self):
        """Publish heartbeat + status every 30 seconds"""
        counter = 0
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)
            if not self.running:
                break
            counter += 1
            
            payload = {
                "timestamp": datetime.now().isoformat(),
                "counter": counter,
                "recording": self.camera.is_recording
            }
            self.client.publish(self.TOPIC_HEARTBEAT, json.dumps(payload))
            self.publish_status()
    
    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        will = json.dumps({"online": False, "timestamp": datetime.now().isoformat()})
        self.client.will_set(self.TOPIC_STATUS, will, qos=1, retain=True)
        
        self.client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        self.running = True
        
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        self.client.loop_start()
    
    def stop(self):
        self.running = False
        offline = json.dumps({"online": False, "timestamp": datetime.now().isoformat()})
        self.client.publish(self.TOPIC_STATUS, offline, retain=True)
        self.client.loop_stop()
        self.client.disconnect()

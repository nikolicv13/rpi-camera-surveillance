#!/usr/bin/env python3
"""Configuration settings for the camera system"""

# MQTT Settings
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "veljko-camera-main"

# HTTP Settings
HTTP_PORT = 8080

# Camera Settings
RESOLUTION = (1280, 720)
JPEG_QUALITY = 30
VIDEO_BITRATE = 8000000

# Storage Paths
SAVE_FOLDER = "/home/gorannik/veljko-diplomski/recordings"
EVENTS_FOLDER = "/home/gorannik/veljko-diplomski/events"

# System Settings
HEARTBEAT_INTERVAL = 30

# Push Notifications
PUSH_TOKEN_FILE = "/home/gorannik/veljko-diplomski/push_token.json"
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Resolution mapping for streaming
STREAM_RESOLUTION_MAP = {
    (854, 480): (640, 360),
    (1280, 720): (640, 360),
    (1920, 1080): (960, 540),
}
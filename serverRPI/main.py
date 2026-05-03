#!/usr/bin/env python3


import socket
from config import *
from camera_system import CameraSystem
from storage_manager import StorageManager
from mqtt_handler import MQTTHandler
from web_server import ThreadingHTTPServer, WebHandler
from push_notifications import PushNotificationManager
from motion_detection import MotionDetector

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def main():
    print("=" * 60)
    print(" VELJKO CAMERA SYSTEM")
    print("=" * 60)

    ip = get_ip()
    
    camera_system = None
    mqtt_handler = None
    http_server = None
    storage_manager = None

    try:
        # Initialize components
        camera_system = CameraSystem()
        storage_manager = StorageManager(SAVE_FOLDER, camera_system)
        camera_system.initialize()
        
        WebHandler.camera_system = camera_system
        WebHandler.storage_manager = storage_manager
        
        # MQTT
        print("\n[MQTT] Connecting...")
        mqtt_handler = MQTTHandler(camera_system)
        camera_system.mqtt_handler = mqtt_handler
        mqtt_handler.start()
        
        if storage_manager.config['auto_delete_enabled']:
            storage_manager.start()
        
        # HTTP Server
        print(f"[HTTP] Starting on port {HTTP_PORT}...")
        http_server = ThreadingHTTPServer(('0.0.0.0', HTTP_PORT), WebHandler)
        
        print("\n" + "=" * 60)
        print("  ✅ SYSTEM ACTIVE!")
        print("=" * 60)
        print(f"\n  📺 Web UI:      http://{ip}:{HTTP_PORT}")
        print(f"  🎬 Stream:      http://{ip}:{HTTP_PORT}/stream.mjpg")
        print(f"\n  MQTT Commands:")
        print(f"    mosquitto_pub -t 'camera/command' -m 'snapshot'")
        print(f"    mosquitto_pub -t 'camera/command' -m 'motion_start'")
        print(f"\n  Press Ctrl+C to exit")
        print("=" * 60 + "\n")
        
        http_server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n[INFO] Shutting down...")
        
    finally:
        if http_server:
            http_server.shutdown()
        if mqtt_handler:
            mqtt_handler.stop()
        if camera_system:
            camera_system.close()
        
        print("[OK] System stopped.")

if __name__ == "__main__":
    main()

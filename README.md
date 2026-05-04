# Raspberry Pi Camera Surveillance System
>  Developed as a diploma thesis demonstrating full-stack IoT development, real-time communication protocols, and edge computing.

A full-stack IoT camera surveillance system built with Raspberry Pi and React Native, featuring real-time streaming, motion detection, and remote control capabilities.

## Overview

This project implements a complete camera surveillance solution using a Raspberry Pi as the camera server and a React Native mobile application for remote monitoring and control. The system supports live video streaming, motion detection with automatic recording, snapshot capture, and intelligent storage management.

### Key Features

- **Real-time Video Streaming**: Low-latency MJPEG streaming over HTTP
- **Motion Detection**: Motion detection with configurable sensitivity
- **Automatic Recording**: Event-triggered and scheduled recording modes
- **Remote Control**: Full camera control via mobile application
- **Local Notifications**: Real-time alerts for motion events and system status
- **Intelligent Storage**: Automatic cleanup based on time and disk space
- **MQTT Integration**: Real-time bidirectional communication
- **RESTful API**: Comprehensive HTTP API for camera control
- **Organized File Management**: Date-based folder structure for recordings


### Technology Stack

**Backend (Raspberry Pi)**
- Python 3.13
- Picamera2 (camera interface)
- Paho MQTT (real-time messaging)
- OpenCV (motion detection)
- FFmpeg (video processing)
- HTTP server (streaming & API)

**Frontend (Mobile)**
- React Native
- TypeScript
- Expo
- MQTT.js (real-time updates)
- React Native WebView (streaming)

**Communication**
- MQTT (Eclipse Mosquitto)
- RESTful HTTP API
- MJPEG streaming
- WebSocket (notifications)


---

##  Quick Start

> **Prerequisites:** Raspberry Pi 4+ with Camera Module, Node.js 18+, Python 3.11+, Mosquitto MQTT Broker, FFmpeg.

1. **Clone the repository**
   ```bash
   git clone https://github.com/nikolicv13/veljko-camera-system.git
   cd veljko-camera-system
2. **Start the Backend (Raspberry Pi)**
   ```bash
    cd serverRPI

    sudo apt update
    sudo apt install -y python3-pip python3-picamera2 ffmpeg mosquitto mosquitto-clients

     # Enable and start MQTT broker
    sudo systemctl enable mosquitto  
    sudo systemctl start mosquitto
    
    # Install Python dependencies
    python3 -m pip install -r requirements.txt
    
    # Create config file from template 
    cp config.example.py config.py
    
    # Edit configuration (IP, credentials, etc.)
    nano config.py
    
    # Run backend
    python3 main.py
3. **Start the Mobile App**
   ```bash
    cd mobile
    
    npm install
    
    # Set Raspberry Pi IP
    nano src/config.ts
    
    # Start Expo
    npx expo start


## Configuration

  ### Backend
  
  Edit `serverRPI/config.py`:
  
  ```python
  MQTT_BROKER = "localhost"      # Use "localhost" if Mosquitto runs on same device
  MQTT_PORT = 1883
  HTTP_PORT = 8080
  
  RESOLUTION = (1280, 720)       # Camera resolution
  VIDEO_BITRATE = 8000000        # Bitrate in bits per second
  
  SAVE_FOLDER = "/home/pi/recordings"  # Folder where videos/snapshots are stored
```

  ### Mobile
  
  Edit `mobile/config.ts`:
  
  ```ts
  export const CAMERA_IP = "192.168.1.100"; // Raspberry Pi IP address
  export const HTTP_PORT = 8080;
  export const MQTT_PORT = 1883;
  ```
  ### ⚠️ Important
  Network: Make sure your phone and Raspberry Pi are on the same Wi-Fi network.

--- 

## API Endpoints

### 📸Camera Control
```bash
POST   /api/snapshot        Capture a snapshot
POST   /api/record/start    Start recording
POST   /api/record/stop     Stop recording
GET    /api/status          Get camera status
```

### 🎯Motion Detection
```bash
POST   /api/motion/start    Enable motion detection
POST   /api/motion/stop     Disable motion detection
POST   /api/motion/config   Update motion settings
```

### 📁File Management
```bash
GET     /api/files/snapshots              List snapshots
GET     /api/files/videos                 List videos
DELETE  /api/files/snapshot/:filename     Delete snapshot
DELETE  /api/files/video/:filename        Delete video
```

### 💾Storage
```bash
GET    /api/storage/status   Get disk usage
POST   /api/storage/config   Update storage settings
```

### 📡MQTT Topics
```bash
camera/command      Commands sent to camera
camera/status       Status updates
camera/motion       Motion detection events
camera/recording    Recording state changes
camera/snapshot     Snapshot events
camera/storage      Storage warnings
camera/heartbeat    Health checks
```

---


## Features

### Motion Detection
+ Sensitivity (0–100%)
+ Minimum detection area (pixel threshold)
+ Cooldown between detections
+ Auto-record on motion

### Storage Management
+ Automatic deletion based on file age
+ Cleanup when disk space is low
+ Configurable retention policies
+ Low storage alerts


### Recording Modes
+ Manual recording (via mobile app)
+ Motion-triggered recording
+ 24/7 continuous recording (segmented)




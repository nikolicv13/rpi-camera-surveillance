#!/usr/bin/env python3
"""Video conversion utilities using ffmpeg"""

import os
import subprocess
import threading

def convert_h264_to_mp4(h264_path, delete_original=True):
    """Convert raw H.264 file to MP4 container using ffmpeg"""
    try:
        mp4_path = h264_path.replace('.h264', '.mp4')
        
        print(f"🔄 Converting: {os.path.basename(h264_path)} → {os.path.basename(mp4_path)}")

        result = subprocess.run(
            [
                'ffmpeg',
                '-framerate', '30',
                '-i', h264_path,
                '-c', 'copy',
                '-movflags', '+faststart',
                '-y',
                mp4_path
            ],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0 and os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 0:
            print(f"✅ Conversion successful: {os.path.basename(mp4_path)}")
            
            if delete_original and os.path.exists(h264_path):
                os.remove(h264_path)
                print(f"🗑️ Deleted original: {os.path.basename(h264_path)}")
            
            return mp4_path
        else:
            print(f"❌ Conversion failed: {result.stderr.strip()}")
            return None

    except Exception as e:
        print(f"❌ Conversion error: {e}")
        return None

def convert_in_background(h264_path, delete_original=True):
    """Run conversion in background thread"""
    thread = threading.Thread(
        target=convert_h264_to_mp4,
        args=(h264_path, delete_original),
        daemon=True
    )
    thread.start()
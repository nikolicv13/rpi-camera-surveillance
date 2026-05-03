#!/usr/bin/env python3
"""HTTP web server and API handlers"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime

from config import *
from file_utils import (
    get_organized_path,
    list_gallery_files,
    find_file_in_gallery,
    cleanup_empty_dirs  
)

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    daemon_threads = True


class WebHandler(BaseHTTPRequestHandler):
    """HTTP request handler"""
    
    camera_system = None
    
    def do_GET(self):
        if self.path == '/':
            self._serve_index()
        elif self.path == '/stream.mjpg':
            self._serve_stream()
        elif self.path == '/api/status':
            self._serve_api_status()
        elif self.path == '/api/files/snapshots':
            self._serve_files_snapshots()
        elif self.path == '/api/files/videos':
            self._serve_files_videos()
        elif self.path.startswith('/api/files/snapshot/'):
            self._serve_single_snapshot()
        elif self.path.startswith('/api/files/video/'):
            self._serve_single_video()
        elif self.path == '/api/motion/config':
            self._serve_motion_config()
        elif self.path == '/api/camera/config':   
            self._serve_camera_config()    
        elif self.path == '/api/storage/status':  
            self._serve_storage_status()          
        elif self.path == '/api/storage/config': 
            self._serve_storage_config()              
        else:
            self._serve_404()
    
    def do_POST(self):
        if self.path == '/api/snapshot':
            self._api_snapshot()
        elif self.path == '/api/record/start':
            self._api_record_start()
        elif self.path == '/api/record/stop':
            self._api_record_stop()
        elif self.path == '/api/motion/start':
            self._api_start_motion()
        elif self.path == '/api/motion/stop':
            self._api_stop_motion()
        elif self.path == '/api/motion/config':
            self._api_update_motion_config()
        elif self.path == '/api/camera/config':   
            self._api_update_camera_config()  
        elif self.path == '/api/push/register':  
            self._api_register_push_token() 
        elif self.path == '/api/recording/247/start': 
            self._api_start_247_recording()           
        elif self.path == '/api/recording/247/stop':  
            self._api_stop_247_recording()     
        elif self.path == '/api/storage/config':  
            self._api_update_storage_config()            
        else:
            self._serve_404()
    
    def do_DELETE(self):
        if self.path.startswith('/api/files/snapshot/'):
            self._api_delete_snapshot()
        elif self.path.startswith('/api/files/video/'):
            self._api_delete_video()
        else:
            self._serve_404()
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def _serve_index(self):
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Veljko Camera System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #1a1a2e; color: white; text-align: center; font-family: sans-serif; }
        img { max-width: 100%; border: 3px solid #4CAF50; border-radius: 10px; }
        button { padding: 12px 20px; background: #4CAF50; color: white; border: none; border-radius: 8px; margin: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>📹 Veljko Camera System</h1>
    <img src="/stream.mjpg" alt="Live Stream">
    <br>
    <button onclick="fetch('/api/snapshot',{method:'POST'}).then(r=>r.json()).then(d=>alert(d.success?'Saved':'Error'))">📷 Snapshot</button>
    <button onclick="fetch(rec?'/api/record/stop':'/api/record/start',{method:'POST'}).then(()=>rec=!rec)" id="recbtn">🔴 Record</button>
    <script>let rec=false;</script>
</body>
</html>"""
        
        content = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)
    
    def _serve_stream(self):
        """MJPEG stream"""
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            while True:
                frame = WebHandler.camera_system.wait_for_frame()
                if frame:
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(frame)}\r\n'.encode())
                    self.wfile.write(b'\r\n')
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
        except:
            pass
    
    def _serve_api_status(self):
        status = WebHandler.camera_system.get_status()
        self._send_json(status)
    
    def _serve_files_snapshots(self):
        """API: List all snapshots organised by date"""
        files = list_gallery_files(
            SAVE_FOLDER,
            extensions=('.jpg', '.jpeg', '.png')
        )
        self._send_json({
            'success': True,
            'files':   files,
            'count':   len(files)
        })


    def _serve_files_videos(self):
        """API: List all videos organised by date"""
        files = list_gallery_files(
            SAVE_FOLDER,
            extensions=('.mp4', '.h264')
        )
        self._send_json({
            'success': True,
            'files':   files,
            'count':   len(files)
        })
    
    
    def _serve_single_snapshot(self):
        """Serve a single snapshot image by filename"""
        filename = os.path.basename(self.path.split('/')[-1])
        filepath = find_file_in_gallery(SAVE_FOLDER, filename)

        if not filepath:
            self.send_response(404)
            self.end_headers()
            return

        try:
            with open(filepath, 'rb') as f:
                file_data = f.read()

            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', len(file_data))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(file_data)
        except Exception:
            self.send_response(500)
            self.end_headers()


    def _serve_single_video(self):
        """Serve a single video file by filename"""
        filename = os.path.basename(self.path.split('/')[-1])
        filepath = find_file_in_gallery(SAVE_FOLDER, filename)

        if not filepath:
            self.send_response(404)
            self.end_headers()
            return

        content_type = 'video/mp4' if filename.endswith('.mp4') else 'video/h264'
        file_size=os.path.getsize(filepath)

        range_header = self.headers.get('Range')
        start = 0
        end = file_size - 1

        if range_header:
            # Range header looks like: "bytes=0-1048575" or "bytes=1048576-"
            try:
                range_spec = range_header.strip().replace('bytes=', '')
                range_start_str, range_end_str = range_spec.split('-')

                start = int(range_start_str) if range_start_str else 0
                end   = int(range_end_str)   if range_end_str   else file_size - 1

                # Clamp end to the actual file size
                end = min(end, file_size - 1)
            except (ValueError, AttributeError):
                # Malformed Range header → send the whole file
                start = 0
                end = file_size - 1

        chunk_size = end - start + 1

        try:
            with open(filepath, 'rb') as f:
                f.seek(start)

                if range_header:
                    # ── Partial Content (seeking) ────────────────────────────
                    self.send_response(206)  # 206 Partial Content
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(chunk_size))
                    self.send_header(
                        'Content-Range',
                        f'bytes {start}-{end}/{file_size}'
                    )
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                else:
                    # ── Full file (first load) ───────────────────────────────
                    self.send_response(200)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(file_size))
                    self.send_header('Accept-Ranges', 'bytes')  # Tell client we support ranges
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()

                # ── Stream in small chunks to avoid RAM issues ───────────────
                BUFFER_SIZE = 256 * 1024  # 256 KB chunks
                bytes_remaining = chunk_size

                while bytes_remaining > 0:
                    read_size = min(BUFFER_SIZE, bytes_remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    try:
                        self.wfile.write(data)
                    except (BrokenPipeError, ConnectionResetError):
                        # Client closed the connection (e.g. exited the modal)
                        # This is normal behaviour, not an error
                        return
                    bytes_remaining -= len(data)

        except OSError as e:
            print(f"[HTTP] Video serve error: {e}")
            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass  # Connection already broken, nothing we can do
            
            
    def _serve_camera_config(self):
        """API: GET current camera config"""
        cam_sys=WebHandler.camera_system
        self._send_json({
            'success': True,
            'config': {
                'resolution': f"{cam_sys.current_resolution[0]}x{cam_sys.current_resolution[1]}",
                'bitrate': WebHandler.camera_system.current_bitrate,
                'jpeg_quality': JPEG_QUALITY,
            }
        })

    def _api_update_camera_config(self):
        """API: POST new camera config"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            success, message = WebHandler.camera_system.update_camera_config(
                resolution=data.get('resolution'),
                bitrate=data.get('bitrate'),
            )

            self._send_json({'success': success, 'message': message})
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)})
    
    def _serve_motion_config(self):
        """API: Get motion config"""
        md = WebHandler.camera_system.motion_detector
        self._send_json({
            'success': True,
            'config': md.config,
            'state': {
                'detecting': md.state['detecting'],
                'last_trigger': md.state['last_trigger_time']
            }
        })
    
    def _api_snapshot(self):
        frame, result = WebHandler.camera_system.take_snapshot()
        if frame:
            self._send_json({"success": True, "filename": result})
        else:
            self._send_json({"success": False, "error": result})
    
    def _api_record_start(self):
        success, result = WebHandler.camera_system.start_recording()
        if success:
            self._send_json({"success": True, "filename": result})
        else:
            self._send_json({"success": False, "error": result})
    
    def _api_record_stop(self):
        success, result = WebHandler.camera_system.stop_recording()
        if success:
            self._send_json({"success": True, "data": result})
        else:
            self._send_json({"success": False, "error": result})
    
    def _api_start_motion(self):
        success, msg = WebHandler.camera_system.motion_detector.start()
        
        if success and WebHandler.camera_system.mqtt_handler:
            WebHandler.camera_system.mqtt_handler.publish_status()
        self._send_json({'success': success, 'message': msg})
    
    def _api_stop_motion(self):
        success, msg = WebHandler.camera_system.motion_detector.stop()

        if success and WebHandler.camera_system.mqtt_handler:
            WebHandler.camera_system.mqtt_handler.publish_status()
        self._send_json({'success': success, 'message': msg})
    
    def _api_update_motion_config(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)
            
            md = WebHandler.camera_system.motion_detector
            md.update_config(**data)
            
            self._send_json({'success': True, 'config': md.config})
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)})
    
    def _api_delete_snapshot(self):
        """DELETE /api/files/snapshot/<filename>"""
        filename = os.path.basename(self.path.split('/')[-1])
        filepath = find_file_in_gallery(SAVE_FOLDER, filename)

        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                # Clean up empty day/month folders
                cleanup_empty_dirs(os.path.dirname(filepath), SAVE_FOLDER)
                self._send_json({'success': True, 'filename': filename})
            except OSError as e:
                self._send_json({'success': False, 'error': str(e)})
        else:
            self._send_json({'success': False, 'error': 'File not found'})


    def _api_delete_video(self):
        """DELETE /api/files/video/<filename>"""
        filename = os.path.basename(self.path.split('/')[-1])
        filepath = find_file_in_gallery(SAVE_FOLDER, filename)

        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
                # Clean up empty day/month folders
                cleanup_empty_dirs(os.path.dirname(filepath), SAVE_FOLDER)
                self._send_json({'success': True, 'filename': filename})
            except OSError as e:
                self._send_json({'success': False, 'error': str(e)})
        else:
            self._send_json({'success': False, 'error': 'File not found'})
    
    def _api_register_push_token(self):
        """API: Register a push notification token from the mobile app."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            token = data.get('token', '').strip()

            if not token:
                self._send_json({'success': False, 'error': 'No token provided'})
                return

            if not token.startswith('ExponentPushToken['):
                self._send_json({'success': False, 'error': 'Invalid token format'})
                return

            # Save the token globally
            push_manager.save_token(token)

            self._send_json({'success': True, 'message': 'Token registered'})

        except Exception as e:
            self._send_json({'success': False, 'error': str(e)})
            
    def _api_start_247_recording(self):
        """API: Start 24/7 recording mode"""
        success, message = WebHandler.camera_system.start_247_recording()
        self._send_json({'success': success, 'message': message})

    def _api_stop_247_recording(self):
        """API: Stop 24/7 recording mode"""
        success, message = WebHandler.camera_system.stop_247_recording()
        self._send_json({'success': success, 'message': message})        
    


    def _serve_storage_status(self):
        """API: GET current disk usage statistics."""
        status = WebHandler.storage_manager.get_status()
        self._send_json({'success': True, 'status': status})

    def _serve_storage_config(self):
        """API: GET current storage management config."""
        config = WebHandler.storage_manager.config
        self._send_json({'success': True, 'config': config})

    def _api_update_storage_config(self):
        """API: POST new storage management config."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(body)

            # Update the config in the storage manager
            new_config = WebHandler.storage_manager.update_config(**data)
            
            self._send_json({'success': True, 'config': new_config})
        except Exception as e:
            self._send_json({'success': False, 'error': str(e)})
    
    def _send_json(self, data):
        try:
            content = json.dumps(data).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(content))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(content)
        except:
            pass
    
    def _serve_404(self):
        self.send_response(404)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP logs

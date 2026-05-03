#!/usr/bin/env python3
"""Storage management and cleanup automation"""

import os
import json
import time
import shutil
import threading
from datetime import datetime

class StorageManager:
    """Manages disk space by deleting old files based on configured rules."""
    CONFIG_FILE = "storage_config.json"
    DEFAULT_CONFIG = {
        'auto_delete_enabled': False,
        'max_days': 14,
        'max_gb': 10,
        'check_interval_hours': 6.0, # How often to run the cleanup job 6
        'warning_threshold_pct': 85.0,
    }

    def __init__(self, folder_to_manage,camera_system):
        self.managed_folder = folder_to_manage
        self.config = self.DEFAULT_CONFIG.copy()
        self.camera_system = camera_system
        
        self._thread = None
        self._is_running = False
        self._lock = threading.RLock()

       # self._low_storage_warning_sent = False 
        

    def _load_config(self):
        """Load config from JSON file, or use defaults if file doesn't exist."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(saved)
                    print(f"[STORAGE] Loaded saved config: {config}")
                    return config
        except Exception as e:
            print(f"[STORAGE] Could not load config file: {e}")
        return self.DEFAULT_CONFIG.copy()

    def _save_config(self):
        """Save current config to JSON file so it survives reboots."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"[STORAGE] Could not save config file: {e}")

    def update_config(self, **kwargs):
        """Update storage management configuration."""
        with self._lock:
            for key, value in kwargs.items():
                if key in self.config:
                    try:
                        target_type = type(self.config[key])
                        self.config[key] = target_type(value)
                        print(f"[STORAGE] Config updated: {key} = {self.config[key]}")
                    except (ValueError, TypeError):
                        print(f"[STORAGE] Warning: Could not set {key} to {value}")
            
            # 👇 FIX 3: Save to file immediately upon update
            self._save_config()

            if self.config['auto_delete_enabled'] and not self._is_running:
                self.start()
            elif not self.config['auto_delete_enabled'] and self._is_running:
                self.stop()
        return self.config

    def get_status(self):
        """Get current disk usage statistics."""
        try:
            total, used, free = shutil.disk_usage(self.managed_folder)
            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'used_pct': round((used / total) * 100, 1),
            }
        except FileNotFoundError:
            return { 'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'used_pct': 0 }

    def start(self):
        """Start the background cleanup thread."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self._thread.start()
            print(f"[STORAGE] ▶️ Auto-cleanup manager started.")

    def stop(self):
        """Stop the background cleanup thread."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            print("[STORAGE] ⏹️ Auto-cleanup manager stopped.")

    def _cleanup_loop(self):
        """The core loop that periodically runs the cleanup logic."""
        while self._is_running:
            try:
                print("[STORAGE] 🧹 Running scheduled cleanup...")

                # ─────────────────────────────────────────────────────────────
                # 1. CHECK STORAGE + SEND WARNING VIA MQTT (SVAKI PUT)
                # ─────────────────────────────────────────────────────────────
                try:
                    usage = self.get_status()
                    used_percentage = usage.get('used_pct', 0)
                    free_gb = usage.get('free_gb', 0)
                    
                    #WARNING_THRESHOLD_PCT = 85.0  # Threshold za upozorenje
                    WARNING_THRESHOLD_PCT = self.config.get('warning_threshold_pct', 85.0)
                    # 🔴 UVEK ŠALJI NOTIFIKACIJU ako je usage >= threshold
                    if used_percentage >= WARNING_THRESHOLD_PCT:
                        print(f"[STORAGE] ⚠️ Low storage warning! Usage: {used_percentage}%")
                        
                        if self.camera_system and self.camera_system.mqtt_handler:
                            payload = {
                                "timestamp": datetime.now().isoformat(),
                                "type": "storage_warning",
                                "used_pct": used_percentage,
                                "free_gb": free_gb
                            }
                            info = self.camera_system.mqtt_handler.client.publish(
                                "camera/storage",
                                json.dumps(payload),
                                qos=1,
                                retain=False
                            )
                            print(f"[MQTT] 📡 Published storage warning (rc={info.rc})")

                except Exception as e:
                    print(f"[STORAGE] ❌ Error during notification check: {e}")

                # ─────────────────────────────────────────────────────────────
                # 2. RUN CLEANUP (delete old files)
                # ─────────────────────────────────────────────────────────────
                self._run_cleanup_logic()

            except Exception as e:
                print(f"[STORAGE] ❌ Error during cleanup: {e}")

            # ─────────────────────────────────────────────────────────────
            # 3. WAIT LOOP (safe stop)
            # ─────────────────────────────────────────────────────────────
            wait_seconds = self.config['check_interval_hours'] * 3600

            for _ in range(int(wait_seconds)):
                if not self._is_running:
                    break
                time.sleep(1)

    def _run_cleanup_logic(self):
        """The main logic for finding and deleting files."""
        if not self.config['auto_delete_enabled']:
            return
    
        now = time.time()
        max_days_sec = self.config['max_days'] * 86400
        min_free_gb_bytes = self.config['max_gb'] * (1024**3)

        # --- Rule 1: Delete files older than max_days ---
        files_deleted_by_age = 0
        all_files = self._get_all_files_sorted()
        
        files_to_check = [] 
        for file_path, modified_time in all_files:
            age_seconds = now - modified_time
            if age_seconds > max_days_sec:
                try:
                    os.remove(file_path)
                    files_deleted_by_age += 1
                    print(f"[STORAGE] 🗑️ Deleted old file (age): {os.path.basename(file_path)}")
                except OSError as e:
                    print(f"[STORAGE] ❌ Failed to delete {file_path}: {e}")
            else:
                files_to_check.append((file_path, modified_time))

        if files_deleted_by_age > 0:
            print(f"[STORAGE] ✅ Cleanup (by age) finished. Deleted {files_deleted_by_age} files.")

        # --- Rule 2: Delete oldest files if FREE SPACE is below the threshold ---
        files_deleted_by_size = 0
        try:
            _, _, free_space = shutil.disk_usage(self.managed_folder)
            
            for file_path, _ in files_to_check:
                if free_space > min_free_gb_bytes:
                    break
                
                try:
                    file_size = os.path.getsize(file_path)
                    os.remove(file_path)
                    free_space += file_size 
                    files_deleted_by_size += 1
                    print(f"[STORAGE] 🗑️ Deleted old file (to free space): {os.path.basename(file_path)}")
                except OSError as e:
                    print(f"[STORAGE] ❌ Failed to delete {file_path}: {e}")

        except FileNotFoundError:
            print("[STORAGE] ❌ Could not check disk usage. Path not found.")

        if files_deleted_by_size > 0:
            print(f"[STORAGE] ✅ Cleanup (by size) finished. Deleted {files_deleted_by_size} files.")

    def _get_all_files_sorted(self):
        """Returns a list of all files in the managed folder, sorted from oldest to newest."""
        file_list = []
        for root, _, files in os.walk(self.managed_folder):
            for filename in files:
                if filename.lower().endswith(('.mp4', '.h264', '.jpg')):
                    file_path = os.path.join(root, filename)
                    try:
                        modified_time = os.path.getmtime(file_path)
                        file_list.append((file_path, modified_time))
                    except FileNotFoundError:
                        continue
        file_list.sort(key=lambda x: x[1])
        return file_list

#!/usr/bin/env python3
"""Push notification management via Expo"""

import os
import json
import threading
import urllib.request
from datetime import datetime
from config import PUSH_TOKEN_FILE, EXPO_PUSH_URL

class PushNotificationManager:
    """Sends push notifications to the mobile app via Expo's service."""

    def __init__(self):
        self.token = self._load_token()

    def _load_token(self) -> str | None:
        """Load saved push token and preferences from disk."""
        try:
            if os.path.exists(PUSH_TOKEN_FILE):
                with open(PUSH_TOKEN_FILE, 'r') as f:
                    data = json.load(f)
                    self.preferences = data.get('preferences', {})
                    token = data.get('token')
                    if token:
                        print(f"[PUSH] Loaded token: {token[:20]}...")
                        return token
        except Exception as e:
            print(f"[PUSH] Could not load token: {e}")
        self.preferences = {}
        return None
        
    def send_motion_alert(self, confidence: float, snapshot_filename: str):
        """Send a motion alert only if the user has enabled it."""
        if not self.preferences.get('notifyMotion', True):
            print("[PUSH] Motion notifications disabled by user preference.")
            return

        self.send(
            title="🏃 Motion Detected!",
            body=f"Movement detected at {datetime.now().strftime('%H:%M:%S')}",
            data={
                "type": "motion_detected",
                "confidence": confidence,
                "snapshot": snapshot_filename,
                "timestamp": datetime.now().isoformat(),
            }
        ) 
        
    def send_storage_alert(self, used_pct: float, free_gb: float):
        """Sends a low storage alert ONLY IF the user has enabled it."""
        if not self.preferences.get('notifyStorage', True): # Подразумевано је True
            print("[PUSH] Skipping storage notification (disabled by user).")
            return

        self.send(
            title="⚠️ Low Storage Warning",
            body=f"Disk usage is at {used_pct}%. Only {free_gb:.1f} GB remaining.",
            data={ "type": "storage_alert", "used_pct": used_pct }
        )       

    def save_token(self, token: str, preferences: dict = None):
        """Save push token and preferences to disk."""
        try:
            with open(PUSH_TOKEN_FILE, 'w') as f:
                json.dump({
                    'token': token,
                    'updated': datetime.now().isoformat(),
                    # Store preferences, with safe defaults
                    'preferences': preferences or {
                        'notifyMotion': True,
                        'notifyRecording': False,
                        'notifyStorage': True,
                    }
                }, f)
            self.token = token
            self.preferences = preferences or {}
            print(f"[PUSH] ✅ Token + preferences saved.")
        except Exception as e:
            print(f"[PUSH] Could not save token: {e}")

    def send(self, title: str, body: str, data: dict = None):
        """
        Send a push notification to the registered device.
        This is a fire-and-forget operation run in a background thread.
        """
        if not self.token:
            print("[PUSH] No token registered, skipping notification.")
            return

        thread = threading.Thread(
            target=self._send_internal,
            args=(title, body, data or {}),
            daemon=True,
        )
        thread.start()

    def _send_internal(self, title: str, body: str, data: dict):
        """Internal method that actually makes the HTTP request to Expo."""
        try:
            payload = json.dumps({
                "to": self.token,
                "title": title,
                "body": body,
                "data": data,
                "sound": "default",
                "priority": "high",
                # Android specific
                "channelId": "camera-alerts",
                # Badge count
                "badge": 1,
            }).encode('utf-8')

            req = urllib.request.Request(
                EXPO_PUSH_URL,
                data=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                },
                method='POST',
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))

                # Check if Expo reported an error for this specific token
                if result.get('data', {}).get('status') == 'error':
                    error_msg = result.get('data', {}).get('message', 'Unknown error')
                    print(f"[PUSH] ❌ Expo error: {error_msg}")
                    
                    if 'DeviceNotRegistered' in error_msg:
                        print("[PUSH] Token is no longer valid, clearing.")
                        self.token = None
                else:
                    print(f"[PUSH] ✅ Notification sent: '{title}'")

        except Exception as e:
            print(f"[PUSH] ❌ Failed to send notification: {e}")          

push_manager=PushNotificationManager()

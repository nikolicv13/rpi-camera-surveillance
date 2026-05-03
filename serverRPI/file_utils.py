#!/usr/bin/env python3
"""File organization and gallery management utilities"""

import os
from datetime import datetime

def get_stream_resolution(main_resolution: tuple) -> tuple:
    """Calculate appropriate stream resolution"""
    from config import STREAM_RESOLUTION_MAP
    return STREAM_RESOLUTION_MAP.get(main_resolution, (640, 360))

def get_organized_path(base_folder, filename):
    """Organize files by date into folders"""
    try:
        parts = filename.split('_')
        date_str = parts[1]
        date = datetime.strptime(date_str, "%Y%m%d")
    except (IndexError, ValueError):
        date = datetime.now()

    month_folder = date.strftime("%Y-%m")
    day_folder = date.strftime("%d")
    folder_path = os.path.join(base_folder, month_folder, day_folder)
    os.makedirs(folder_path, exist_ok=True)
    
    return os.path.join(folder_path, filename)

def list_gallery_files(base_folder, extensions):
    """Walk base_folder recursively and return sorted file list"""
    files = []
    if not os.path.exists(base_folder):
        return files

    for root, dirs, filenames in os.walk(base_folder):
        dirs.sort()
        for filename in filenames:
            if filename.lower().endswith(extensions):
                filepath = os.path.join(root, filename)
                try:
                    stat = os.stat(filepath)
                    rel = os.path.relpath(root, base_folder)
                    date_path = rel if rel != '.' else ''

                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created': stat.st_mtime,
                        'date_path': date_path,
                    })
                except OSError:
                    continue

    files.sort(key=lambda f: f['created'], reverse=True)
    return files

def find_file_in_gallery(base_folder, filename):
    """Search for a file anywhere inside base_folder"""
    for root, dirs, files in os.walk(base_folder):
        if filename in files:
            return os.path.join(root, filename)
    return None

def cleanup_empty_dirs(folder, stop_at):
    """Walk upward removing empty directories"""
    folder = os.path.abspath(folder)
    stop_at = os.path.abspath(stop_at)

    while folder != stop_at:
        try:
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
                print(f"[GALLERY] Removed empty folder: {folder}")
            else:
                break
        except OSError:
            break
        folder = os.path.dirname(folder)

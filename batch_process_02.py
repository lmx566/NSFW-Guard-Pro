"""
远程 API 批量图片处理脚本 (Remote API Batch Processing Script)
通过 HTTP API 发送图片到 AI 服务器处理，适用于无 AI 环境的远程服务器。

用法 (Usage):
  python3 batch_process_02.py

依赖 (Requirements):
  pip install requests
"""

import os
import mimetypes
import requests
import time
from pathlib import Path

# --- Configuration ---
API_BASE_URL = "http://205.198.80.58:8000"  # 直接连服务器 IP，不经过 Cloudflare
API_KEY = "NSFW_PRO_8rqNo38SzYgZX86-byPnlZvvXzpiJL5rbE_TYIkbce8"
TARGET_DIR = "02"
MODE = "solid"
COLOR = "#FFC0CB"  # Pink
INTENSITY = 50
MAX_RETRIES = 3

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}

# MIME type mapping for correct Content-Type header
MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
    '.bmp': 'image/bmp',
}


def make_session() -> requests.Session:
    """Creates a session that bypasses all local proxies."""
    session = requests.Session()
    # Completely disable any system/env proxy settings (Clash, VPN, etc.)
    session.trust_env = False
    # Explicitly clear proxies
    session.proxies = {'http': None, 'https': None}
    return session


def process_folder():
    target_path = Path(TARGET_DIR)
    if not target_path.exists():
        print(f"Error: Directory '{TARGET_DIR}' not found.")
        return

    progress_file = "processed.txt"
    processed_files = set()
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as pf:
            processed_files = {line.strip() for line in pf if line.strip()}

    files = sorted([f for f in target_path.iterdir() if f.suffix.lower() in EXTENSIONS])
    # Filter files that are not already processed
    files_to_process = [f for f in files if f.name not in processed_files]
    total_total = len(files)
    total = len(files_to_process)

    if total == 0:
        print(f"All {total_total} images in '{TARGET_DIR}' have already been processed.")
        return

    print(f"Found {total_total} images total. {total} remaining to process.")
    print(f"Server: {API_BASE_URL} | Mode: {MODE}\n")

    session = make_session()
    headers = {'X-API-KEY': API_KEY}

    success_count = 0
    fail_count = 0

    for i, file_path in enumerate(files_to_process, 1):
        filename = file_path.name
        ext = file_path.suffix.lower()
        mime_type = MIME_TYPES.get(ext, 'application/octet-stream')

        print(f"[{i}/{total}] {filename}", end=" ... ", flush=True)

        success = False
        for attempt in range(MAX_RETRIES):
            try:
                # Upload file with correct MIME type
                with open(file_path, 'rb') as f:
                    response = session.post(
                        f"{API_BASE_URL}/api/process",
                        headers=headers,
                        data={'mode': MODE, 'intensity': INTENSITY, 'color': COLOR},
                        files={'file': (filename, f, mime_type)},
                        timeout=120,  # AI processing can take up to 2 minutes
                    )

                if response.status_code == 200:
                    result = response.json()
                    processed_url = result.get('processed_url', '')

                    if not processed_url:
                        raise ValueError("No processed_url in response")

                    # Handle URL that may start with /api/files/...?v=...
                    clean_url = processed_url.split('?')[0]
                    download_url = f"{API_BASE_URL}{clean_url}"

                    img_response = session.get(download_url, timeout=60)
                    img_response.raise_for_status()

                    # Atomically overwrite the original file
                    tmp_path = str(file_path) + ".tmp"
                    with open(tmp_path, 'wb') as out_f:
                        out_f.write(img_response.content)
                    os.replace(tmp_path, str(file_path))

                    # Update progress file
                    with open(progress_file, 'a') as pf:
                        pf.write(filename + "\n")

                    blur = result.get('blur_count', 0)
                    print(f"OK ({blur} areas censored)")
                    success_count += 1
                    success = True
                    break

                elif response.status_code == 403:
                    print(f"\n  [Error 403] Invalid API Key. Check API_KEY in script.")
                    return  # No point retrying auth failures

                elif response.status_code == 413:
                    print(f"\n  [Error 413] File too large (max 10MB), skipping.")
                    fail_count += 1
                    success = True  # skip, not worth retrying
                    break

                else:
                    err = response.text[:200].strip()
                    print(f"\n  [Attempt {attempt+1}] HTTP {response.status_code}: {err}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(3)

            except requests.exceptions.Timeout:
                print(f"\n  [Attempt {attempt+1}] Timeout (server still processing?)")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)

            except requests.exceptions.ConnectionError as e:
                print(f"\n  [Attempt {attempt+1}] Connection error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(5)

            except Exception as e:
                print(f"\n  [Attempt {attempt+1}] Unexpected error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)

        if not success:
            fail_count += 1
            print(f"FAILED after {MAX_RETRIES} attempts.")

        # Brief pause between requests to avoid overwhelming the server
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"Done! Success: {success_count}  Failed: {fail_count}  Total: {total}")
    print(f"{'='*50}")


if __name__ == "__main__":
    process_folder()

import json
import os
import requests
import time
import html
from urllib.parse import urljoin, quote

def download_missing_images():
    report_path = 'audit_report.json'
    images_dir = '/home/khushal/Desktop/Projects/GatePYQ/web/images'
    base_url = 'https://gateoverflow.in/'
    
    if not os.path.exists(report_path):
        print(f"Error: {report_path} not found. Run audit_data.py first.")
        return

    with open(report_path, 'r') as f:
        report = json.load(f)

    missing_images = report.get('details', {}).get('missing_images', [])
    if not missing_images:
        print("No missing images found in report.")
        return

    # Extract unique image sources
    # Format in report: "Post ID: Missing image SRC"
    unique_srcs = set()
    for entry in missing_images:
        if ": Missing image " in entry:
            src = entry.split(": Missing image ")[1]
            unique_srcs.add(src.strip())

    print(f"Found {len(unique_srcs)} unique missing image URLs.")
    
    os.makedirs(images_dir, exist_ok=True)
    
    downloaded = 0
    failed = 0
    
    for src in unique_srcs:
        # Decode HTML entities like &amp; in the URL
        src_clean = html.unescape(src)
        full_url = urljoin(base_url, src_clean)
        filename = os.path.basename(src_clean)
        
        # Clean filename (handle ?qa=blob&... cases)
        if '?' in filename:
            # We keep it as is or simplify it? 
            # The audit script looks for os.path.basename(img_src)
            pass
            
        local_path = os.path.join(images_dir, filename)
        
        if os.path.exists(local_path):
            continue

        try:
            print(f"Downloading: {full_url}")
            # Use a realistic User-Agent to avoid blocks
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(full_url, headers=headers, timeout=15)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                downloaded += 1
            else:
                print(f"Failed to download {full_url}: Status {response.status_code}")
                failed += 1
            
            # Simple rate limiting
            time.sleep(0.2)
        except Exception as e:
            print(f"Error downloading {full_url}: {e}")
            failed += 1

    print(f"\n--- Download Summary ---")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed: {failed}")

if __name__ == "__main__":
    download_missing_images()

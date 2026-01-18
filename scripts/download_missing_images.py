import os
import json
import re
import requests
import time
import sys

def download_missing_images():
    web_dir = "web"
    images_dir = os.path.join(web_dir, "images")
    json_path = "extraction/questions.json"
    
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        
    print(f"Scanning for missing images in {json_path}...")
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("questions.json not found!")
        return

    # Collect all image IDs needed
    needed_blobs = set()
    
    def scan_text(text):
        if not text: return
        # Look for gateoverflow blob IDs (escaped or unescaped)
        # Matches: qa_blobid=12345...
        matches = re.findall(r'qa_blobid=(\d+)', text)
        for m in matches:
            needed_blobs.add(m)
            
    # Traverse the JSON structure
    count = 0
    for subject, tests in data.items():
        for test in tests:
            for section in test.get('sections', []):
                for q in section.get('questions', []):
                    scan_text(q.get('question', ''))
                    scan_text(q.get('solution', ''))
                    scan_text(q.get('text', ''))
                    # Options too if they have images
                    if isinstance(q.get('options'), dict):
                        for opt_val in q['options'].values():
                            scan_text(opt_val)
    
    print(f"Found {len(needed_blobs)} unique image references.")
    
    missing_blobs = []
    for blob_id in needed_blobs:
        filename = f"gateoverflow_blob_{blob_id}.png"
        filepath = os.path.join(images_dir, filename)
        if not os.path.exists(filepath):
            missing_blobs.append(blob_id)
            
    print(f"Identified {len(missing_blobs)} missing images.")
    
    if not missing_blobs:
        print("All images are present locally.")
        return

    # Download missing images
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Download locally missing images
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def download_image(blob_id):
        url = f"https://gateoverflow.in/?qa=blob&qa_blobid={blob_id}"
        filename = f"gateoverflow_blob_{blob_id}.png"
        filepath = os.path.join(images_dir, filename)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception:
            return False

    print(f"Starting parallel download for {len(missing_blobs)} images...")
    
    completed = 0
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_image, blob_id): blob_id for blob_id in missing_blobs}
        
        for future in as_completed(futures):
            completed += 1
            if completed % 10 == 0:
                print(f"Progress: {completed}/{len(missing_blobs)}", end="\r")

    print(f"\nDownload process completed.")

if __name__ == "__main__":
    download_missing_images()

import os
import requests
from bs4 import BeautifulSoup
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script_or_style in soup(["script", "style", "link", "meta"]):
        script_or_style.decompose()
        
    return soup.prettify()

def scrape_and_clean():
    links_file = "question_links.txt"
    raw_dir = "scraped_html/raw"
    cleaned_dir = "scraped_html/cleaned"
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(cleaned_dir, exist_ok=True)
    
    if not os.path.exists(links_file):
        print(f"Error: {links_file} not found.")
        return

    with open(links_file, "r") as f:
        links = [line.strip() for line in f.readlines() if line.strip()]

    to_scrape = links
    total = len(to_scrape)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    def process_url(url, i, total, delay):
        try:
            match = re.search(r'in/(\d+)/', url)
            post_id = match.group(1) if match else f"unknown_{i}"
            raw_path = os.path.join(raw_dir, f"{post_id}.html")
            cleaned_path = os.path.join(cleaned_dir, f"{post_id}.html")
            if os.path.exists(raw_path) and os.path.exists(cleaned_path):
                return "SKIPPED" # Indicate it was skipped, not an error or rate limit
            print(f"[{i+1}/{total}] Scraping {url} (delay: {delay:.2f}s) ...")
            response = requests.get(url, headers=headers)
            if response.status_code == 429:
                print(f"Rate limited (429) for {url}. Increasing delay...")
                time.sleep(30) # Initial wait before returning rate limit status
                return "RATE_LIMIT"
            response.raise_for_status()
            raw_content = response.text
            with open(raw_path, "w", encoding='utf-8') as f:
                f.write(raw_content)
            cleaned_content = clean_html(raw_content)
            with open(cleaned_path, "w", encoding='utf-8') as f:
                f.write(cleaned_content)
            return "SUCCESS"
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
            return "ERROR"

    current_delay = 0
    consecutive_successes = 0
    batch_size = 20
    start = 0
    while start < total:
        batch = to_scrape[start:start+batch_size]
        # Process the current batch, retrying if any rate limit occurs
        while True:
            rate_limit_hit = False
            batch_successes = 0
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                futures = {executor.submit(process_url, url, start + idx, total, current_delay): url for idx, url in enumerate(batch)}
                for future in as_completed(futures):
                    result = future.result()
                    if result == "RATE_LIMIT":
                        rate_limit_hit = True
                    elif result == "SUCCESS":
                        batch_successes += 1
                    # SKIPPED and ERROR do not affect counters
            if rate_limit_hit:
                # Increase delay and retry the same batch
                if current_delay == 0:
                    current_delay = 0.2
                else:
                    current_delay = min(current_delay * 2, 5)
                time.sleep(current_delay)
                # Continue the inner while to retry the batch
                continue
            else:
                # No rate limit, exit retry loop
                break
        # Update counters after successful batch
        consecutive_successes += batch_successes
        if consecutive_successes > 20 and current_delay > 0:
            current_delay = max(0, current_delay - 0.1)
            consecutive_successes = 0
        if current_delay > 0:
            time.sleep(current_delay)
        start += batch_size

if __name__ == "__main__":
    scrape_and_clean()

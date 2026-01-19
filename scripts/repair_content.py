import json
import os
import requests
import time
import re
import html
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

def normalize_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def extract_options_and_clean_html(soup, tags=[]):
    options = {}
    q_view = soup.find("div", class_="qa-q-view-content")
    if not q_view: return {}, ""
    text_div = q_view.find("div", itemprop="text")
    if not text_div: 
        # Fallback: maybe it's just inside q_view without a text div
        text_div = q_view
    
    # Heuristic for MCQ: has 4 options or tagged as MCQ
    is_descriptive = any(t.lower() in ['descriptive', 'numerical', 'nat'] for t in tags)
    
    options_list = text_div.find('ol', style=re.compile(r'list-style-type\s*:\s*upper-alpha', re.I))
    if not options_list:
        potential_lists = text_div.find_all(['ol', 'ul'])
        for plist in potential_lists:
            items = plist.find_all('li')
            if len(items) == 4:
                options_list = plist
                break
    
    # If it's descriptive OR has != 4 items, be careful
    if options_list:
        items = options_list.find_all('li')
        # Check what the question would look like WITHOUT the options list
        # If the remaining part is too small (< 20 chars), it's likely NOT an options list but the main content
        temp_div = BeautifulSoup(str(text_div), 'lxml')
        temp_list = temp_div.find('ol') or temp_div.find('ul')
        if temp_list: temp_list.decompose()
        remaining_text = temp_div.get_text().strip()
        
        if (not is_descriptive or len(items) == 4) and len(remaining_text) > 30:
            labels = ['A', 'B', 'C', 'D', 'E', 'F']
            for i, item in enumerate(items):
                if i < len(labels):
                    options[labels[i]] = "".join([str(x) for x in item.contents]).strip()
            
            # Only decompose if we are fairly sure they are options
            if len(items) >= 4 or not is_descriptive:
                options_list.decompose()
        else:
            # It's probably a numbered sub-question or the main body
            pass

    question_html = "".join([str(x) for x in text_div.contents])
    return options, question_html

def repair_content():
    questions_path = '/home/khushal/Desktop/Projects/GatePYQ/extraction/questions.json'
    base_url = 'https://gateoverflow.in/'
    
    with open(questions_path, 'r') as f:
        data = json.load(f)
        
    targets = []
    # Find targets: missing answer, short text, or recently broken "missing question"
    for subject, subj_data in data.items():
        for test in subj_data:
            for section in test.get('sections', []):
                for q in section.get('questions', []):
                    ans = str(q.get('answer', '')).strip()
                    q_text = str(q.get('question', '')).strip()
                    tags = q.get('tags', [])
                    
                    if not ans or q_text == "" or len(q_text) < 30 or "______" in q_text:
                        targets.append((q.get('post_id'), tags))

    print(f"Total target posts to repair: {len(targets)}")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    repaired_data = {}
    
    def fetch_and_extract(pid, tags):
        url = urljoin(base_url, str(pid))
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                options, question_html = extract_options_and_clean_html(soup, tags)
                
                # Extract solution
                solution_html = ""
                selected_answer = soup.find("article", class_="qa-a-list-item-selected") or soup.find("article", class_="qa-a-list-item")
                if selected_answer:
                    a_content = selected_answer.find("div", class_="qa-a-item-content")
                    if a_content:
                        a_text_div = a_content.find("div", itemprop="text")
                        if a_text_div:
                            solution_html = "".join([str(x) for x in a_text_div.contents])

                # Extract answer label - More robust
                answer_label = ""
                if solution_html:
                    sol_text = normalize_text(BeautifulSoup(solution_html, 'lxml').get_text())
                    # Look for [Aa]nswer is (A), Correct: A, etc.
                    patterns = [
                        r'[Aa]nswer\s*(?:is|:)?\s*\(?([A-D])\)?', 
                        r'[Cc]orrect\s*[Aa]nswer\s*(?:is|:)?\s*(?:\$)?([A-D])(?:\$)?', 
                        r'[Oo]ption\s*(?:is|:)?\s*\(?([A-D])\)?',
                        r'^([A-D])\s*$',  # Just the label
                        r'^Correct\s*Option\s*[:]\s*([A-D])'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, sol_text, re.I)
                        if match: 
                            answer_label = match.group(1).upper()
                            break
                    
                    # If still not found, try common end-of-solution labels
                    if not answer_label:
                        match = re.search(r'Ans[:\s]+([A-D])', sol_text, re.I)
                        if match: answer_label = match.group(1).upper()

                # If question_html is still too short, don't overwrite with it if original was better
                # But here we assume re-scrape gives BEST. 
                # Exception: if it's empty, we failed.
                if not question_html.strip():
                    return pid, None

                return pid, {
                    "question": question_html,
                    "options": options,
                    "answer": answer_label,
                    "solution": solution_html,
                    "text": question_html
                }
        except Exception as e:
            pass
        return pid, None

    max_workers = 10
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_and_extract, pid, tags): pid for pid, tags in targets}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            pid, result = future.result()
            if result:
                repaired_data[pid] = result
            if completed % 20 == 0:
                print(f"Progress: {completed}/{len(targets)} repaired.")

    # Update questions.json
    updated_count = 0
    for subject, subj_data in data.items():
        for test in subj_data:
            for section in test.get('sections', []):
                for q in section.get('questions', []):
                    pid = q.get('post_id')
                    if pid in repaired_data:
                        repair = repaired_data[pid]
                        # Only update fields if they are not significantly worse
                        # e.g. don't overwrite a decent question with empty
                        if repair['question'].strip():
                            q['question'] = repair['question']
                            q['text'] = repair['question']
                        
                        if repair['options']:
                            q['options'] = repair['options']
                        
                        # Update answer even if empty (might have been cleared correctly) 
                        # but usually we want to KEEP old if new is empty? 
                        # No, re-scrape is fresh truth.
                        if repair['answer']:
                            q['answer'] = repair['answer']
                        
                        if repair['solution']:
                            q['solution'] = repair['solution']
                            
                        updated_count += 1

    with open(questions_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print(f"Successfully repaired {updated_count} questions in questions.json.")

if __name__ == "__main__":
    repair_content()

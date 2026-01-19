import json
import os
import requests
import time
import re
from bs4 import BeautifulSoup

def clean_html_for_prompt(html_content):
    if not html_content: return ""
    soup = BeautifulSoup(html_content, 'lxml')
    return soup.get_text(separator=' ').strip()

def repair_answers_ai(api_key):
    questions_path = '/home/khushal/Desktop/Projects/GatePYQ/extraction/questions.json'
    # Using gemini-flash-latest (Stable alias, likely 1.5)
    model = "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    with open(questions_path, 'r') as f:
        data = json.load(f)
        
    targets = []
    for subject, tests in data.items():
        for test in tests:
            for section in test.get('sections', []):
                for q in section.get('questions', []):
                    if not q.get('answer'):
                        targets.append(q)

    print(f"Total targets for AI extraction: {len(targets)}")
    
    batch_size = 20
    repaired_count = 0
    
    for i in range(0, len(targets), batch_size):
        batch = targets[i:i + batch_size]
        
        prompt_items = []
        for q in batch:
            q_text = clean_html_for_prompt(q.get('question', ''))
            sol_text = clean_html_for_prompt(q.get('solution', ''))
            options = q.get('options', {})
            options_str = ", ".join([f"{k}: {v}" for k, v in options.items()])
            
            prompt_items.append({
                "post_id": q['post_id'],
                "question": q_text[:500], # Trucate to save tokens
                "options": options_str,
                "solution": sol_text[:1000]
            })

        prompt = f"""
You are an expert GATE examiner. Extract the final correct answer for each of the following questions.
Return the results in a JSON object where keys are the 'post_id' and values are the final answer string.

Rules:
- If MCQ: Provide exactly the option letter (e.g. "A").
- If NAT: Provide the number or range (e.g. "5.4" or "2 to 4").
- If MSQ: Provide letters separated by comma (e.g. "A,B").
- Keep it concise. No explanation.

Questions:
{json.dumps(prompt_items, indent=2)}
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        # Infinite retry loop as requested
        max_retries = 999999
        retry_count = 0
        success = False
        
        while not success:
            try:
                response = requests.post(url, json=payload, timeout=60)
                if response.status_code == 200:
                    res_json = response.json()
                    content = res_json['candidates'][0]['content']['parts'][0]['text']
                    answers_map = json.loads(content)
                    
                    # Update the original dicts in batch
                    for q in batch:
                        pid = str(q['post_id'])
                        if pid in answers_map:
                            ans = str(answers_map[pid]).strip()
                            if len(ans) < 20: # Sanity check
                                q['answer'] = ans
                                repaired_count += 1
                    
                    print(f"Processed batch {i//batch_size + 1}/{(len(targets)-1)//batch_size + 1}. Total repaired: {repaired_count}")
                    success = True
                elif response.status_code == 429: # Resource Exhausted
                    print(f"Batch {i//batch_size + 1}: Rate limited (429). waiting 120s...")
                    time.sleep(120) 
                else:
                    print(f"Batch {i//batch_size + 1}: Error {response.status_code}. Retrying in 60s...")
                    time.sleep(60)
            except Exception as e:
                print(f"Batch {i//batch_size + 1}: Exception {e}. Retrying in 60s...")
                time.sleep(60)
        
        # Rate limit compliance: Paid tier is much more generous
        # Using 2 second delay
        time.sleep(2)
        
        # Periodic save
        if (i // batch_size) % 5 == 0:
            with open(questions_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    # Final save
    with open(questions_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
        
    print(f"Cleanup complete. Successfully repaired {repaired_count} answers.")

if __name__ == "__main__":
    import sys
    key = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GEMINI_API_KEY')
    if not key:
        print("Please provide GEMINI_API_KEY as an argument or environment variable.")
    else:
        repair_answers_ai(key)

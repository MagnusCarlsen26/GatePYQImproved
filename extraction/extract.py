import os
import json
import re
from bs4 import BeautifulSoup

def normalize_text(text):
    if not text:
        return ""
    # Replace non-breaking spaces and other whitespace with regular space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_data_from_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')

    question_id = os.path.basename(html_path).replace('.html', '')
    
    # Extract Question
    q_view = soup.find('div', class_='qa-part-q-view')
    if not q_view:
        return None

    q_container = q_view.find('div', itemprop='text')
    if not q_container:
        return None

    options = {}
    options_list = q_container.find('ol', style=re.compile(r'list-style-type\s*:\s*upper-alpha', re.I))
    
    if not options_list:
        potential_lists = q_container.find_all(['ol', 'ul'])
        for plist in potential_lists:
            items = plist.find_all('li')
            if len(items) >= 2:
                options_list = plist
                break

    if options_list:
        items = options_list.find_all('li')
        labels = ['A', 'B', 'C', 'D', 'E', 'F']
        for i, item in enumerate(items):
            if i < len(labels):
                options[labels[i]] = item.decode_contents().strip()
        options_list.decompose()

    tags = []
    tag_list = soup.find('ul', class_='qa-q-view-tag-list')
    if tag_list:
        tags = [tag.get_text().strip() for tag in tag_list.find_all('li')]

    answer_key = None
    solution_html = ""
    
    accepted_answer = soup.find('article', class_='qa-a-list-item-selected')
    if not accepted_answer:
        best_label = soup.find('div', class_='qa-a-selected-text')
        if best_label:
            accepted_answer = best_label.find_parent('article')

    if not accepted_answer:
        accepted_answer = soup.find('article', class_='qa-a-list-item')

    if accepted_answer:
        ans_content = accepted_answer.find('div', itemprop='text')
        if ans_content:
            solution_html = ans_content.decode_contents().strip()
            # Normalize solution text for better matching
            ans_text = normalize_text(ans_content.get_text())
            
            patterns = [
                r'[Aa]nswer\s*(?:is|:)?\s*\(?([A-E])\)?',
                r'[Cc]orrect\s*[Aa]nswer\s*(?:is|:)?\s*(?:\$)?([A-E])(?:\$)?',
                r'[Oo]ption\s*(?:is|:)?\s*\(?([A-E])\)?',
                r'<strong>\s*([A-E])\s*<\/strong>',
                r'<b>\s*([A-E])\s*<\/b>',
                r'ans\s*(?:is|:)?\s*([A-E])',
                r'^\s*([A-E])\s*$',
                r'(?:^|\s)\(?([A-E])\)?(?:\s|$|\.)'
            ]
            
            # Search in normalized text and raw HTML
            search_str = normalize_text(solution_html) + "\n" + ans_text
            
            for pattern in patterns:
                matches = re.finditer(pattern, search_str, re.IGNORECASE)
                for match in matches:
                    potential = match.group(1).upper()
                    if potential in ['A', 'B', 'C', 'D', 'E']:
                        answer_key = potential
                        break
                if answer_key:
                    break
            
            # Fallback: match normalized option text
            if not answer_key and options:
                for label, val in options.items():
                    val_soup = BeautifulSoup(val, 'lxml')
                    val_text = normalize_text(val_soup.get_text())
                    if val_text and len(val_text) > 2:
                        # Check if val_text exists in ans_text
                        if val_text.lower() in ans_text.lower():
                            answer_key = label
                            break
                        # Try without "the " prefix
                        if val_text.lower().startswith("the "):
                            stripped_val = val_text[4:].strip()
                            if stripped_val and len(stripped_val) > 2:
                                if stripped_val.lower() in ans_text.lower():
                                    answer_key = label
                                    break
    
    question_html = q_container.decode_contents().strip()

    return {
        "id": question_id,
        "question": question_html,
        "options": options,
        "answer": answer_key,
        "solution": solution_html,
        "tags": tags
    }

def main():
    input_dir = 'scraped_html/cleaned'
    output_file = 'extraction/questions.json'
    
    results = []
    if not os.path.exists(input_dir):
        print(f"Directory {input_dir} not found.")
        return

    files = sorted([f for f in os.listdir(input_dir) if f.endswith('.html')])
    
    print(f"Processing {len(files)} files...")
    
    found_answers = 0
    for filename in files:
        path = os.path.join(input_dir, filename)
        try:
            data = extract_data_from_html(path)
            if data:
                results.append(data)
                if data['answer']:
                    found_answers += 1
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Extraction complete. Saved to {output_file}")
    print(f"Found answers for {found_answers}/{len(results)} questions.")

if __name__ == "__main__":
    main()

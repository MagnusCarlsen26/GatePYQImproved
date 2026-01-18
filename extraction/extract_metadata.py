import os
import json
from bs4 import BeautifulSoup
import re

def get_subject(tags):
    for name in tags:
        name = name.lower().replace('-', ' ')
        tokens = name.split()
        
        if 'theory of computation' in name or 'toc' in tokens: return 'Theory of Computation'
        if 'databases' in name or 'dbms' in tokens: return 'Databases & DBMS'
        if 'c programming' in name or 'programming' in name: return 'Programming & DS'
        if 'data structure' in name or 'ds' in tokens: return 'Programming & DS'
        if 'algorithms' in name or 'algorithm' in name: return 'Algorithms'
        if 'computer networks' in name or 'networks' in name or 'cn' in tokens: return 'Computer Networks'
        if 'compiler design' in name or 'cd' in tokens: return 'Compiler Design'
        if 'co and architecture' in name or 'computer organization' in name or 'coa' in tokens: return 'COA'
        if 'operating system' in name or 'os' in tokens: return 'Operating Systems'
        if 'mixed subjects' in name or 'full length' in name: return 'Mixed Subjects'
        if 'digital logic' in name or 'dl' in tokens: return 'Digital Logic'
        if 'discrete math' in name or 'engineering mathematics' in name or 'math' in name: return 'Mathematics'
        if 'dm' in tokens: return 'Mathematics'
        if 'calculus' in name or 'probability' in name or 'counting' in name or 'combinatorics' in name or 'linear algebra' in name: return 'Mathematics'
        if 'mock' in name: return 'Mock Tests'
        if 'aptitude' in name: return 'General Aptitude'
    return 'Other'

def extract_metadata():
    cleaned_dir = "../scraped_html/cleaned"
    output_file = "questions.json"
    
    if not os.path.exists(cleaned_dir):
        print(f"Error: {cleaned_dir} not found.")
        return

    # Load existing data first
    existing_data = {}
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                # Helper to normalize key search if existing list
                if isinstance(raw_data, list):
                    for item in raw_data:
                        # Use string ID for consistency
                        pid = str(item.get('post_id', item.get('id', ''))) 
                        if pid:
                            existing_data[pid] = item
                else:
                    print(f"Warning: {output_file} format not recognized (not a list). Starting fresh.")
        except Exception as e:
             print(f"Error loading existing data: {e}. Starting fresh.")
    
    files = [f for f in os.listdir(cleaned_dir) if f.endswith(".html")]
    files.sort()
    
    print(f"Found {len(files)} files to process.")

    for filename in files:
        filepath = os.path.join(cleaned_dir, filename)
        post_id = filename.replace(".html", "")
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as e:
            print(f"Error parsing file {filename}: {e}")
            continue
        
        # Extract Tags
        tags = []
        tag_list = soup.find("ul", class_="qa-q-view-tag-list")
        if tag_list:
            for tag_link in tag_list.find("a", class_="qa-tag-link"):
                tags.append(tag_link.get_text(strip=True))
        
        # Determine Subject
        subject = get_subject(tags)
        
        # Determine Subtopics
        subtopics = [t for t in tags]

        # Extract Year and Question Number from Title
        title_tag = soup.find("title")
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        
        year = None
        question_num = None
        
        year_match = re.search(r'\b(19|20)\d{2}\b', title_text)
        if year_match:
            year = int(year_match.group(0))
            
        q_num_match = re.search(r'Question\s*:\s*(\d+)', title_text, re.IGNORECASE)
        if q_num_match:
            question_num = int(q_num_match.group(1))
            
        # Extract Question Body
        question_html = ""
        q_view = soup.find("div", class_="qa-q-view-content")
        if q_view:
            text_div = q_view.find("div", itemprop="text")
            if text_div:
                # Get inner HTML
                question_html = "".join([str(x) for x in text_div.contents])
        
        # Extract Solution/Answer
        solution_html = ""
        # Try to find selected answer first
        selected_answer = soup.find("article", class_="qa-a-list-item-selected")
        if selected_answer:
            a_content = selected_answer.find("div", class_="qa-a-item-content")
            if a_content:
                a_text_div = a_content.find("div", itemprop="text")
                if a_text_div:
                    solution_html = "".join([str(x) for x in a_text_div.contents])
        else:
            # Fallback to first answer if no selected answer
            first_answer = soup.find("article", class_="qa-a-list-item")
            if first_answer:
                 a_content = first_answer.find("div", class_="qa-a-item-content")
                 if a_content:
                    a_text_div = a_content.find("div", itemprop="text")
                    if a_text_div:
                        solution_html = "".join([str(x) for x in a_text_div.contents])
                        
        # Attempt to extract simple answer label (e.g. "A", "B", "C", "D") from solution
        answer_label = ""
        if solution_html:
            # Common pattern: "Answer is (A)" or "Option A"
            # specific pattern seen: Answer is (<strong>D</strong>)
            ans_match = re.search(r'Answer is\s*\(?\s*(?:<strong>)?\s*([A-D])\s*(?:</strong>)?\s*\)?', solution_html, re.IGNORECASE)
            if ans_match:
                answer_label = ans_match.group(1).upper()

        # Update entry in flat dictionary (for internal tracking/updates)
        entry = existing_data.get(post_id, {})
        entry.update({
             "post_id": post_id,
             "title": title_text,
             "subject": subject,
             "subtopics": subtopics,
             "year": year,
             "question_num": question_num,
             "tags": tags,
             "question": question_html,
             "options": {},
             "answer": answer_label,
             "solution": solution_html,
             "text": question_html, # Mapping 'question' to 'text' for target schema
             "award": 1, # Default
             "penalty": "0", # Default
             "global_idx": int(post_id) if post_id.isdigit() else 0 # Use post_id as index
        })
        existing_data[post_id] = entry

    # --- Transformation to Target Schema ---
    final_output = {}
    
    # 1. Group by Subject
    grouped_by_subject = {}
    for pid, q in existing_data.items():
        subj = q.get('subject', 'Other')
        if subj not in grouped_by_subject:
            grouped_by_subject[subj] = []
        grouped_by_subject[subj].append(q)

    # 2. Build Nested Structure
    for subj, questions in grouped_by_subject.items():
        # Create a single "Collected Questions" test for this subject
        # In the future, we could group by Year or Topic to create multiple "tests" per subject.
        
        # Sort questions by Year then Question Number for logical ordering
        questions.sort(key=lambda x: (x.get('year') or 0, x.get('question_num') or 0))
        
        # Assign local_idx
        for i, q in enumerate(questions):
            q['local_idx'] = i + 1
            
        test_structure = {
            "id": f"{subj.replace(' ', '_')}_Collected",
            "display_name": f"{subj} - All Questions",
            "total_qs": str(len(questions)),
            "total_marks": len(questions), # Dummy value
            "syllabus": f"Complete {subj} Syllabus",
            "test_link": "#", # Dummy link
            "sections": [
                {
                    "name": "Technical",
                    "questions": questions
                }
            ]
        }
        
        final_output[subj] = [test_structure]

    # Save consolidated data
    with open(output_file, 'w') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"Successfully consolidated and reformatted metadata for {len(existing_data)} questions to questions.json")

if __name__ == "__main__":
    extract_metadata()

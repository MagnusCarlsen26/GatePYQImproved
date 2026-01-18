import os
import json
from bs4 import BeautifulSoup
import re
from concurrent.futures import ProcessPoolExecutor
import time

def normalize_text(text):
    if not text:
        return ""
    # Replace non-breaking spaces and other whitespace with regular space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_subject(tags, title):
    # 1. Try to get subject from Title Prefix
    if title:
        parts = title.split(':')
        if len(parts) > 1:
            prefix = parts[0].strip().lower()
            if 'theory of computation' in prefix: return 'Theory of Computation'
            if 'databases' in prefix or 'dbms' in prefix: return 'Databases & DBMS'
            if 'programming' in prefix or 'ds' in prefix or 'data structures' in prefix: return 'Programming & DS'
            if 'algorithms' in prefix or 'algorithm' in prefix: return 'Algorithms'
            if 'computer networks' in prefix or 'networks' in prefix: return 'Computer Networks'
            if 'compiler design' in prefix: return 'Compiler Design'
            if 'co & architecture' in prefix or 'computer organization' in prefix: return 'COA'
            if 'operating system' in prefix: return 'Operating Systems'
            if 'digital logic' in prefix: return 'Digital Logic'
            if 'engineering mathematics' in prefix or 'calculus' in prefix or 'linear algebra' in prefix or 'probability' in prefix or 'discrete mathematics' in prefix: return 'Mathematics'
            if 'general aptitude' in prefix: return 'General Aptitude'

    # 2. Fallback to Tags if title fails
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

def split_tags(tags):
    """
    Splits tags into exam_tags (containing year patterns) and topic_tags (subtopics).
    Returns (exam_tags, topic_tags)
    """
    exam_tags = []
    topic_tags = []
    
    # Regex for exam/year tags like gate2022, isro2010, gatecse-2015, etc.
    year_pattern = re.compile(r'^(gate|isro|tifr|net|ugc).*\d{4}.*$', re.IGNORECASE)
    
    for tag in tags:
        if year_pattern.match(tag):
            exam_tags.append(tag)
        else:
            topic_tags.append(tag)
            
    return exam_tags, topic_tags

# Tags to exclude from subtopic consideration (non-topic tags)
EXCLUDED_TAGS = {
    'easy', 'normal', 'hard', 'medium', 'difficult',  # difficulty
    'descriptive', 'numerical-answers', 'multiple-selects', 'true-false', 
    'fill-in-the-blanks', 'match-the-following', 'one-mark', 'two-marks',  # question types
    'Data Structures', 'Algorithms', 'Databases', 'Theory of Computation', 
    'Digital Logic', 'CO & Architecture', 'Computer Networks', 'Compiler Design', 
    'Operating System', 'Programming in C',  # subject names (capitalized)
}

# Priority subtopics - more specific topics that should be preferred
PRIORITY_SUBTOPICS = [
    # Data Structures - specific
    'avl-tree', 'b-tree', 'binary-search-tree', 'binary-tree', 'binary-heap',
    'linked-list', 'stack', 'queue', 'hashing', 'array', 'trie',
    # Algorithms - specific  
    'graph-algorithms', 'minimum-spanning-tree', 'shortest-path', 'graph-search',
    'sorting', 'searching', 'dynamic-programming', 'greedy', 'divide-and-conquer',
    'recurrence-relation', 'time-complexity', 'asymptotic-notations',
    # TOC - specific
    'finite-automata', 'regular-language', 'regular-expression', 'context-free-language',
    'context-free-grammar', 'pushdown-automata', 'turing-machine', 'decidability',
    'minimal-state-automata', 'identify-class-language', 'grammar',
    # Databases - specific
    'sql', 'database-normalization', 'relational-algebra', 'er-diagram',
    'transaction-and-concurrency', 'functional-dependency',
    # OS - specific
    'process-synchronization', 'process-scheduling', 'virtual-memory', 'page-replacement',
    'disk', 'deadlock', 'semaphore', 'memory-management', 'file-system',
    # COA - specific
    'cache-memory', 'pipelining', 'number-representation', 'machine-instruction',
    'interrupts', 'addressing-mode', 'memory-interfacing', 'io-system',
    # Compiler - specific
    'parsing', 'lr-parser', 'runtime-environment', 'syntax-directed-translation',
    'lexical-analysis', 'code-generation', 'code-optimization', 'intermediate-code',
    # Networks - specific
    'tcp', 'ip', 'network-layer', 'data-link-layer', 'application-layer',
    'subnetting', 'routing', 'flow-control', 'error-detection',
    # Digital Logic - specific
    'boolean-algebra', 'k-map', 'circuit-output', 'combinational-circuit',
    'sequential-circuit', 'flip-flop', 'counter', 'number-system',
    # Programming - specific
    'recursion', 'parameter-passing', 'identify-function', 'pointers',
    'loop-invariants', 'output', 'c-programming',
]

# Subject-level fallback tags (lowercase)
SUBJECT_TAGS = {
    'data-structures': 'data-structures',
    'algorithms': 'algorithms', 
    'theory-of-computation': 'theory-of-computation',
    'databases': 'databases',
    'operating-system': 'operating-system',
    'co-and-architecture': 'computer-organization',
    'compiler-design': 'compiler-design',
    'computer-networks': 'computer-networks',
    'digital-logic': 'digital-logic',
    'programming': 'programming',
    'programming-in-c': 'programming',
}

def get_single_subtopic(topic_tags, subject):
    """
    Select a single subtopic from topic_tags and format as gatecse-xxx.
    Priority: Specific topics > Subject-level tags > Subject name
    """
    # Normalize tags to lowercase for matching
    tags_lower = {t.lower(): t for t in topic_tags}
    
    # 1. Try to find a priority (specific) subtopic
    for priority_tag in PRIORITY_SUBTOPICS:
        if priority_tag in tags_lower:
            return priority_tag
    
    # 2. Try subject-level tags
    for tag_key, normalized in SUBJECT_TAGS.items():
        if tag_key in tags_lower:
            return normalized
    
    # 3. Try any remaining non-excluded tag
    for tag in topic_tags:
        tag_lower = tag.lower()
        if tag not in EXCLUDED_TAGS and tag_lower not in EXCLUDED_TAGS:
            # Format as lowercase with hyphens
            formatted = tag_lower.replace(' ', '-').replace('_', '-')
            return formatted
    
    # 4. Fallback to subject
    subject_map = {
        'Programming & DS': 'programming',
        'Operating Systems': 'operating-system',
        'Compiler Design': 'compiler-design',
        'Databases & DBMS': 'databases',
        'Computer Networks': 'computer-networks',
        'Digital Logic': 'digital-logic',
        'COA': 'computer-organization',
        'Algorithms': 'algorithms',
        'Theory of Computation': 'theory-of-computation',
        'Mathematics': 'mathematics',
        'General Aptitude': 'general-aptitude',
    }
    return subject_map.get(subject, 'general')



def extract_options_and_clean_html(soup):
    options = {}
    q_view = soup.find("div", class_="qa-q-view-content")
    if not q_view:
        return {}, ""
    
    text_div = q_view.find("div", itemprop="text")
    if not text_div:
        return {}, ""

    # Strategy: Look for <ol> with uppercase alpha type
    # This works for most GO questions
    options_list = text_div.find('ol', style=re.compile(r'list-style-type\s*:\s*upper-alpha', re.I))
    
    # Fallback strategies if specific style not found
    if not options_list:
        potential_lists = text_div.find_all(['ol', 'ul'])
        for plist in potential_lists:
            items = plist.find_all('li')
            # Heuristic: if list has 4 elements, it's likely options
            if len(items) == 4:
                options_list = plist
                break
    
    if options_list:
        items = options_list.find_all('li')
        labels = ['A', 'B', 'C', 'D', 'E', 'F']
        for i, item in enumerate(items):
            if i < len(labels):
                options[labels[i]] = "".join([str(x) for x in item.contents]).strip()
        
        # Remove the options list from the DOM so it doesn't appear in 'question' text
        options_list.decompose()

    # Get the cleaned HTML
    question_html = "".join([str(x) for x in text_div.contents])
    
    return options, question_html

def process_single_file(filepath):
    """
    Process a single HTML file and return the dictionary entry.
    Returns None if error.
    """
    filename = os.path.basename(filepath)
    post_id = filename.replace(".html", "")
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Use lxml for speed
        soup = BeautifulSoup(html_content, "lxml")
    except Exception as e:
        print(f"Error parsing file {filename}: {e}")
        return None
    
    # Extract Tags
    tags = []
    tag_list = soup.find("ul", class_="qa-q-view-tag-list")
    if tag_list:
        tag_items = tag_list.find_all(["li", "a"]) 
        for item in tag_items:
            if item.name == 'li':
                link = item.find('a')
                if link:
                    tags.append(link.get_text(strip=True))
                else:
                    tags.append(item.get_text(strip=True))
            elif item.name == 'a':
                 tags.append(item.get_text(strip=True))
    
    tags = list(set(tags))

    # Title
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    
    # Clean Title: Remove " | Question: ..." suffix
    if title_text:
        title_text = re.sub(r'\s*\|\s*Question\s*:\s*\d+.*$', '', title_text, flags=re.IGNORECASE).strip()
    
    # Determine Subject
    subject = get_subject(tags, title_text)
    
    # Split Tags into Exam Tags and Topic Tags
    exam_tags, topic_tags = split_tags(tags)
    
    # Get single normalized subtopic
    subtopic = get_single_subtopic(topic_tags, subject)

    # Extract Year and Question Number from Title
    year = None
    question_num = None
    
    year_match = re.search(r'\b(19|20)\d{2}\b', title_text)
    if year_match:
        year = int(year_match.group(0))
        
    q_num_match = re.search(r'Question\s*:\s*(\d+)', title_text, re.IGNORECASE)
    if q_num_match:
        question_num = int(q_num_match.group(1))
        
    # Extract Options and Question Body
    options, question_html = extract_options_and_clean_html(soup)

    # Extract Solution/Answer
    solution_html = ""
    selected_answer = soup.find("article", class_="qa-a-list-item-selected")
    if selected_answer:
        a_content = selected_answer.find("div", class_="qa-a-item-content")
        if a_content:
            a_text_div = a_content.find("div", itemprop="text")
            if a_text_div:
                solution_html = "".join([str(x) for x in a_text_div.contents])
    else:
        first_answer = soup.find("article", class_="qa-a-list-item")
        if first_answer:
             a_content = first_answer.find("div", class_="qa-a-item-content")
             if a_content:
                a_text_div = a_content.find("div", itemprop="text")
                if a_text_div:
                    solution_html = "".join([str(x) for x in a_text_div.contents])
                    
    # Attempt to extract simple answer label
    answer_label = ""
    if solution_html:
        sol_text = normalize_text(BeautifulSoup(solution_html, 'lxml').get_text())
        patterns = [
            r'[Aa]nswer\s*(?:is|:)?\s*\(?([A-D])\)?',
            r'[Cc]orrect\s*[Aa]nswer\s*(?:is|:)?\s*(?:\$)?([A-D])(?:\$)?',
            r'[Oo]ption\s*(?:is|:)?\s*\(?([A-D])\)?',
            r'^\s*([A-D])\s*$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sol_text)
            if match:
                answer_label = match.group(1).upper()
                break
        
        if not answer_label:
             # Look for <strong>A</strong> pattern in raw html
             bold_match = re.search(r'<strong>\s*([A-D])\s*</strong>', solution_html)
             if bold_match:
                 answer_label = bold_match.group(1)

    # Build Entry
    entry = {
         "post_id": post_id,
         "title": title_text,
         "subject": subject,
         "subtopic": subtopic,
         "year": year,
         "question_num": question_num,
         "tags": exam_tags, # Only exam/year related tags
         "question": question_html, # Cleaned html
         "options": options,
         "answer": answer_label,
         "solution": solution_html,
         "text": question_html, 
         "award": 1,
         "penalty": "0",
         "global_idx": int(post_id) if post_id.isdigit() else 0
    }
    return entry

def extract_metadata():
    cleaned_dir = "../scraped_html/cleaned"
    output_file = "questions.json"
    
    if not os.path.exists(cleaned_dir):
        print(f"Error: {cleaned_dir} not found.")
        return

    files = [f for f in os.listdir(cleaned_dir) if f.endswith(".html")]
    files.sort()
    
    print(f"Found {len(files)} files to process.")
    
    all_filepaths = [os.path.join(cleaned_dir, f) for f in files]
    
    consolidated_questions = {}
    stats = {'subjects': {}, 'options_found': 0, 'total': 0}
    
    start_time = time.time()
    
    # Use ProcessPoolExecutor for parallel processing
    # Adjust max_workers based on system, usually cpu_count is good default
    with ProcessPoolExecutor() as executor:
        results = []
        # Submit all tasks
        futures = {executor.submit(process_single_file, fp): fp for fp in all_filepaths}
        
        completed_count = 0
        total_files = len(all_filepaths)
        
        import concurrent.futures
        for future in concurrent.futures.as_completed(futures):
            completed_count += 1
            entry = future.result()
            
            if completed_count % 200 == 0:
                print(f"Processed {completed_count}/{total_files} files...")
            
            if entry:
                consolidated_questions[entry['post_id']] = entry
                
                # Update stats
                subj = entry.get('subject', 'Other')
                stats['subjects'][subj] = stats['subjects'].get(subj, 0) + 1
                if entry.get('options'):
                    stats['options_found'] += 1
                stats['total'] += 1

    end_time = time.time()
    print(f"Processed {stats['total']} questions in {end_time - start_time:.2f} seconds.")

    # --- Transformation to Target Schema ---
    final_output = {}
    
    # 1. Group by Subject
    grouped_by_subject = {}
    for pid, q in consolidated_questions.items():
        subj = q.get('subject', 'Other')
        if subj not in grouped_by_subject:
            grouped_by_subject[subj] = []
        grouped_by_subject[subj].append(q)

    # 2. Build Nested Structure - Group by subtopic within each subject
    for subj, questions in grouped_by_subject.items():
        # Group questions by subtopic
        subtopic_groups = {}
        for q in questions:
            st = q.get('subtopic', 'general')
            if st not in subtopic_groups:
                subtopic_groups[st] = []
            subtopic_groups[st].append(q)
        
        # Build sections for each subtopic
        sections = []
        global_idx = 1
        for subtopic_name in sorted(subtopic_groups.keys()):
            subtopic_qs = subtopic_groups[subtopic_name]
            # Sort questions by Year then Question Number
            subtopic_qs.sort(key=lambda x: (x.get('year') or 9999, x.get('question_num') or 9999))
            
            # Assign local_idx
            for q in subtopic_qs:
                q['local_idx'] = global_idx
                global_idx += 1
            
            sections.append({
                "name": subtopic_name,
                "questions": subtopic_qs
            })
        
        test_structure = {
            "id": f"{subj.replace(' ', '_')}_Collected",
            "display_name": f"{subj} - All Questions",
            "total_qs": str(len(questions)),
            "total_marks": len(questions),
            "syllabus": f"Complete {subj} Syllabus",
            "test_link": "#",
            "sections": sections
        }
        
        final_output[subj] = [test_structure]

    # Save
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=4)
        
    print(f"Options extracted for {stats['options_found']} questions.")
    print("Subject breakdown:")
    for s, c in stats['subjects'].items():
        print(f"  {s}: {c}")
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    extract_metadata()

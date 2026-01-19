import json
import os
import re
import html
from pathlib import Path

def audit_questions():
    questions_path = '/home/khushal/Desktop/Projects/GatePYQ/extraction/questions.json'
    images_dir = '/home/khushal/Desktop/Projects/GatePYQ/web/images'
    
    if not os.path.exists(questions_path):
        print(f"Error: {questions_path} not found.")
        return

    with open(questions_path, 'r') as f:
        data = json.load(f)

    report = {
        "summary": {
            "total_questions": 0,
            "duplicate_post_ids": 0,
            "duplicate_global_indices": 0,
            "missing_fields": 0,
            "empty_answers": 0,
            "inconsistent_choices": 0,
            "missing_images": 0,
            "placeholders": 0
        },
        "details": {
            "duplicates": [],
            "missing_fields": [],
            "inconsistent_answers": [],
            "missing_images": [],
            "placeholders": []
        }
    }

    seen_post_ids = set()
    seen_global_indices = set()
    img_tag_regex = re.compile(r'<img [^>]*src="([^"]+)"')

    for subject, subj_data in data.items():
        for test in subj_data:
            for section in test.get('sections', []):
                for q in section.get('questions', []):
                    report["summary"]["total_questions"] += 1
                    post_id = q.get('post_id')
                    global_idx = q.get('global_idx')

                    # 1. Uniqueness check
                    if post_id in seen_post_ids:
                        report["summary"]["duplicate_post_ids"] += 1
                        report["details"]["duplicates"].append(f"Duplicate post_id: {post_id}")
                    seen_post_ids.add(post_id)

                    if global_idx in seen_global_indices:
                        report["summary"]["duplicate_global_indices"] += 1
                        report["details"]["duplicates"].append(f"Duplicate global_idx: {global_idx}")
                    seen_global_indices.add(global_idx)

                    # 2. Missing fields check
                    required_fields = ['question', 'subject', 'subtopic', 'year']
                    missing = [f for f in required_fields if not q.get(f)]
                    if missing:
                        report["summary"]["missing_fields"] += 1
                        report["details"]["missing_fields"].append(f"Post {post_id} missing: {', '.join(missing)}")

                    # 3. Answer consistency
                    ans = q.get('answer', '')
                    opts = q.get('options', {})
                    if not ans or str(ans).strip() == "":
                        report["summary"]["empty_answers"] += 1
                    elif opts:
                        # If options exist, answer should be in keys
                        if isinstance(opts, dict):
                            valid_keys = set(opts.keys())
                            # Multiple correct answer handling
                            ans_list = [a.strip() for a in str(ans).split(',')]
                            if not all(a in valid_keys for a in ans_list):
                                report["summary"]["inconsistent_choices"] += 1
                                report["details"]["inconsistent_answers"].append(f"Post {post_id}: Answer '{ans}' not in options {list(valid_keys)}")

                    # 4. Placeholder & Quality Check
                    q_text = q.get('question', '')
                    if len(q_text) < 20 or "______" in q_text or "..." in q_text:
                        report["summary"]["placeholders"] += 1
                        report["details"]["placeholders"].append(f"Post {post_id}: Potential placeholder/short text")

                    # 5. Image Integrity
                    all_text = q_text + q.get('solution', '')
                    found_images = img_tag_regex.findall(all_text)
                    for img_src in found_images:
                        # Decode HTML entities like &amp; in the URL before checking file existence
                        img_src_clean = html.unescape(img_src)
                        img_filename = os.path.basename(img_src_clean)
                        local_path = os.path.join(images_dir, img_filename)
                        if not os.path.exists(local_path):
                            report["summary"]["missing_images"] += 1
                            report["details"]["missing_images"].append(f"Post {post_id}: Missing image {img_filename}")

    # Print Summary
    print("\n--- Integrity Audit Summary ---")
    for key, val in report["summary"].items():
        print(f"{key.replace('_', ' ').capitalize()}: {val}")
    
    # Write full report
    with open('audit_report.json', 'w') as f:
        json.dump(report, f, indent=4)
    print("\nFull report saved to audit_report.json")

if __name__ == "__main__":
    audit_questions()

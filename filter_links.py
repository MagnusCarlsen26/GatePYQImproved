import re

def filter_links(input_path, output_path):
    # Pattern: https://gateoverflow.in/[ID]/[SLUG]
    # ID is numeric, SLUG can contain alphanumeric and hyphens
    pattern = re.compile(r'^https://gateoverflow\.in/\d+/[a-zA-Z0-9-]+$')
    
    filtered_links = []
    with open(input_path, 'r') as f:
        for line in f:
            link = line.strip()
            if pattern.match(link):
                filtered_links.append(link)
    
    with open(output_path, 'w') as f:
        for link in filtered_links:
            f.write(link + '\n')
    
    print(f"Filtered {len(filtered_links)} links to {output_path}")

if __name__ == "__main__":
    filter_links("links.txt", "question_links.txt")

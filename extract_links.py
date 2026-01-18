import fitz

def extract_links(pdf_path, output_path):
    links = set()
    doc = fitz.open(pdf_path)
    
    for page in doc:
        for link in page.get_links():
            if 'uri' in link:
                links.add(link['uri'])
    
    with open(output_path, 'w') as f:
        for link in sorted(list(links)):
            f.write(link + '\n')
    
    print(f"Extracted {len(links)} unique links to {output_path}")

if __name__ == "__main__":
    extract_links("volume2.pdf", "links.txt")

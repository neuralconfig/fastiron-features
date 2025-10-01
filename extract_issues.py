#!/usr/bin/env python3
"""
Extract bug fixes and known issues from FastIron release notes PDFs.
"""

import pdfplumber
import json
import re
from pathlib import Path
from collections import defaultdict

def extract_version_from_filename(filename):
    """Extract version number from release notes filename like 'fastiron-08090mc-releasenotes-1.0.pdf'"""
    # Match patterns like: 08090, 08091, 10020b_cd3, 08090mc, 08095pb1, etc.
    match = re.search(r'fastiron-([^-]+)-releasenotes', filename)
    if match:
        version_str = match.group(1)

        # Handle CD releases like "10020b_cd3"
        if '_cd' in version_str:
            parts = version_str.split('_')
            base_version = parts[0]
            cd_suffix = '_' + parts[1]
        else:
            base_version = version_str
            cd_suffix = ''

        # Remove any letter suffix (including multi-letter like "mc", "pb1")
        letter_suffix = ''
        # Find where digits end
        digit_end = 0
        for i, c in enumerate(base_version):
            if c.isdigit():
                digit_end = i + 1
            else:
                break

        if digit_end < len(base_version):
            letter_suffix = base_version[digit_end:]
            base_version = base_version[:digit_end]

        # Convert 08090 to 08.0.90 or 10020 to 10.0.20
        if len(base_version) >= 5 and base_version.isdigit():
            major = str(int(base_version[:2]))  # Remove leading zero
            minor = base_version[2]
            patch = base_version[3:5]
            result = f"{major}.{minor}.{patch}"
            if letter_suffix:
                result += letter_suffix
            result += cd_suffix
            return result

    return None

def clean_text(text):
    """Clean text by removing extra whitespace and newlines"""
    if not text:
        return ""
    # Replace newlines with spaces, collapse multiple spaces
    text = text.replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_issue_block(text, start_idx, issue_id):
    """Parse a single issue block from text starting at start_idx"""
    issue = {
        'id': issue_id,
        'symptom': '',
        'condition': '',
        'workaround': '',
        'recovery': '',
        'probability': '',
        'found_in': [],
        'technology': ''
    }

    # Extract each field using regex patterns
    # Symptom (required)
    symptom_match = re.search(r'Symptom\s+(.+?)(?=Condition|Workaround|Recovery|Probability|Found In|Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if symptom_match:
        issue['symptom'] = clean_text(symptom_match.group(1))

    # Condition
    condition_match = re.search(r'Condition\s+(.+?)(?=Workaround|Recovery|Probability|Found In|Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if condition_match:
        issue['condition'] = clean_text(condition_match.group(1))

    # Workaround
    workaround_match = re.search(r'Workaround\s+(.+?)(?=Recovery|Probability|Found In|Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if workaround_match:
        issue['workaround'] = clean_text(workaround_match.group(1))

    # Recovery
    recovery_match = re.search(r'Recovery\s+(.+?)(?=Probability|Found In|Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if recovery_match:
        issue['recovery'] = clean_text(recovery_match.group(1))

    # Probability
    probability_match = re.search(r'Probability\s+(.+?)(?=Found In|Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if probability_match:
        issue['probability'] = clean_text(probability_match.group(1))

    # Found In (can have multiple versions)
    found_in_match = re.search(r'Found In\s+(.+?)(?=Technology|Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if found_in_match:
        found_in_text = found_in_match.group(1)
        # Extract version numbers like "FI 10.0.20", "FI 08.0.95"
        versions = re.findall(r'FI\s*(\d+\.\d+\.\d+[a-z]*(?:_cd\d+)?)', found_in_text, re.IGNORECASE)
        issue['found_in'] = versions

    # Technology / Technology Group
    tech_match = re.search(r'Technology\s*/\s*Technology\s+Group\s+(.+?)(?=Issue FI-|$)', text[start_idx:], re.DOTALL | re.IGNORECASE)
    if tech_match:
        issue['technology'] = clean_text(tech_match.group(1))

    return issue

def extract_issues_from_pdf(pdf_path):
    """Extract all issues (closed and known) from a single release notes PDF"""
    issues = []

    print(f"Processing {pdf_path.name}...")

    version = extract_version_from_filename(pdf_path.name)
    if not version:
        print(f"  Warning: Could not extract version from filename")
        return issues

    print(f"  Version: {version}")

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        in_issues_section = False

        # Extract all text from the PDF
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            # Check if we've entered an issues section
            if re.search(r'(Closed Issues|Known Issues|Issues)', text, re.IGNORECASE):
                in_issues_section = True

            # Stop if we hit certain end markers
            if re.search(r'(Limitations and Restrictions|Obtaining Technical Support)', text, re.IGNORECASE):
                in_issues_section = False

            if in_issues_section:
                full_text += text + "\n"

        if not full_text:
            print(f"  No issues section found")
            return issues

        # Find all section headers to map issues to their status
        section_headers = []

        # Look for "Closed Issues with Code Changes" sections
        for match in re.finditer(r'Closed Issues.*?(?:in|for).*?(?:Release|FastIron)\s+(\d+\.\d+\.\d+[a-z_cd\d]*)', full_text, re.IGNORECASE):
            section_headers.append({
                'start': match.start(),
                'status': 'closed',
                'version': match.group(1)
            })

        # Look for "Known Issues" sections
        for match in re.finditer(r'Known Issues.*?(?:in|for).*?(?:Release|FastIron)\s+(\d+\.\d+\.\d+[a-z_cd\d]*)', full_text, re.IGNORECASE):
            section_headers.append({
                'start': match.start(),
                'status': 'known',
                'version': match.group(1)
            })

        # Sort by position
        section_headers.sort(key=lambda x: x['start'])

        # Find all issue IDs (FI-XXXXXX)
        issue_pattern = r'Issue\s+(FI-\d+)'
        issue_matches = list(re.finditer(issue_pattern, full_text, re.IGNORECASE))

        print(f"  Found {len(issue_matches)} issues")

        # Parse each issue
        for i, match in enumerate(issue_matches):
            issue_id = match.group(1)
            start_idx = match.start()

            # Determine status based on which section this issue is in
            current_status = 'unknown'
            current_section_version = version

            for header in reversed(section_headers):
                if start_idx > header['start']:
                    current_status = header['status']
                    current_section_version = header['version']
                    break

            # Parse the issue block
            issue = parse_issue_block(full_text, start_idx, issue_id)
            issue['status'] = current_status
            issue['fixed_in'] = current_section_version if current_status == 'closed' else None
            issue['reported_version'] = version

            # Only add if we have at least a symptom
            if issue['symptom']:
                issues.append(issue)

        print(f"  Extracted {len(issues)} issues with data")

    return issues

def main():
    """Main extraction process"""
    # Find all release notes PDFs (not feature support matrix)
    release_notes_dir = Path("release-notes")

    if not release_notes_dir.exists():
        print("Error: release-notes directory not found")
        return

    # Find release notes PDFs (exclude feature support matrix PDFs)
    pdf_files = []
    for pdf_file in release_notes_dir.glob("fastiron-*-releasenotes*.pdf"):
        pdf_files.append(pdf_file)

    # Remove duplicates and sort
    pdf_files = sorted(list(set(pdf_files)))

    if not pdf_files:
        print("Error: No release notes PDFs found")
        return

    print(f"Found {len(pdf_files)} release notes PDF files to process\n")

    all_issues = []

    for pdf_file in pdf_files:
        issues = extract_issues_from_pdf(pdf_file)
        all_issues.extend(issues)

    # Save to JSON
    output_file = Path("issues_data.json")
    with open(output_file, 'w') as f:
        json.dump(all_issues, f, indent=2)

    print(f"\nExtraction complete!")
    print(f"Total issues extracted: {len(all_issues)}")
    print(f"Output saved to: {output_file}")

    # Print some statistics
    statuses = defaultdict(int)
    technologies = defaultdict(int)
    versions_with_issues = set()

    for issue in all_issues:
        statuses[issue['status']] += 1
        if issue['technology']:
            technologies[issue['technology']] += 1
        if issue['fixed_in']:
            versions_with_issues.add(issue['fixed_in'])
        versions_with_issues.add(issue['reported_version'])

    print(f"\nStatistics:")
    print(f"  Closed issues: {statuses.get('closed', 0)}")
    print(f"  Known issues: {statuses.get('known', 0)}")
    print(f"  Versions covered: {sorted(versions_with_issues)}")
    print(f"  Unique technology groups: {len(technologies)}")

    if technologies:
        print(f"\nTop 5 technology groups:")
        for tech, count in sorted(technologies.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"    {tech}: {count}")

if __name__ == "__main__":
    main()

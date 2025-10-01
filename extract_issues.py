#!/usr/bin/env python3
"""
Extract defects (bug fixes and known issues) from FastIron release notes PDFs using table extraction.
"""

import pdfplumber
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def extract_version_from_filename(filename):
    """Extract version number from release notes filename like 'fastiron-08090mc-releasenotes-1.0.pdf'"""
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
        digit_end = 0
        for i, c in enumerate(base_version):
            if c.isdigit():
                digit_end = i + 1
            else:
                break

        if digit_end < len(base_version):
            letter_suffix = base_version[digit_end:]
            base_version = base_version[:digit_end]

        # Convert 08090 to 8.0.90 or 10020 to 10.0.20
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
    text = str(text).replace('\n', ' ').replace('\r', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def is_defect_table(table):
    """Check if a table is a defect table (has Issue FI-XXXXXX structure)"""
    if not table or len(table) < 7:  # Defect tables have at least 7 rows
        return False

    # First row should be ['Issue', 'FI-XXXXXX']
    first_row = table[0]
    if len(first_row) != 2:
        return False

    field_name = str(first_row[0]).strip() if first_row[0] else ""
    field_value = str(first_row[1]).strip() if first_row[1] else ""

    return field_name.lower() == 'issue' and re.match(r'FI-\d+', field_value)

def extract_fi_number(table):
    """Extract FI number from defect table"""
    if table and len(table) > 0 and len(table[0]) >= 2:
        fi_text = str(table[0][1]).strip()
        match = re.match(r'(FI-\d+)', fi_text)
        if match:
            return match.group(1)
    return None

def parse_defect_table(table):
    """Parse a defect table and extract all fields"""
    if not is_defect_table(table):
        return None

    defect = {
        'id': '',
        'symptom': '',
        'condition': '',
        'workaround': '',
        'recovery': '',
        'probability': '',
        'found_in': [],
        'technology': ''
    }

    # Extract FI number
    defect['id'] = extract_fi_number(table)
    if not defect['id']:
        return None

    # Parse each row (field_name, field_value)
    for row in table:
        if len(row) < 2:
            continue

        field_name = str(row[0]).strip().lower() if row[0] else ""
        field_value = str(row[1]).strip() if row[1] else ""

        if 'symptom' in field_name:
            defect['symptom'] = clean_text(field_value)
        elif 'condition' in field_name:
            defect['condition'] = clean_text(field_value)
        elif 'workaround' in field_name:
            defect['workaround'] = clean_text(field_value)
        elif 'recovery' in field_name:
            defect['recovery'] = clean_text(field_value)
        elif 'probability' in field_name:
            defect['probability'] = clean_text(field_value)
        elif 'found in' in field_name:
            # Extract version numbers like "FI 10.0.20 FI 08.0.95"
            versions = re.findall(r'FI\s*(\d+\.\d+\.\d+[a-z]*(?:_cd\d+)?)', field_value, re.IGNORECASE)
            defect['found_in'] = versions
        elif 'technology' in field_name:
            defect['technology'] = clean_text(field_value)

    # Only return if we have at least a symptom
    if defect['symptom']:
        return defect
    return None

def determine_section_status(page_text):
    """Determine if current page is in 'closed' or 'known' issues section"""
    # Look for section headers in page text
    if re.search(r'Closed Issues.*with Code Changes', page_text, re.IGNORECASE):
        return 'closed'
    elif re.search(r'Known Issues', page_text, re.IGNORECASE):
        return 'known'
    return None

def extract_defects_from_pdf(pdf_path):
    """Extract all defects from a single release notes PDF"""
    defects_by_fi = {}  # Key by FI number

    print(f"  Processing {pdf_path.name}...", flush=True)

    version = extract_version_from_filename(pdf_path.name)
    if not version:
        print(f"  ⚠ Warning: Could not extract version from filename", flush=True)
        return defects_by_fi

    print(f"  Version: {version}", flush=True)

    with pdfplumber.open(pdf_path) as pdf:
        current_status = None  # 'closed' or 'known'
        pages_with_defects = 0

        for page_num, page in enumerate(pdf.pages, 1):
            # Get page text to determine section
            page_text = page.extract_text() or ""

            # Update current section status based on headers
            section_status = determine_section_status(page_text)
            if section_status:
                current_status = section_status

            # Skip if not in an issues section and page doesn't have FI numbers
            if not current_status and 'FI-' not in page_text:
                continue

            # Extract tables from page
            tables = page.extract_tables()

            for table in tables:
                defect = parse_defect_table(table)
                if not defect:
                    continue

                fi_num = defect['id']
                pages_with_defects += 1

                # If we haven't seen this FI number, add it
                if fi_num not in defects_by_fi:
                    defects_by_fi[fi_num] = defect
                    defects_by_fi[fi_num]['version_history'] = {}

                # Record this version and status (use current_status or 'known' as default)
                status = current_status if current_status else 'known'
                defects_by_fi[fi_num]['version_history'][version] = status

    print(f"  ✓ Extracted {len(defects_by_fi)} unique defects from {pages_with_defects} tables", flush=True)
    return defects_by_fi

def merge_defects(all_defects_by_pdf):
    """Merge defects from multiple PDFs, aggregating by FI number"""
    merged = {}

    for pdf_defects in all_defects_by_pdf:
        for fi_num, defect in pdf_defects.items():
            if fi_num not in merged:
                # First time seeing this defect
                merged[fi_num] = {
                    'id': defect['id'],
                    'symptom': defect['symptom'],
                    'condition': defect['condition'],
                    'workaround': defect['workaround'],
                    'recovery': defect['recovery'],
                    'probability': defect['probability'],
                    'technology': defect['technology'],
                    'found_in': defect.get('found_in', []),
                    'version_history': defect['version_history'].copy()
                }
            else:
                # Merge version history
                merged[fi_num]['version_history'].update(defect['version_history'])

                # Update fields if they were empty before (prefer non-empty data)
                for field in ['symptom', 'condition', 'workaround', 'recovery', 'probability', 'technology']:
                    if not merged[fi_num][field] and defect[field]:
                        merged[fi_num][field] = defect[field]

                # Merge found_in versions
                for v in defect.get('found_in', []):
                    if v not in merged[fi_num]['found_in']:
                        merged[fi_num]['found_in'].append(v)

    # Calculate first_seen and fixed_in for each defect
    for fi_num, defect in merged.items():
        versions = sorted(defect['version_history'].keys())

        # First seen is earliest version
        defect['first_seen'] = versions[0] if versions else None

        # Fixed in is the first version where status is 'closed'
        defect['fixed_in'] = None
        for v in versions:
            if defect['version_history'][v] == 'closed':
                defect['fixed_in'] = v
                break

        # Current status is status in the latest version
        defect['current_status'] = defect['version_history'][versions[-1]] if versions else 'unknown'

    return merged

def main():
    """Main extraction process"""
    start_time = datetime.now()
    print(f"\n{'='*80}")
    print(f"FastIron Defect Extraction")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    sys.stdout.flush()

    release_notes_dir = Path("release-notes")

    if not release_notes_dir.exists():
        print("Error: release-notes directory not found")
        return

    # Find release notes PDFs (exclude feature support matrix PDFs)
    pdf_files = sorted(release_notes_dir.glob("fastiron-*-releasenotes*.pdf"))

    if not pdf_files:
        print("Error: No release notes PDFs found")
        return

    print(f"Found {len(pdf_files)} release notes PDF files to process\n", flush=True)

    all_defects = []

    for idx, pdf_file in enumerate(pdf_files, 1):
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / idx if idx > 0 else 0
        remaining = avg_time * (len(pdf_files) - idx)

        print(f"\n[{idx}/{len(pdf_files)}] ({idx/len(pdf_files)*100:.1f}%) - Elapsed: {int(elapsed)}s - ETA: {int(remaining)}s", flush=True)
        defects = extract_defects_from_pdf(pdf_file)
        all_defects.append(defects)

    # Merge defects from all PDFs
    print("\n" + "="*80, flush=True)
    print("Merging defects from all versions...", flush=True)
    merged_defects = merge_defects(all_defects)

    # Verify uniqueness
    print(f"Verifying FI number uniqueness...", flush=True)
    fi_numbers = list(merged_defects.keys())
    if len(fi_numbers) == len(set(fi_numbers)):
        print(f"✓ All {len(fi_numbers)} FI numbers are unique", flush=True)
    else:
        print(f"✗ WARNING: Duplicate FI numbers detected!", flush=True)

    # Convert to list for JSON output (sorted by FI number)
    defects_list = [merged_defects[fi] for fi in sorted(merged_defects.keys())]

    # Save to JSON
    output_file = Path("defects_data.json")
    print(f"Writing output to {output_file}...", flush=True)
    with open(output_file, 'w') as f:
        json.dump(defects_list, f, indent=2)

    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()

    print(f"\n" + "="*80, flush=True)
    print(f"EXTRACTION COMPLETE", flush=True)
    print("="*80, flush=True)
    print(f"Total unique defects: {len(merged_defects)}", flush=True)
    print(f"Output saved to: {output_file}", flush=True)
    print(f"Total time: {int(total_time)}s ({total_time/60:.1f} minutes)", flush=True)

    # Print statistics
    closed_count = sum(1 for d in defects_list if d['current_status'] == 'closed')
    known_count = sum(1 for d in defects_list if d['current_status'] == 'known')

    print(f"\nDefect Status:", flush=True)
    print(f"  Currently fixed (closed): {closed_count}", flush=True)
    print(f"  Currently known issues: {known_count}", flush=True)

    # Count defects by technology
    tech_counts = defaultdict(int)
    for defect in defects_list:
        if defect['technology']:
            tech_counts[defect['technology']] += 1

    if tech_counts:
        print(f"\nTop 10 technology groups:", flush=True)
        for tech, count in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {tech}: {count}", flush=True)

    # Show version coverage
    all_versions = set()
    for defect in defects_list:
        all_versions.update(defect['version_history'].keys())

    print(f"\nVersion Coverage:", flush=True)
    print(f"  Total versions: {len(all_versions)}", flush=True)
    print(f"  Versions: {', '.join(sorted(all_versions)[:10])}", flush=True)
    if len(all_versions) > 10:
        print(f"  ... and {len(all_versions) - 10} more", flush=True)

    # Show sample records
    print(f"\nSample defect records:", flush=True)
    for i, defect in enumerate(defects_list[:3], 1):
        print(f"\n  {i}. {defect['id']}:", flush=True)
        print(f"     Symptom: {defect['symptom'][:80]}...", flush=True)
        print(f"     Versions tracked: {len(defect['version_history'])}", flush=True)
        print(f"     First seen: {defect['first_seen']}", flush=True)
        print(f"     Fixed in: {defect['fixed_in'] or 'Not fixed'}", flush=True)
        print(f"     Current status: {defect['current_status']}", flush=True)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze defect table formatting across different FastIron versions to identify any format changes.
"""

import pdfplumber
import re
from pathlib import Path

def find_defect_section_pages(pdf_path):
    """Find pages that contain defect sections (Closed Issues or Known Issues)"""
    pages_info = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""

            # Check if page has defect section headers
            has_closed = bool(re.search(r'Closed Issues.*with Code Changes', text, re.IGNORECASE))
            has_known = bool(re.search(r'Known Issues', text, re.IGNORECASE))

            # Check if page has FI- issue numbers
            has_fi_numbers = bool(re.findall(r'FI-\d+', text))

            if has_closed or has_known or has_fi_numbers:
                pages_info.append({
                    'page': page_num,
                    'has_closed': has_closed,
                    'has_known': has_known,
                    'has_fi_numbers': has_fi_numbers
                })

    return pages_info

def extract_sample_table(pdf_path, max_pages=3):
    """Extract first few defect tables from a PDF for format analysis"""
    tables_found = []

    with pdfplumber.open(pdf_path) as pdf:
        pages_checked = 0

        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""

            # Look for defect sections
            if not (re.search(r'Closed Issues|Known Issues', text, re.IGNORECASE) or re.search(r'FI-\d+', text)):
                continue

            tables = page.extract_tables()

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Check if this looks like a defect table (has Issue FI-XXXXX)
                first_row = table[0]
                if len(first_row) >= 2:
                    field_name = str(first_row[0]).strip() if first_row[0] else ""
                    field_value = str(first_row[1]).strip() if first_row[1] else ""

                    if field_name.lower() == 'issue' and re.match(r'FI-\d+', field_value):
                        tables_found.append({
                            'page': page_num,
                            'table': table,
                            'fi_number': field_value
                        })

                        if len(tables_found) >= max_pages:
                            return tables_found

            pages_checked += 1
            if pages_checked >= 20:  # Don't search too far
                break

    return tables_found

def analyze_table_structure(table):
    """Analyze the structure of a defect table"""
    fields = []

    for row in table:
        if len(row) >= 2:
            field_name = str(row[0]).strip() if row[0] else ""
            field_value = str(row[1]).strip() if row[1] else ""

            if field_name:
                fields.append(field_name)

    return fields

def main():
    """Analyze formatting across major versions"""

    # Versions to check
    test_versions = [
        ('8.0.90', 'release-notes/fastiron-08090-releasenotes-3.0.pdf'),
        ('8.0.91', 'release-notes/fastiron-08091-releasenotes-2.0.pdf'),
        ('8.0.92', 'release-notes/fastiron-08092-releasenotes-1.0.pdf'),
        ('8.0.95', 'release-notes/fastiron-08095-releasenotes-1.0.pdf'),
        ('9.0.0', 'release-notes/fastiron-09000-releasenotes-1.0.pdf'),
        ('9.0.10', 'release-notes/fastiron-09010-releasenotes-1.0.pdf'),
        ('10.0.0', 'release-notes/fastiron-10000-releasenotes-7.0.pdf'),
        ('10.0.10', 'release-notes/fastiron-10010a-releasenotes-2.0.pdf'),
        ('10.0.20', 'release-notes/fastiron-10020-releasenotes-1.0.pdf'),
    ]

    print("=" * 80)
    print("DEFECT TABLE FORMAT ANALYSIS ACROSS VERSIONS")
    print("=" * 80)

    for version, pdf_path in test_versions:
        path = Path(pdf_path)

        if not path.exists():
            print(f"\n\n{version}: FILE NOT FOUND: {pdf_path}")
            continue

        print(f"\n\n{'='*80}")
        print(f"VERSION: {version}")
        print(f"FILE: {path.name}")
        print(f"{'='*80}")

        # Find defect section pages
        print("\n1. DEFECT SECTION PAGES:")
        pages_info = find_defect_section_pages(path)

        if pages_info:
            closed_pages = [p['page'] for p in pages_info if p['has_closed']]
            known_pages = [p['page'] for p in pages_info if p['has_known']]
            fi_pages = [p['page'] for p in pages_info if p['has_fi_numbers']]

            print(f"   Closed Issues sections: pages {closed_pages[:5]}")
            print(f"   Known Issues sections: pages {known_pages[:5]}")
            print(f"   Pages with FI numbers: {len(fi_pages)} pages")
        else:
            print("   No defect sections found")

        # Extract sample tables
        print("\n2. SAMPLE DEFECT TABLES:")
        sample_tables = extract_sample_table(path, max_pages=2)

        if sample_tables:
            for i, table_info in enumerate(sample_tables, 1):
                print(f"\n   Table {i} (Page {table_info['page']}, {table_info['fi_number']}):")
                fields = analyze_table_structure(table_info['table'])
                print(f"   Fields: {fields}")

                # Show first few rows for inspection
                print(f"   First 5 rows:")
                for j, row in enumerate(table_info['table'][:5], 1):
                    if len(row) >= 2:
                        print(f"      Row {j}: {str(row[0])[:30]:30s} | {str(row[1])[:50]}")
        else:
            print("   No defect tables found")

    print("\n\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()

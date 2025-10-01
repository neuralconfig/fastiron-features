#!/usr/bin/env python3
"""
Extract new features, CLI commands, and enhancements from FastIron release notes PDFs.
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

def extract_list_items(text, start_marker, end_markers):
    """Extract bullet point list items between markers"""
    items = []

    # Find the start position
    start_match = re.search(start_marker, text, re.IGNORECASE)
    if not start_match:
        return items

    start_pos = start_match.end()

    # Find the end position (first matching end marker)
    end_pos = len(text)
    for end_marker in end_markers:
        end_match = re.search(end_marker, text[start_pos:], re.IGNORECASE)
        if end_match:
            end_pos = start_pos + end_match.start()
            break

    # Extract the section text
    section_text = text[start_pos:end_pos]

    # Extract bullet points (lines starting with •, -, or *)
    lines = section_text.split('\n')
    current_item = ""

    for line in lines:
        line = line.strip()
        # Check if this is a new bullet point
        if re.match(r'^[•\-\*]\s+', line):
            # Save previous item if exists
            if current_item:
                items.append(clean_text(current_item))
            # Start new item (remove bullet character)
            current_item = re.sub(r'^[•\-\*]\s+', '', line)
        elif line and current_item:
            # Continue current item
            current_item += " " + line

    # Add last item
    if current_item:
        items.append(clean_text(current_item))

    return items

def extract_hardware_info(text):
    """Extract new hardware information from the text"""
    hardware = []

    # Look for hardware section
    hw_section_match = re.search(r'New\s+(?:Ruckus\s+)?(?:ICX|Hardware).*?(?:SKUs?|Models?|Switch)', text, re.IGNORECASE | re.DOTALL)
    if not hw_section_match:
        return hardware

    # Try to find hardware model patterns (ICX XXXX-XXX)
    hw_models = re.findall(r'(?:The\s+)?ICX\s*(\d{4}[A-Z]?(?:-\d{2}[A-Z]+)?)', text, re.IGNORECASE)

    for model in hw_models:
        hardware.append(f"ICX{model}")

    return list(set(hardware))  # Remove duplicates

def extract_software_features(text):
    """Extract new software features from the text"""
    features = []

    # Look for "Feature Descriptions" table (two-column format)
    feature_desc_match = re.search(r'Feature\s+Descriptions\s+(.*?)(?=CLI Commands|Modified Commands|New Commands|RFCs and Standards)', text, re.IGNORECASE | re.DOTALL)
    if feature_desc_match:
        feature_section = feature_desc_match.group(1)

        # Split by lines and look for feature patterns
        # Features typically have the name on one line and description on another or the same line
        lines = feature_section.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and common headers
            if not line or 'FastIron' in line or 'Part Number' in line or 'Page' in line:
                i += 1
                continue

            # Check if this might be a feature name (typically starts with capital, reasonable length)
            if line and len(line) < 100 and not line.startswith('•'):
                # Try to get description from same line or next line
                description = ""

                # Check if there's a description on the same line (after multiple spaces)
                if '  ' in line:
                    parts = re.split(r'\s{2,}', line, 1)
                    if len(parts) == 2:
                        feature_name = parts[0].strip()
                        description = parts[1].strip()
                        features.append(f"{feature_name}: {description}")
                        i += 1
                        continue

                # Otherwise, check next lines for description
                feature_name = line
                i += 1
                desc_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip()[0].isupper():
                    desc_lines.append(lines[i].strip())
                    i += 1

                if desc_lines:
                    description = ' '.join(desc_lines)
                    features.append(f"{feature_name}: {description}")
                else:
                    features.append(feature_name)
            else:
                i += 1

    # Also try extracting from bulleted lists
    items = extract_list_items(text, r'New Software Features', [r'CLI Commands', r'RFCs and Standards'])
    features.extend(items)

    return list(set(features))  # Remove duplicates

def extract_cli_commands(text):
    """Extract CLI command changes"""
    cli_changes = {
        'new': [],
        'modified': [],
        'deprecated': [],
        'reintroduced': []
    }

    # Helper to extract commands from a section (including checking for "No new/modified/deprecated")
    def extract_command_section(section_name, text):
        commands = []

        # Look for the section
        pattern = f'{section_name}.*?in.*?\\d+\\.\\d+\\.\\d+[a-z_cd\\d]*'
        section_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if not section_match:
            # Try simpler pattern
            section_match = re.search(f'{section_name}', text, re.IGNORECASE)

        if section_match:
            start_pos = section_match.end()

            # Find end position
            end_markers = [r'New Commands', r'Modified Commands', r'Deprecated Commands', r'Reintroduced Commands', r'RFCs and Standards', r'MIBs', r'Hardware Support']
            end_pos = len(text)
            for marker in end_markers:
                end_match = re.search(marker, text[start_pos:], re.IGNORECASE)
                if end_match and end_match.start() > 0:
                    end_pos = start_pos + end_match.start()
                    break

            section_text = text[start_pos:end_pos]

            # Check if it says "no new/modified/deprecated commands"
            if re.search(r'No (?:new|commands have been)', section_text, re.IGNORECASE):
                return []

            # Extract command names (typically with • or in code format)
            # Commands can be listed as bullets or just text
            for line in section_text.split('\n'):
                line = line.strip()
                # Remove bullet points
                line = re.sub(r'^[•\-\*]\s+', '', line)

                # Skip empty lines and common non-command text
                if not line or 'FastIron' in line or 'Part Number' in line or len(line) > 100:
                    continue

                # If line looks like a command (reasonable length, not a full sentence)
                if line and not line.endswith('.') and len(line) < 80:
                    commands.append(line)

        return commands

    # Extract each type of command
    cli_changes['new'] = extract_command_section('New Commands', text)
    cli_changes['modified'] = extract_command_section('Modified Commands', text)
    cli_changes['deprecated'] = extract_command_section('Deprecated Commands', text)
    cli_changes['reintroduced'] = extract_command_section('Reintroduced Commands', text)

    return cli_changes

def extract_rfcs_and_mibs(text):
    """Extract RFCs and MIBs information"""
    rfcs = []
    mibs = []

    # Look for RFC section
    rfc_section_match = re.search(r'RFCs and Standards(.{10,500})', text, re.IGNORECASE | re.DOTALL)
    if rfc_section_match:
        rfc_text = rfc_section_match.group(1)
        # Check if it says there are no new RFCs
        if not re.search(r'no\s+(?:new|newly)', rfc_text, re.IGNORECASE):
            # Try to extract RFC numbers
            rfc_nums = re.findall(r'RFC\s*(\d+)', rfc_text, re.IGNORECASE)
            rfcs = [f"RFC {num}" for num in rfc_nums]

    # Look for MIB section
    mib_section_match = re.search(r'MIBs(.{10,500})', text, re.IGNORECASE | re.DOTALL)
    if mib_section_match:
        mib_text = mib_section_match.group(1)
        # Check if it says there are no new MIBs
        if not re.search(r'no\s+(?:new|newly)', mib_text, re.IGNORECASE):
            # Try to extract MIB names (typically in all caps with hyphens)
            mib_names = re.findall(r'([A-Z][A-Z0-9\-]{3,}(?:\-MIB)?)', mib_text)
            mibs = list(set(mib_names))  # Remove duplicates

    return rfcs, mibs

def extract_features_from_pdf(pdf_path):
    """Extract feature data from a single release notes PDF"""
    print(f"Processing {pdf_path.name}...")

    version = extract_version_from_filename(pdf_path.name)
    if not version:
        print(f"  Warning: Could not extract version from filename")
        return None

    print(f"  Version: {version}")

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        in_new_features_section = False
        pages_collected = 0

        # Extract text from pages that contain "New in This Release"
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue

            # Skip table of contents pages (typically have lots of dots and page numbers)
            if re.search(r'\.{5,}', text) and page_num < 10:
                continue

            # Start collecting when we hit actual "New in This Release" header (not just ToC entry)
            # Look for the header followed by actual content like "Hardware" or bullet points
            if not in_new_features_section:
                if re.search(r'New in This Release', text, re.IGNORECASE):
                    # Make sure this is the actual section, not ToC
                    # Check if next lines have content like "Hardware" or "Software Features"
                    if re.search(r'(?:Hardware|Software Features|CLI Commands)', text, re.IGNORECASE):
                        in_new_features_section = True

            if in_new_features_section:
                full_text += text + "\n"
                pages_collected += 1

                # Stop after collecting several pages or when we hit actual next sections
                # (not ToC entries)
                if pages_collected > 2:
                    if re.search(r'^(?:Hardware Support|Software Upgrade|Upgrade Information|Closed Issues|Known Issues)\s*$', text, re.MULTILINE | re.IGNORECASE):
                        break

        if not full_text:
            print(f"  No 'New in This Release' section found")
            return None

        # Extract all components
        hardware = extract_hardware_info(full_text)
        software_features = extract_software_features(full_text)
        cli_commands = extract_cli_commands(full_text)
        rfcs, mibs = extract_rfcs_and_mibs(full_text)

        print(f"  Hardware: {len(hardware)}, Features: {len(software_features)}, CLI: {len(cli_commands['new'])} new, {len(cli_commands['modified'])} modified, {len(cli_commands['deprecated'])} deprecated")

        return {
            'version': version,
            'hardware': hardware,
            'software_features': software_features,
            'cli_commands': cli_commands,
            'rfcs': rfcs,
            'mibs': mibs
        }

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

    all_releases = []

    for pdf_file in pdf_files:
        release_data = extract_features_from_pdf(pdf_file)
        if release_data:
            all_releases.append(release_data)

    # Save to JSON
    output_file = Path("release_features_data.json")
    with open(output_file, 'w') as f:
        json.dump(all_releases, f, indent=2)

    print(f"\nExtraction complete!")
    print(f"Total releases extracted: {len(all_releases)}")
    print(f"Output saved to: {output_file}")

    # Print some statistics
    total_hardware = sum(len(r['hardware']) for r in all_releases)
    total_features = sum(len(r['software_features']) for r in all_releases)
    total_cli_new = sum(len(r['cli_commands']['new']) for r in all_releases)
    total_cli_modified = sum(len(r['cli_commands']['modified']) for r in all_releases)
    total_rfcs = sum(len(r['rfcs']) for r in all_releases)
    total_mibs = sum(len(r['mibs']) for r in all_releases)

    print(f"\nStatistics:")
    print(f"  Total new hardware models: {total_hardware}")
    print(f"  Total new software features: {total_features}")
    print(f"  Total new CLI commands: {total_cli_new}")
    print(f"  Total modified CLI commands: {total_cli_modified}")
    print(f"  Total RFCs: {total_rfcs}")
    print(f"  Total MIBs: {total_mibs}")

    # Show versions covered
    versions = [r['version'] for r in all_releases]
    print(f"\nVersions covered: {sorted(versions)}")

if __name__ == "__main__":
    main()

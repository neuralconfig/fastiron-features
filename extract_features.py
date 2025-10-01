#!/usr/bin/env python3
"""
Extract feature support data from FastIron PDF files.
"""

import pdfplumber
import json
import re
from pathlib import Path

def extract_version_from_filename(filename):
    """Extract version number from filename like 'fastiron-08090-featuresupportmatrix.pdf'"""
    match = re.search(r'fastiron-(\d+)-', filename)
    if match:
        version_str = match.group(1)
        # Convert 08090 to 08.0.90
        if len(version_str) == 5:
            return f"{version_str[:2]}.{version_str[2]}.{version_str[3:]}"
    return None

def normalize_platform_name(platform_str):
    """Normalize platform names to consistent format"""
    if not platform_str:
        return None

    # Remove spaces and hyphens, convert to uppercase
    platform_str = str(platform_str).strip().upper().replace(' ', '').replace('-', '')

    # Handle common PDF extraction errors
    error_mappings = {
        'ICX77507': 'ICX7550',
        'ICX77509': 'ICX7550',
        'ICX775013': 'ICX7550',
        'ICX7750': 'ICX7550',
        'ICX820034': 'ICX8200',
        'ICX820042': 'ICX8200',
    }

    if platform_str in error_mappings:
        return error_mappings[platform_str]

    # Extract ICX model number - handle 4-digit models and special suffixes
    match = re.search(r'ICX(\d{4}(?:ES)?)', platform_str)
    if match:
        model = match.group(1)
        return f"ICX{model}"

    return None

def is_feature_table_row(row):
    """Check if a row appears to be from a feature table"""
    if not row or len(row) < 2:
        return False

    # Feature rows have a feature name and version numbers or "No"
    # Skip header rows and empty rows
    first_cell = str(row[0]).strip() if row[0] else ""

    # Skip obvious non-feature rows
    skip_patterns = ['ICX 7', 'ICX 8', 'ICX7', 'ICX8',
                     'Feature', 'Table', 'Chapter', 'Page', 'RUCKUS', 'FastIron']

    if any(pattern in first_cell for pattern in skip_patterns):
        return False

    if not first_cell or first_cell == '':
        return False

    return True

def clean_version(version_str):
    """Clean and normalize version strings - strict validation"""
    if not version_str:
        return "No"

    version_str = str(version_str).strip()

    # If it's "No" or empty, return "No"
    if version_str.lower() == 'no' or version_str == '' or version_str == 'None':
        return "No"

    # Clean up version numbers - remove whitespace and footnote markers
    # But preserve dots, digits, letters, and underscores
    version_str = re.sub(r'[^\d.a-zA-Z_]', '', version_str)

    if version_str == '':
        return "No"

    # FastIron versions MUST follow X.0.YY or XX.0.YY[suffix] format strictly
    # Valid formats:
    #   X.0.YY or XX.0.YY    (e.g., 8.0.90, 10.0.20)
    #   X.0.YYn or XX.0.YYn  (e.g., 10.0.20a, 8.0.95f) - single letter
    #   X.0.YYnm             (e.g., 10.0.10cd) - two letters
    #   X.0.YY_cdn           (e.g., 10.0.20_cd1, 10.0.20_cd12) - CD with 1-2 digit number
    #   X.0.YYn_cdn          (e.g., 10.0.10g_cd1) - letter + CD with 1-2 digit number

    # Strict pattern: X.0.YY or XX.0.YY + optional suffix
    # CD number must be 1-2 digits only (not 111)
    match = re.match(r'^(\d{1,2})\.0\.(\d{2})([a-z]{0,2}(?:_cd\d{1,2})?)$', version_str, re.IGNORECASE)
    if match:
        major, patch, suffix = match.groups()
        # Remove leading zeros from major version (8 not 08)
        major = str(int(major))
        result = f"{major}.0.{patch}"
        if suffix:
            result += suffix.lower()
        return result

    # If it doesn't match the strict format, it's invalid
    return "No"

def extract_features_from_pdf(pdf_path):
    """Extract feature data from a single PDF file"""
    features = []
    current_category = None
    current_platforms = None
    seen_features = set()  # Track feature names to avoid duplicates from page breaks

    print(f"Processing {pdf_path.name}...")

    version = extract_version_from_filename(pdf_path.name)
    if not version:
        print(f"  Warning: Could not extract version from filename")
        return features

    print(f"  Version: {version}")

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract tables from the page
            tables = page.extract_tables()

            for table in tables:
                if not table or len(table) < 2:
                    continue

                # Look for tables with ICX platform headers
                header = table[0] if table else []

                # STRICT VALIDATION: First column must be "Feature" for valid feature tables
                first_col = str(header[0]).strip() if header and header[0] else ""
                if first_col.lower() != "feature":
                    continue

                header_str = ' '.join([str(cell) for cell in header if cell])

                # Check if this looks like a feature table (has ICX platforms)
                if 'ICX' in header_str:
                    # Extract platform names from header
                    platforms = []
                    for cell in header[1:]:  # Skip first column (Feature name)
                        platform = normalize_platform_name(cell)
                        if platform:
                            platforms.append(platform)

                    if not platforms:
                        continue

                    current_platforms = platforms

                    if page_num < 3:  # Only print for first occurrence
                        print(f"  Detected platforms: {', '.join(platforms)}")

                    # Process feature rows
                    for row in table[1:]:  # Skip header row
                        if not is_feature_table_row(row):
                            continue

                        if len(row) < 2:  # Need at least feature name + 1 platform
                            continue

                        feature_name = str(row[0]).strip() if row[0] else ""

                        # Clean feature name: remove newlines, collapse spaces, strip
                        feature_name = feature_name.replace('\n', ' ').replace('\r', ' ')
                        feature_name = re.sub(r'\s+', ' ', feature_name).strip()

                        # Validate feature name - should be reasonable length
                        if not feature_name or len(feature_name) > 150:
                            continue

                        # Check if this might be a category header
                        if feature_name and not any(row[i] for i in range(1, min(len(platforms)+1, len(row)))):
                            current_category = feature_name
                            continue

                        # Extract version support for each platform dynamically
                        platform_data = {}
                        has_valid_version = False

                        for i, platform in enumerate(platforms):
                            col_idx = i + 1  # +1 because first column is feature name
                            if col_idx < len(row):
                                cleaned_ver = clean_version(row[col_idx])
                                platform_data[platform] = cleaned_ver
                                # Track if we have at least one valid version (not "No")
                                if cleaned_ver != "No":
                                    has_valid_version = True
                            else:
                                platform_data[platform] = "No"

                        # Only add feature if it has at least one valid version number
                        if not has_valid_version:
                            continue

                        # Skip if we've already seen this feature (due to page breaks/table continuation)
                        if feature_name in seen_features:
                            continue

                        seen_features.add(feature_name)

                        feature_data = {
                            "name": feature_name,
                            "category": current_category or "Uncategorized",
                            "version": version,
                            "platforms": platform_data
                        }

                        features.append(feature_data)

    print(f"  Extracted {len(features)} features")
    return features

def main():
    """Main extraction process"""
    # Find all feature support matrix PDFs
    release_notes_dir = Path("release-notes")

    if not release_notes_dir.exists():
        print("Error: release-notes directory not found")
        return

    # Find PDFs with or without " (1)" suffix
    pdf_files = []
    for pattern in ["fastiron-*-featuresupportmatrix.pdf", "fastiron-*-featuresupportmatrix*.pdf"]:
        pdf_files.extend(release_notes_dir.glob(pattern))

    # Remove duplicates and sort
    pdf_files = sorted(list(set(pdf_files)))

    if not pdf_files:
        print("Error: No feature support matrix PDFs found")
        return

    print(f"Found {len(pdf_files)} PDF files to process\n")

    all_features = []

    for pdf_file in pdf_files:
        features = extract_features_from_pdf(pdf_file)
        all_features.extend(features)

    # Save to JSON
    output_file = Path("features_data.json")
    with open(output_file, 'w') as f:
        json.dump(all_features, f, indent=2)

    print(f"\nExtraction complete!")
    print(f"Total features extracted: {len(all_features)}")
    print(f"Output saved to: {output_file}")

    # Print some statistics
    versions = set(f['version'] for f in all_features)
    categories = set(f['category'] for f in all_features)
    all_platforms = set()
    for f in all_features:
        all_platforms.update(f['platforms'].keys())

    print(f"\nVersions found: {sorted(versions)}")
    print(f"Platforms found: {sorted(all_platforms)}")
    print(f"Categories found: {len(categories)}")

if __name__ == "__main__":
    main()

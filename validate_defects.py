#!/usr/bin/env python3
"""
Validate the defects_data.json output to ensure data quality.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_defects():
    """Load defects data"""
    with open('defects_data.json', 'r') as f:
        return json.load(f)

def validate_uniqueness(defects):
    """Validate that all FI numbers are unique"""
    fi_numbers = [d['id'] for d in defects]
    unique_fi = set(fi_numbers)

    print("=" * 80)
    print("UNIQUENESS VALIDATION")
    print("=" * 80)
    print(f"Total records: {len(fi_numbers)}")
    print(f"Unique FI numbers: {len(unique_fi)}")

    if len(fi_numbers) == len(unique_fi):
        print("✓ All FI numbers are unique")
        return True
    else:
        print("✗ DUPLICATE FI numbers detected!")
        # Find duplicates
        seen = set()
        duplicates = set()
        for fi in fi_numbers:
            if fi in seen:
                duplicates.add(fi)
            seen.add(fi)
        print(f"  Duplicates: {sorted(duplicates)}")
        return False

def validate_version_history(defects):
    """Validate version history data"""
    print("\n" + "=" * 80)
    print("VERSION HISTORY VALIDATION")
    print("=" * 80)

    all_versions = set()
    defects_with_history = 0
    total_version_entries = 0

    for defect in defects:
        if defect.get('version_history'):
            defects_with_history += 1
            versions = defect['version_history'].keys()
            all_versions.update(versions)
            total_version_entries += len(versions)

    print(f"Defects with version history: {defects_with_history}/{len(defects)}")
    print(f"Total version entries: {total_version_entries}")
    print(f"Unique versions tracked: {len(all_versions)}")
    print(f"\nVersions covered: {', '.join(sorted(all_versions)[:15])}")
    if len(all_versions) > 15:
        print(f"  ... and {len(all_versions) - 15} more")

    # Average versions per defect
    avg_versions = total_version_entries / len(defects) if defects else 0
    print(f"\nAverage versions per defect: {avg_versions:.1f}")

    return all_versions

def validate_required_fields(defects):
    """Validate that required fields are present"""
    print("\n" + "=" * 80)
    print("REQUIRED FIELDS VALIDATION")
    print("=" * 80)

    required_fields = ['id', 'symptom', 'version_history', 'first_seen', 'fixed_in', 'current_status']

    issues = []
    for i, defect in enumerate(defects):
        for field in required_fields:
            if field not in defect:
                issues.append(f"Record {i} ({defect.get('id', 'unknown')}): Missing field '{field}'")

    if not issues:
        print("✓ All required fields present in all records")
    else:
        print(f"✗ Found {len(issues)} issues:")
        for issue in issues[:10]:
            print(f"  {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")

    return len(issues) == 0

def analyze_status_distribution(defects):
    """Analyze defect status distribution"""
    print("\n" + "=" * 80)
    print("STATUS DISTRIBUTION")
    print("=" * 80)

    status_counts = defaultdict(int)
    for defect in defects:
        status = defect.get('current_status', 'unknown')
        status_counts[status] += 1

    for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / len(defects) * 100
        print(f"  {status}: {count} ({pct:.1f}%)")

def analyze_technology_distribution(defects):
    """Analyze technology distribution"""
    print("\n" + "=" * 80)
    print("TOP 10 TECHNOLOGY GROUPS")
    print("=" * 80)

    tech_counts = defaultdict(int)
    for defect in defects:
        tech = defect.get('technology', '')
        if tech:
            tech_counts[tech] += 1

    for tech, count in sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = count / len(defects) * 100
        print(f"  {tech}: {count} ({pct:.1f}%)")

def show_sample_records(defects):
    """Show sample records"""
    print("\n" + "=" * 80)
    print("SAMPLE RECORDS (First 3)")
    print("=" * 80)

    for i, defect in enumerate(defects[:3], 1):
        print(f"\n{i}. {defect['id']}")
        print(f"   Status: {defect.get('current_status', 'unknown')}")
        print(f"   Symptom: {defect['symptom'][:100]}...")
        print(f"   First seen: {defect.get('first_seen', 'N/A')}")
        print(f"   Fixed in: {defect.get('fixed_in', 'Not fixed')}")
        print(f"   Versions tracked: {len(defect.get('version_history', {}))}")
        if defect.get('technology'):
            print(f"   Technology: {defect['technology']}")

def main():
    """Run all validations"""
    print("\n" + "=" * 80)
    print("DEFECTS DATA VALIDATION")
    print("=" * 80)

    # Check if file exists
    if not Path('defects_data.json').exists():
        print("✗ Error: defects_data.json not found")
        return

    # Load data
    print("\nLoading defects_data.json...")
    try:
        defects = load_defects()
        print(f"✓ Loaded {len(defects)} defect records")
    except Exception as e:
        print(f"✗ Error loading data: {e}")
        return

    print(f"File size: {Path('defects_data.json').stat().st_size / 1024 / 1024:.2f} MB")

    # Run validations
    validate_uniqueness(defects)
    all_versions = validate_version_history(defects)
    validate_required_fields(defects)
    analyze_status_distribution(defects)
    analyze_technology_distribution(defects)
    show_sample_records(defects)

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

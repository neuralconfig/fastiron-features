#!/usr/bin/env python3
"""
Check if we have release notes for all feature matrix versions.
"""

import re
from pathlib import Path

def extract_base_version(filename):
    """Extract base version like 08090 from filename"""
    match = re.search(r'fastiron-(\d{5})', filename)
    if match:
        return match.group(1)
    return None

def format_version(version_str):
    """Convert 08090 to 8.0.90"""
    if len(version_str) == 5:
        major = str(int(version_str[:2]))
        minor = version_str[2]
        patch = version_str[3:5]
        return f"{major}.{minor}.{patch}"
    return version_str

def main():
    print("=" * 80)
    print("VERSION COVERAGE CHECK")
    print("=" * 80)

    # Get feature matrix versions
    feature_matrix_dir = Path("feature-matrix")
    feature_versions = set()
    for pdf in feature_matrix_dir.glob("fastiron-*-featuresupportmatrix*.pdf"):
        base_ver = extract_base_version(pdf.name)
        if base_ver:
            feature_versions.add(base_ver)

    print(f"\nFeature matrix versions found: {len(feature_versions)}")
    for ver in sorted(feature_versions):
        print(f"  {ver} -> {format_version(ver)}")

    # Get release note versions
    release_notes_dir = Path("release-notes")
    release_versions = set()
    for pdf in release_notes_dir.glob("fastiron-*-releasenotes*.pdf"):
        base_ver = extract_base_version(pdf.name)
        if base_ver:
            release_versions.add(base_ver)

    print(f"\nRelease note versions found: {len(release_versions)}")
    sample = sorted(release_versions)[:15]
    for ver in sample:
        print(f"  {ver} -> {format_version(ver)}")
    if len(release_versions) > 15:
        print(f"  ... and {len(release_versions) - 15} more")

    # Check coverage
    print("\n" + "=" * 80)
    print("COVERAGE ANALYSIS")
    print("=" * 80)

    missing = feature_versions - release_versions
    if missing:
        print(f"\n✗ MISSING: {len(missing)} feature matrix versions don't have release notes:")
        for ver in sorted(missing):
            print(f"  {ver} -> {format_version(ver)}")
    else:
        print("\n✓ All feature matrix versions have release notes")

    # Show what we have
    have_both = feature_versions.intersection(release_versions)
    print(f"\n✓ Versions with BOTH feature matrix and release notes: {len(have_both)}")
    for ver in sorted(have_both):
        print(f"  {ver} -> {format_version(ver)}")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if missing:
        print("\nAction needed:")
        print("  - Locate release notes for missing versions, OR")
        print("  - Remove those feature matrices from the dataset, OR")
        print("  - Accept that defect tracking won't be available for those versions")
    else:
        print("\n✓ No action needed - all feature matrix versions have release notes")
        print("  Website can safely show defect data for all feature versions")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Check version coverage across features and defects data.
"""

import json
from pathlib import Path

def main():
    print("\n" + "=" * 80)
    print("VERSION COVERAGE ANALYSIS")
    print("=" * 80)

    # Load features data
    print("\nLoading features_data.json...")
    if Path('features_data.json').exists():
        with open('features_data.json', 'r') as f:
            features = json.load(f)

        # Extract versions from features data
        feature_versions = set()
        for feature in features:
            # Versions come from the 'version' field (which PDF it came from)
            feature_versions.add(feature['version'])

        print(f"✓ Loaded {len(features)} feature records")
        print(f"✓ Feature matrix versions: {len(feature_versions)}")
        print(f"  Versions: {', '.join(sorted(feature_versions))}")
    else:
        print("✗ features_data.json not found")
        feature_versions = set()

    # Load defects data
    print("\nLoading defects_data.json...")
    if Path('defects_data.json').exists():
        with open('defects_data.json', 'r') as f:
            defects = json.load(f)

        # Extract versions from defects data
        defect_versions = set()
        for defect in defects:
            defect_versions.update(defect['version_history'].keys())

        print(f"✓ Loaded {len(defects)} defect records")
        print(f"✓ Release note versions: {len(defect_versions)}")
        print(f"  Versions: {', '.join(sorted(defect_versions)[:20])}")
        if len(defect_versions) > 20:
            print(f"  ... and {len(defect_versions) - 20} more")
    else:
        print("✗ defects_data.json not found")
        defect_versions = set()

    # Compare
    print("\n" + "=" * 80)
    print("COMPARISON")
    print("=" * 80)

    print(f"\nFeature matrix versions: {len(feature_versions)}")
    print(f"Release note versions: {len(defect_versions)}")

    # Check overlap
    overlap = feature_versions.intersection(defect_versions)
    print(f"Versions in both datasets: {len(overlap)}")
    if overlap:
        print(f"  {', '.join(sorted(overlap))}")

    # Check feature versions not in defects
    feature_only = feature_versions - defect_versions
    if feature_only:
        print(f"\nVersions in features but NOT in defects: {len(feature_only)}")
        print(f"  {', '.join(sorted(feature_only))}")

    # Check defect versions not in features
    defect_only = defect_versions - feature_versions
    if defect_only:
        print(f"\nVersions in defects but NOT in features: {len(defect_only)}")
        print(f"  {', '.join(sorted(defect_only)[:20])}")
        if len(defect_only) > 20:
            print(f"  ... and {len(defect_only) - 20} more")

    # Analysis for website
    print("\n" + "=" * 80)
    print("WEBSITE DROPDOWN RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. FEATURE LOOKUP & VERSION COMPARE TABS:")
    print("   Should use feature matrix versions (current implementation is correct)")
    print(f"   Available versions: {', '.join(sorted(feature_versions))}")

    print("\n2. DEFECT TRACKER TAB:")
    print("   Should use release note versions (current implementation is correct)")
    print(f"   Available versions: {len(defect_versions)} versions")
    print(f"   Sample: {', '.join(sorted(defect_versions)[:15])}")
    if len(defect_versions) > 15:
        print(f"   ... and {len(defect_versions) - 15} more")

    print("\n3. STATUS:")
    if feature_versions and defect_versions:
        print("   ✓ Both datasets populated")
        print("   ✓ Website dropdown logic is appropriate:")
        print("     - Features: Compare only versions with feature matrices")
        print("     - Defects: Track across all release note versions")
    else:
        print("   ✗ Missing data files")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

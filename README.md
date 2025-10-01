# RUCKUS FastIron Feature Navigator

An interactive web application for exploring FastIron switch features, bug fixes, and release notes across different hardware platforms and software versions.

🔗 **Live Site:** [https://neuralconfig.github.io/fastiron-features/](https://neuralconfig.github.io/fastiron-features/)

## ⚠️ Work in Progress

This tool is currently under development and the data extraction may be incomplete or contain errors. **Always refer to the official [RUCKUS FastIron documentation](https://support.ruckuswireless.com/) as the authoritative source of truth** for feature support, compatibility, and release information.

This is an unofficial community tool designed to help navigate and search FastIron documentation more easily.

## Features

### 📊 Feature Lookup
- Search through all FastIron features
- Filter by platform (ICX 7150, 7250, 7450, 7650, 7850, 8200)
- See which version introduced each feature

### 🔄 Version Compare
- Compare features between any two FastIron versions
- See what was added, removed, or changed
- Detailed side-by-side comparison

### 🐛 Bug Tracker
- Search **2,500+ bug fixes and known issues**
- Filter by status (Fixed/Known) and version
- View symptoms, conditions, workarounds, and recovery steps
- Search by issue ID, symptom, or technology group

### 📋 Release Notes
- View what's new in each FastIron version
- New hardware models, software features, CLI commands
- RFCs, MIBs, and deprecated commands

### 🔄 Upgrade Path Analyzer
- Analyze upgrade impact between versions
- See all bugs fixed during upgrade
- Review known issues in target version
- Make informed upgrade decisions

## Data Sources

The application extracts data from official RUCKUS FastIron PDFs:
- Feature Support Matrix documents
- Release Notes documents

### Current Coverage
- **Versions:** 8.0.90 through 10.0.20
- **Features:** 1,000+ features tracked
- **Issues:** 2,500+ bugs and known issues
- **Platforms:** ICX 7150, 7250, 7450, 7650, 7850, 8200

## Data Files

- `features_data.json` (1.7MB) - Feature support matrix
- `issues_data.json` (1.9MB) - Bug fixes and known issues
- `release_features_data.json` (117KB) - Release notes data

## Updating Data

To regenerate data from updated PDFs:

1. Place new PDF files in `release-notes/` directory:
   - `fastiron-XXXXX-featuresupportmatrix.pdf`
   - `fastiron-XXXXX-releasenotes-X.X.pdf`

2. Run extraction scripts:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install pdfplumber

python extract_features.py           # Updates features_data.json
python extract_issues.py             # Updates issues_data.json
python extract_release_features.py   # Updates release_features_data.json
```

3. Commit and push the updated JSON files

## Technical Details

- **Pure client-side application** - No server required
- **Framework:** Vanilla JavaScript
- **Data format:** JSON
- **Hosting:** GitHub Pages
- **PDF Parsing:** pdfplumber (Python)

## Project Structure

```
fastiron-features/
├── index.html                      # Main web application
├── features_data.json              # Feature support data
├── issues_data.json                # Bug tracking data
├── release_features_data.json      # Release notes data
├── extract_features.py             # Feature extraction script
├── extract_issues.py               # Issue extraction script
├── extract_release_features.py     # Release notes extraction script
└── README.md                       # This file
```

## Browser Compatibility

Works in all modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari

## License

Data extracted from official RUCKUS documentation. This tool is for informational purposes only.

## Disclaimer

This is an **unofficial tool**. All information should be verified against official RUCKUS documentation. For official support and documentation, visit [RUCKUS Support](https://support.ruckuswireless.com/).

---

**Maintained by:** NeuralConfig
**Last Updated:** September 2025

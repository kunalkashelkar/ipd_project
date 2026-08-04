# Datasets

Benchmark datasets for training and evaluating the vulnerability detection models.

## Supported Datasets

| Dataset | Language | Granularity | Vulnerabilities | Source |
|---------|----------|-------------|-----------------|--------|
| **Big-Vul** | C/C++ | Function-level | 188 CWE types | [GitHub](https://github.com/ZeoVan/MSR_20_Code_Vulnerability_CSV_Dataset) |
| **Devign** | C | Function-level | Mixed | [GitHub](https://github.com/epicosy/devign) |
| **SARD** | C/C++ | Program-level | NIST test cases | [NIST](https://samate.nist.gov/SARD/) |
| **D2A** | C/C++ | Function-level | Real-world | [IBM](https://github.com/nicholaschenai/d2a-leaderboard) |

## Quickstart: Automatic Downloading
A centralized Python script is provided to pull these down programmatically from Hugging Face and NIST databases.

```bash
# Navigate to datasets folder
cd datasets

# Download all datasets (WARNING: Can consume ~10GB+)
python download.py --datasets all

# Download specific datasets only
python download.py --datasets bigvul juliet

# Run in --dev-mode (Limits HF datasets to 10k slices for testing)
python download.py --datasets all --dev-mode
```

## Directory Structure

```text
datasets/
├── raw/            # Original unprocessed downloads (created by script)
│   ├── juliet/
│   ├── bigvul.jsonl
│   └── devign.jsonl
├── processed/      # Cleaned, tokenized, graph-ready data
├── splits/         # Train / validation / test splits
├── download.py     # Central CLI Downloader
└── README.md
```

## Notes

- Large dataset files (CSVs, jsonls, pickles) are excluded from Git via `.gitignore`.
- Preprocessing integration into the main parsing/backend servers will be handled locally.

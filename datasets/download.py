# ============================================================
# Datasets Bulk Downloader
# ============================================================
import argparse
from pathlib import Path
from loguru import logger
from downloaders.hf_downloader import HuggingFaceDownloader
from downloaders.nist_downloader import NISTDownloader

def main():
    parser = argparse.ArgumentParser(description="Download Vuln Detection Datasets")
    parser.add_argument(
        "--datasets", 
        nargs="+",
        choices=["bigvul", "devign", "diversevul", "juliet", "all"],
        default=["all"],
        help="Which datasets to download"
    )
    parser.add_argument(
        "--dev-mode",
        action="store_true",
        help="Limit huggingface datasets to 10,000 samples for fast dev iteration."
    )
    args = parser.parse_args()
    
    datasets = args.datasets
    if "all" in datasets:
        datasets = ["bigvul", "devign", "diversevul", "juliet"]
        
    raw_dir = Path("./raw")
    
    logger.info(f"Starting dataset acquisition into {raw_dir.absolute()}...")
    
    hf = HuggingFaceDownloader(raw_dir)
    nist = NISTDownloader(raw_dir)
    
    if "bigvul" in datasets:
        hf.download_bigvul(dev_mode=args.dev_mode)
    if "devign" in datasets:
        hf.download_devign(dev_mode=args.dev_mode)
    if "diversevul" in datasets:
        hf.download_diversevul(dev_mode=args.dev_mode)
        
    if "juliet" in datasets:
        nist.download_juliet()
        
    logger.info("Dataset acquisition complete. Ensure files are preprocessed before ingestion by Joern.")

if __name__ == "__main__":
    main()

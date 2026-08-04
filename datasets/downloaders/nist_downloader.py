# ============================================================
# NIST SARD (Juliet) Downloader
# ============================================================
import os
import requests
import zipfile
from pathlib import Path
from tqdm import tqdm
from loguru import logger

JULIET_URL = "https://samate.nist.gov/SARD/downloads/test-suites/2017-10-01-juliet-test-suite-for-c-cplusplus-v1-3.zip"

class NISTDownloader:
    """Downloads and unzips Juliet baseline datasets."""
    
    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.juliet_dir = self.raw_dir / "juliet"
        self.juliet_dir.mkdir(parents=True, exist_ok=True)
        
    def download_juliet(self):
        zip_path = self.juliet_dir / "juliet_v1.3.zip"
        
        if zip_path.exists():
            logger.info(f"Juliet zip already exists at {zip_path}")
        else:
            logger.info(f"Downloading Juliet from {JULIET_URL}...")
            response = requests.get(JULIET_URL, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(zip_path, 'wb') as file, tqdm(
                    desc=zip_path.name,
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                for data in response.iter_content(chunk_size=1024):
                    size = file.write(data)
                    bar.update(size)
                    
        # Unzip
        extract_dir = self.juliet_dir / "extracted"
        if not extract_dir.exists():
            logger.info(f"Extracting to {extract_dir}...")
            extract_dir.mkdir()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # We can limit the extraction for dev if necessary, but Juliet isn't that large zipped
                zip_ref.extractall(extract_dir)
            logger.info("Extraction complete.")
        else:
            logger.info("Juliet already extracted.")

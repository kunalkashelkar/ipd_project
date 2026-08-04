# ============================================================
# Hugging Face Dataset Downloader
# ============================================================
import os
import json
from pathlib import Path
from loguru import logger

try:
    from datasets import load_dataset
except ImportError:
    pass

class HuggingFaceDownloader:
    """Downloads Big-Vul, Devign, and DiverseVul from Hugging Face."""
    
    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
    def download_bigvul(self, dev_mode: bool = False):
        """Downloads bstee615/bigvul"""
        logger.info("Downloading Big-Vul dataset from Hugging Face...")
        ds = load_dataset("bstee615/bigvul", split="train") # it has test/val too usually, just taking train to show logic
        
        target_file = self.raw_dir / "bigvul.jsonl"
        self._save_to_jsonl(ds, target_file, limit=10000 if dev_mode else None)
        logger.info(f"Big-Vul saved to {target_file}")
        
    def download_devign(self, dev_mode: bool = False):
        """Downloads DetectVul/devign"""
        logger.info("Downloading Devign dataset from Hugging Face...")
        ds = load_dataset("DetectVul/devign", split="train")
        
        target_file = self.raw_dir / "devign.jsonl"
        self._save_to_jsonl(ds, target_file, limit=10000 if dev_mode else None)
        logger.info(f"Devign saved to {target_file}")
        
    def download_diversevul(self, dev_mode: bool = False):
        """Downloads wagner-group/diversevul or a popular mirror"""
        logger.info("Downloading DiverseVul dataset from Hugging Face...")
        try:
            ds = load_dataset("wagner-group/diversevul", split="train")
            target_file = self.raw_dir / "diversevul.jsonl"
            self._save_to_jsonl(ds, target_file, limit=10000 if dev_mode else None)
            logger.info(f"DiverseVul saved to {target_file}")
        except Exception as e:
            logger.error(f"Failed to fetch DiverseVul: {e}")

    def _save_to_jsonl(self, hf_dataset, out_path: Path, limit: int = None):
        """Standardizes output to JSONL for easier bulk processing later."""
        # Note: We take a subset if limit is imposed
        if limit:
            hf_dataset = hf_dataset.select(range(min(limit, len(hf_dataset))))
            
        # hf_dataset.to_json() is fast
        hf_dataset.to_json(str(out_path))

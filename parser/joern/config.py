# ============================================================
# Joern Integration — Configuration
# ============================================================

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class JoernConfig(BaseSettings):
    """Joern CLI configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Home directory of Joern CLI installation
    joern_home: str = "/opt/joern"

    # Maximum time (seconds) to wait for joern-parse or joern-export
    joern_timeout: int = 300

    # Directory where generated graphs are stored
    graph_output_dir: str = "./graphs"

    @property
    def joern_cli_dir(self) -> Path:
        return Path(self.joern_home) / "joern-cli"

    @property
    def parse_bin(self) -> Path:
        """Path to the joern-parse binary."""
        return self.joern_cli_dir / "joern-parse"

    @property
    def export_bin(self) -> Path:
        """Path to the joern-export binary."""
        return self.joern_cli_dir / "joern-export"

    @property
    def graphs_path(self) -> Path:
        p = Path(self.graph_output_dir)
        if not p.is_absolute():
            p = _PROJECT_ROOT / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    def is_joern_available(self) -> bool:
        """Return True if both CLI binaries exist and are executable."""
        return self.parse_bin.exists() and self.export_bin.exists()


_config: JoernConfig | None = None


def get_joern_config() -> JoernConfig:
    """Return a cached JoernConfig instance."""
    global _config
    if _config is None:
        _config = JoernConfig()
    return _config

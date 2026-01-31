"""Application settings and configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Application configuration settings.

    Settings can be overridden via environment variables with ASTRAEUS_ prefix.
    Example: ASTRAEUS_MAX_REACT_ITERATIONS=20
    """

    # Project paths
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent
    )
    data_dir: Optional[Path] = Field(default=None)
    output_dir: Optional[Path] = Field(default=None)

    # Agent configuration
    max_react_iterations: int = Field(default=10, ge=1, le=100)
    agent_timeout_seconds: int = Field(default=300, ge=1)
    enable_reasoning_traces: bool = Field(default=True)

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    log_reasoning_traces: bool = Field(default=True)

    # Validation settings
    strict_validation: bool = Field(default=True)
    allow_orphaned_elements: bool = Field(default=False)

    # Timeline generation
    default_work_hours_per_day: int = Field(default=8, ge=1, le=24)
    default_work_days_per_week: int = Field(default=5, ge=1, le=7)

    # Critical path analysis
    critical_path_buffer_percent: float = Field(default=10.0, ge=0, le=100)

    class Config:
        """Pydantic configuration."""
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        """Initialize computed paths after model creation."""
        if self.data_dir is None:
            object.__setattr__(self, 'data_dir', self.project_root / "data")
        if self.output_dir is None:
            object.__setattr__(self, 'output_dir', self.data_dir / "atlas_iii" / "outputs")

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        env_settings = {}

        # Map environment variables to settings
        env_mapping = {
            "ASTRAEUS_MAX_REACT_ITERATIONS": ("max_react_iterations", int),
            "ASTRAEUS_AGENT_TIMEOUT_SECONDS": ("agent_timeout_seconds", int),
            "ASTRAEUS_ENABLE_REASONING_TRACES": ("enable_reasoning_traces", lambda x: x.lower() == "true"),
            "ASTRAEUS_LOG_LEVEL": ("log_level", str),
            "ASTRAEUS_STRICT_VALIDATION": ("strict_validation", lambda x: x.lower() == "true"),
            "ASTRAEUS_DATA_DIR": ("data_dir", Path),
            "ASTRAEUS_OUTPUT_DIR": ("output_dir", Path),
        }

        for env_var, (setting_name, converter) in env_mapping.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    env_settings[setting_name] = converter(value)
                except (ValueError, TypeError):
                    pass  # Use default if conversion fails

        return cls(**env_settings)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns settings initialized from environment variables.
    """
    return Settings.from_env()


def _get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def _get_data_dir() -> Path:
    """Get the data directory."""
    return _get_project_root() / "data"


def _get_output_dir() -> Path:
    """Get the default output directory."""
    return _get_data_dir() / "atlas_iii" / "outputs"


# Convenience exports - computed at import time
PROJECT_ROOT = _get_project_root()
DATA_DIR = _get_data_dir()
OUTPUT_DIR = _get_output_dir()

"""
Configuration management for Astraeus Apertura.

Handles environment variables, secrets, and configuration validation.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class Config:
    """Application configuration."""
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    
    # Database
    database_url: str = "sqlite:///astraeus.db"
    redis_url: Optional[str] = None
    
    # AWS
    aws_region: str = "us-east-1"
    s3_bucket: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Worker Configuration
    worker_threads: int = 4
    max_memory_mb: int = 4096
    
    # Dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8050
    
    # ANSYS
    ansys_version: str = "2024.1"
    ansys_non_graphical: bool = True
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load configuration from environment variables."""
        config = cls()
        
        # Environment
        config.environment = os.getenv('ENVIRONMENT', config.environment)
        config.debug = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')
        
        # API Keys
        config.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        config.openai_api_key = os.getenv('OPENAI_API_KEY')
        config.notion_api_key = os.getenv('NOTION_API_KEY')
        
        # Database
        config.database_url = os.getenv('DATABASE_URL', config.database_url)
        config.redis_url = os.getenv('REDIS_URL')
        
        # AWS
        config.aws_region = os.getenv('AWS_REGION', config.aws_region)
        config.s3_bucket = os.getenv('S3_BUCKET')
        
        # Logging
        config.log_level = os.getenv('LOG_LEVEL', config.log_level)
        config.log_file = os.getenv('LOG_FILE')
        
        # Worker
        worker_threads_str = os.getenv('WORKER_THREADS')
        if worker_threads_str:
            try:
                config.worker_threads = int(worker_threads_str)
            except ValueError:
                logger.warning(f"Invalid WORKER_THREADS value: {worker_threads_str}")
        
        # Dashboard
        config.dashboard_host = os.getenv('DASHBOARD_HOST', config.dashboard_host)
        dashboard_port_str = os.getenv('DASHBOARD_PORT')
        if dashboard_port_str:
            try:
                config.dashboard_port = int(dashboard_port_str)
            except ValueError:
                logger.warning(f"Invalid DASHBOARD_PORT value: {dashboard_port_str}")
        
        # ANSYS
        config.ansys_version = os.getenv('ANSYS_VERSION', config.ansys_version)
        config.ansys_non_graphical = os.getenv('ANSYS_NON_GRAPHICAL', '').lower() not in ('false', '0', 'no')
        
        return config
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check required settings based on environment
        if self.environment == 'production':
            if not self.anthropic_api_key and not self.openai_api_key:
                errors.append("At least one LLM API key required in production")
            
            if self.debug:
                errors.append("Debug mode should be disabled in production")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (with secrets masked)."""
        data = {
            'environment': self.environment,
            'debug': self.debug,
            'database_url': self._mask_secret(self.database_url),
            'aws_region': self.aws_region,
            'log_level': self.log_level,
            'worker_threads': self.worker_threads,
            'dashboard_port': self.dashboard_port,
        }
        
        # Add API key status (not values)
        data['anthropic_api_key_set'] = bool(self.anthropic_api_key)
        data['openai_api_key_set'] = bool(self.openai_api_key)
        data['notion_api_key_set'] = bool(self.notion_api_key)
        
        return data
    
    @staticmethod
    def _mask_secret(value: Optional[str]) -> str:
        """Mask sensitive values."""
        if not value:
            return "Not set"
        if len(value) <= 8:
            return "***"
        return value[:4] + "***" + value[-4:]


# Global configuration instance
config = Config.from_env()


def get_config() -> Config:
    """Get global configuration."""
    return config


def reload_config():
    """Reload configuration from environment."""
    global config
    config = Config.from_env()
    logger.info("Configuration reloaded")

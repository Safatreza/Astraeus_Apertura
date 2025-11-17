"""
Logging configuration for Astraeus Apertura.

Provides structured logging with rotation, error tracking, and cloud integration.
"""

import sys
import logging
from pathlib import Path
from typing import Optional
from loguru import logger

from astraeus.config import get_config


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    json_format: bool = False
):
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_format: Use JSON format for structured logging
    """
    config = get_config()
    
    # Use config values if not provided
    log_level = log_level or config.log_level
    log_file = log_file or config.log_file
    
    # Remove default logger
    logger.remove()
    
    # Console logging
    if json_format or config.environment == 'production':
        # Structured JSON logging for production
        logger.add(
            sys.stderr,
            format="{message}",
            level=log_level,
            serialize=True
        )
    else:
        # Human-readable logging for development
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=log_level,
            colorize=True
        )
    
    # File logging with rotation
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            rotation="100 MB",
            retention="30 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level
        )
    
    # Add exception logging
    logger.add(
        sys.stderr,
        level="ERROR",
        backtrace=True,
        diagnose=True,
        format="<red>{time:YYYY-MM-DD HH:mm:ss}</red> | <level>{level: <8}</level> | {message}"
    )
    
    logger.info(f"Logging configured: level={log_level}, file={log_file}")


def get_logger(name: str):
    """
    Get a logger instance.
    
    Args:
        name: Logger name
    
    Returns:
        Logger instance
    """
    return logger.bind(module=name)


# Setup logging on module import
config = get_config()
setup_logging()

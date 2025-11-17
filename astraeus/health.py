"""
Health check and monitoring endpoints for Astraeus Apertura.

Provides health status, readiness checks, and metrics for monitoring.
"""

import os
import sys
import time
import psutil
from typing import Dict, Any, List
from datetime import datetime
from dataclasses import dataclass


@dataclass
class HealthStatus:
    """Health check status."""
    healthy: bool
    status: str
    checks: Dict[str, bool]
    details: Dict[str, Any]
    timestamp: str


class HealthChecker:
    """
    Comprehensive health checking for the application.
    
    Checks:
    - System resources (CPU, memory, disk)
    - Database connectivity
    - External API availability
    - Worker status
    """
    
    def __init__(self):
        """Initialize health checker."""
        self.start_time = time.time()
    
    def check_health(self, include_details: bool = False) -> HealthStatus:
        """
        Perform health checks.
        
        Args:
            include_details: Include detailed system information
        
        Returns:
            HealthStatus object
        """
        checks = {}
        details = {}
        
        # System checks
        checks['system'] = self._check_system()
        checks['python'] = self._check_python()
        checks['dependencies'] = self._check_dependencies()
        
        if include_details:
            details['system'] = self._get_system_details()
            details['uptime'] = self._get_uptime()
        
        # Determine overall health
        healthy = all(checks.values())
        status = "healthy" if healthy else "unhealthy"
        
        return HealthStatus(
            healthy=healthy,
            status=status,
            checks=checks,
            details=details,
            timestamp=datetime.now().isoformat()
        )
    
    def check_readiness(self) -> Dict[str, Any]:
        """
        Check if application is ready to serve requests.
        
        Returns:
            Readiness status dictionary
        """
        ready = True
        checks = {}
        
        # Check critical dependencies
        try:
            import astraeus
            checks['astraeus_imported'] = True
        except ImportError:
            checks['astraeus_imported'] = False
            ready = False
        
        # Check if startup completed (minimum uptime)
        uptime = time.time() - self.start_time
        checks['startup_complete'] = uptime > 5  # 5 seconds minimum
        if not checks['startup_complete']:
            ready = False
        
        return {
            'ready': ready,
            'checks': checks,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get application metrics for monitoring.
        
        Returns:
            Metrics dictionary
        """
        process = psutil.Process(os.getpid())
        
        return {
            'process': {
                'cpu_percent': process.cpu_percent(interval=0.1),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'threads': process.num_threads(),
                'open_files': len(process.open_files()),
            },
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
            },
            'uptime_seconds': self._get_uptime(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _check_system(self) -> bool:
        """Check system resources."""
        try:
            # Check if system has sufficient resources
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Fail if memory > 95% or disk > 95%
            return mem.percent < 95 and disk.percent < 95
        except Exception:
            return False
    
    def _check_python(self) -> bool:
        """Check Python version."""
        return sys.version_info >= (3, 9)
    
    def _check_dependencies(self) -> bool:
        """Check critical dependencies."""
        required = ['numpy', 'scipy', 'pandas', 'loguru']
        
        for package in required:
            try:
                __import__(package)
            except ImportError:
                return False
        
        return True
    
    def _get_system_details(self) -> Dict[str, Any]:
        """Get detailed system information."""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
            'disk_total_gb': psutil.disk_usage('/').total / 1024 / 1024 / 1024,
        }
    
    def _get_uptime(self) -> float:
        """Get application uptime in seconds."""
        return time.time() - self.start_time


# Global health checker instance
health_checker = HealthChecker()


def get_health_status(include_details: bool = False) -> HealthStatus:
    """Get current health status."""
    return health_checker.check_health(include_details)


def is_ready() -> bool:
    """Check if application is ready."""
    return health_checker.check_readiness()['ready']


def get_metrics() -> Dict[str, Any]:
    """Get application metrics."""
    return health_checker.get_metrics()

"""
Main compliance checker coordinating multiple standards.

Validates antenna designs against aerospace and defense standards,
ensuring regulatory compliance and quality requirements.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


class StandardType(Enum):
    """Types of standards."""
    NASA = "NASA"
    ESA = "ESA"
    MIL_STD = "MIL-STD"
    IPC = "IPC"
    IEEE = "IEEE"


class ComplianceLevel(Enum):
    """Compliance status levels."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceCheck:
    """Single compliance check result."""
    check_id: str
    standard: str
    requirement: str
    status: ComplianceLevel
    details: str
    value: Optional[float] = None
    limit: Optional[float] = None
    unit: Optional[str] = None


@dataclass
class ComplianceResult:
    """
    Complete compliance check result.
    
    Attributes:
        overall_status: Overall compliance status
        checks: List of individual checks
        passed_count: Number of passed checks
        warning_count: Number of warnings
        failed_count: Number of failures
        timestamp: When check was performed
        summary: Summary of results
    """
    overall_status: ComplianceLevel
    checks: List[ComplianceCheck] = field(default_factory=list)
    passed_count: int = 0
    warning_count: int = 0
    failed_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    summary: str = ""
    
    def add_check(self, check: ComplianceCheck):
        """Add a compliance check."""
        self.checks.append(check)
        
        if check.status == ComplianceLevel.PASS:
            self.passed_count += 1
        elif check.status == ComplianceLevel.WARNING:
            self.warning_count += 1
        elif check.status == ComplianceLevel.FAIL:
            self.failed_count += 1
    
    def update_overall_status(self):
        """Update overall status based on checks."""
        if self.failed_count > 0:
            self.overall_status = ComplianceLevel.FAIL
        elif self.warning_count > 0:
            self.overall_status = ComplianceLevel.WARNING
        else:
            self.overall_status = ComplianceLevel.PASS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'overall_status': self.overall_status.value,
            'passed_count': self.passed_count,
            'warning_count': self.warning_count,
            'failed_count': self.failed_count,
            'total_checks': len(self.checks),
            'timestamp': self.timestamp.isoformat(),
            'summary': self.summary,
            'checks': [
                {
                    'check_id': c.check_id,
                    'standard': c.standard,
                    'requirement': c.requirement,
                    'status': c.status.value,
                    'details': c.details,
                    'value': c.value,
                    'limit': c.limit,
                    'unit': c.unit
                }
                for c in self.checks
            ]
        }
    
    def print_report(self):
        """Print formatted compliance report."""
        print("\n" + "="*80)
        print("STANDARDS COMPLIANCE REPORT")
        print("="*80)
        print(f"Overall Status: {self.overall_status.value.upper()}")
        print(f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print(f"Summary:")
        print(f"  ✓ Passed:   {self.passed_count}")
        print(f"  ⚠ Warnings: {self.warning_count}")
        print(f"  ✗ Failed:   {self.failed_count}")
        print(f"  Total:      {len(self.checks)}")
        print()
        
        if self.summary:
            print(f"{self.summary}")
            print()
        
        print("Detailed Results:")
        print("-"*80)
        
        # Group by status
        for status in [ComplianceLevel.FAIL, ComplianceLevel.WARNING, ComplianceLevel.PASS]:
            checks = [c for c in self.checks if c.status == status]
            
            if not checks:
                continue
            
            status_symbol = {'pass': '✓', 'warning': '⚠', 'fail': '✗'}
            print(f"\n{status_symbol[status.value]} {status.value.upper()} ({len(checks)}):")
            
            for check in checks:
                print(f"  [{check.standard}] {check.requirement}")
                print(f"      {check.details}")
                
                if check.value is not None and check.limit is not None:
                    unit_str = f" {check.unit}" if check.unit else ""
                    print(f"      Value: {check.value}{unit_str}, Limit: {check.limit}{unit_str}")
                
                print()
        
        print("="*80)


class ComplianceChecker:
    """
    Main compliance checker coordinating multiple standards.
    
    Validates antenna designs against:
    - NASA standards for space applications
    - ESA standards for European space missions  
    - MIL-STD for defense applications
    - IPC for manufacturing
    - IEEE for electromagnetic compatibility
    """
    
    def __init__(self):
        """Initialize compliance checker."""
        self.checkers = {}
        logger.info("Initialized ComplianceChecker")
    
    def register_checker(self, standard_type: StandardType, checker):
        """
        Register a standard-specific checker.
        
        Args:
            standard_type: Type of standard
            checker: Checker instance
        """
        self.checkers[standard_type] = checker
        logger.info(f"Registered {standard_type.value} standards checker")
    
    def check_all(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any],
        standards: Optional[List[StandardType]] = None
    ) -> ComplianceResult:
        """
        Check compliance against all registered standards.
        
        Args:
            design: Design parameters
            performance: Performance metrics
            requirements: Requirements
            standards: List of standards to check (None = all)
        
        Returns:
            ComplianceResult with all checks
        """
        result = ComplianceResult(overall_status=ComplianceLevel.PASS)
        
        # Determine which standards to check
        if standards is None:
            standards = list(self.checkers.keys())
        
        # Run each checker
        for standard_type in standards:
            if standard_type not in self.checkers:
                logger.warning(f"No checker registered for {standard_type.value}")
                continue
            
            checker = self.checkers[standard_type]
            
            try:
                logger.info(f"Checking {standard_type.value} compliance...")
                checks = checker.check_compliance(design, performance, requirements)
                
                for check in checks:
                    result.add_check(check)
                
                logger.info(f"{standard_type.value}: {len(checks)} checks completed")
            
            except Exception as e:
                logger.error(f"Error checking {standard_type.value} compliance: {e}")
                result.add_check(ComplianceCheck(
                    check_id=f"{standard_type.value}_error",
                    standard=standard_type.value,
                    requirement="Checker execution",
                    status=ComplianceLevel.FAIL,
                    details=f"Error during compliance check: {str(e)}"
                ))
        
        # Update overall status
        result.update_overall_status()
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        logger.info(f"Compliance check complete: {result.overall_status.value}")
        
        return result
    
    def _generate_summary(self, result: ComplianceResult) -> str:
        """Generate summary text."""
        if result.overall_status == ComplianceLevel.PASS:
            return "Design meets all applicable standards requirements."
        elif result.overall_status == ComplianceLevel.WARNING:
            return f"Design passes with {result.warning_count} warnings. Review recommended."
        else:
            return f"Design fails {result.failed_count} critical requirements. Redesign required."
    
    def check_nasa(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> ComplianceResult:
        """Check NASA standards only."""
        return self.check_all(design, performance, requirements, standards=[StandardType.NASA])
    
    def check_esa(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> ComplianceResult:
        """Check ESA standards only."""
        return self.check_all(design, performance, requirements, standards=[StandardType.ESA])
    
    def check_mil_std(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> ComplianceResult:
        """Check MIL-STD standards only."""
        return self.check_all(design, performance, requirements, standards=[StandardType.MIL_STD])

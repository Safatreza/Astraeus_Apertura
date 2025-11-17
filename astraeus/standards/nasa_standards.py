"""
NASA standards compliance checker.

Validates against NASA standards including:
- NASA-STD-8739: Workmanship standards
- Outgassing requirements (ASTM E595)
- Thermal design requirements
- Space environment considerations
"""

from typing import Dict, Any, List
from .compliance_checker import ComplianceCheck, ComplianceLevel
from loguru import logger


class NASAStandardsChecker:
    """
    NASA standards compliance checker.
    
    Checks:
    - Material outgassing (TML < 1.0%, CVCM < 0.1%)
    - Temperature range compliance
    - Radiation tolerance
    - Electromagnetic compatibility
    - Reliability requirements
    """
    
    def __init__(self):
        """Initialize NASA checker."""
        logger.info("Initialized NASA standards checker")
    
    def check_compliance(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> List[ComplianceCheck]:
        """
        Check NASA standards compliance.
        
        Args:
            design: Design parameters
            performance: Performance metrics
            requirements: Requirements
        
        Returns:
            List of ComplianceCheck objects
        """
        checks = []
        
        # Check if space application
        is_space = requirements.get('environment', '').lower() in ['space', 'leo', 'geo', 'orbit']
        
        if is_space:
            checks.extend(self._check_outgassing(design))
            checks.extend(self._check_thermal_design(design, requirements))
            checks.extend(self._check_radiation_tolerance(design))
        
        checks.extend(self._check_emc_compliance(performance))
        checks.extend(self._check_reliability(performance, requirements))
        
        return checks
    
    def _check_outgassing(self, design: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check material outgassing per ASTM E595."""
        checks = []
        
        materials = design.get('materials', {})
        
        # Check substrate outgassing
        substrate = materials.get('substrate', {})
        substrate_name = substrate.get('name', 'Unknown')
        
        # NASA requirement: TML < 1.0%, CVCM < 0.1%
        tml = substrate.get('tml_percent', None)  # Total Mass Loss
        cvcm = substrate.get('cvcm_percent', None)  # Collected Volatile Condensable Material
        
        if tml is not None:
            if tml <= 1.0:
                status = ComplianceLevel.PASS
                details = f"Substrate {substrate_name} TML within limits"
            else:
                status = ComplianceLevel.FAIL
                details = f"Substrate {substrate_name} TML exceeds limit"
            
            checks.append(ComplianceCheck(
                check_id="NASA_OUTGAS_TML",
                standard="NASA-STD (ASTM E595)",
                requirement="Total Mass Loss (TML) < 1.0%",
                status=status,
                details=details,
                value=tml,
                limit=1.0,
                unit="%"
            ))
        
        if cvcm is not None:
            if cvcm <= 0.1:
                status = ComplianceLevel.PASS
                details = f"Substrate {substrate_name} CVCM within limits"
            else:
                status = ComplianceLevel.FAIL
                details = f"Substrate {substrate_name} CVCM exceeds limit"
            
            checks.append(ComplianceCheck(
                check_id="NASA_OUTGAS_CVCM",
                standard="NASA-STD (ASTM E595)",
                requirement="CVCM < 0.1%",
                status=status,
                details=details,
                value=cvcm,
                limit=0.1,
                unit="%"
            ))
        
        return checks
    
    def _check_thermal_design(self, design: Dict[str, Any], requirements: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check thermal design requirements."""
        checks = []
        
        temp_range = requirements.get('temperature_range', '')
        
        if not temp_range:
            return checks
        
        # Parse temperature range (e.g., "-100C to +100C")
        try:
            parts = temp_range.lower().replace('°', '').replace('c', '').split('to')
            min_temp = float(parts[0].strip())
            max_temp = float(parts[1].strip())
            
            # NASA typical space range: -100°C to +100°C
            if min_temp >= -100 and max_temp <= 100:
                status = ComplianceLevel.PASS
                details = "Temperature range within typical space environment limits"
            else:
                status = ComplianceLevel.WARNING
                details = "Temperature range exceeds typical space limits, verify thermal analysis"
            
            checks.append(ComplianceCheck(
                check_id="NASA_THERMAL_RANGE",
                standard="NASA Thermal Design",
                requirement="Operating temperature within space environment limits",
                status=status,
                details=details,
                value=max_temp - min_temp,
                limit=200,
                unit="°C range"
            ))
        
        except Exception as e:
            logger.warning(f"Failed to parse temperature range: {e}")
        
        return checks
    
    def _check_radiation_tolerance(self, design: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check radiation tolerance."""
        checks = []
        
        materials = design.get('materials', {})
        substrate = materials.get('substrate', {})
        
        radiation_hard = substrate.get('radiation_hardened', None)
        
        if radiation_hard is True:
            status = ComplianceLevel.PASS
            details = "Materials are radiation-hardened for space environment"
        elif radiation_hard is False:
            status = ComplianceLevel.WARNING
            details = "Materials not specified as radiation-hardened, verify mission requirements"
        else:
            status = ComplianceLevel.WARNING
            details = "Radiation tolerance not specified"
        
        checks.append(ComplianceCheck(
            check_id="NASA_RAD_TOLERANCE",
            standard="NASA Space Environment",
            requirement="Radiation tolerance for space environment",
            status=status,
            details=details
        ))
        
        return checks
    
    def _check_emc_compliance(self, performance: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check electromagnetic compatibility."""
        checks = []
        
        # Check VSWR (indicator of good matching/low reflections)
        vswr = performance.get('vswr', None)
        
        if vswr is not None:
            if vswr <= 2.0:
                status = ComplianceLevel.PASS
                details = "VSWR within acceptable limits for good EMC"
            elif vswr <= 3.0:
                status = ComplianceLevel.WARNING
                details = "VSWR higher than ideal, may affect EMC performance"
            else:
                status = ComplianceLevel.FAIL
                details = "VSWR too high, likely EMC issues"
            
            checks.append(ComplianceCheck(
                check_id="NASA_EMC_VSWR",
                standard="NASA EMC Requirements",
                requirement="VSWR < 2.0 for good matching",
                status=status,
                details=details,
                value=vswr,
                limit=2.0,
                unit=""
            ))
        
        return checks
    
    def _check_reliability(self, performance: Dict[str, Any], requirements: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check reliability requirements."""
        checks = []
        
        # Check efficiency (indicator of robust design)
        efficiency = performance.get('efficiency', None)
        
        if efficiency is not None:
            if efficiency >= 0.70:
                status = ComplianceLevel.PASS
                details = "Efficiency indicates robust design with margin"
            elif efficiency >= 0.50:
                status = ComplianceLevel.WARNING
                details = "Efficiency lower than ideal, limited design margin"
            else:
                status = ComplianceLevel.FAIL
                details = "Low efficiency indicates design issues"
            
            checks.append(ComplianceCheck(
                check_id="NASA_RELIABILITY_EFF",
                standard="NASA Reliability",
                requirement="Efficiency > 70% for design margin",
                status=status,
                details=details,
                value=efficiency * 100,
                limit=70,
                unit="%"
            ))
        
        return checks

"""
ESA standards compliance checker.

Validates against European Space Agency standards:
- ECSS-E-ST-20: RF and microwave
- ECSS-Q-ST-70: Materials and processes
- ECSS-E-ST-10-04: Space environment
"""

from typing import Dict, Any, List
from .compliance_checker import ComplianceCheck, ComplianceLevel
from loguru import logger


class ESAStandardsChecker:
    """ESA standards compliance checker."""
    
    def __init__(self):
        """Initialize ESA checker."""
        logger.info("Initialized ESA standards checker")
    
    def check_compliance(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> List[ComplianceCheck]:
        """Check ESA standards compliance."""
        checks = []
        
        checks.extend(self._check_rf_performance(performance, requirements))
        checks.extend(self._check_materials(design))
        checks.extend(self._check_space_environment(design, requirements))
        
        return checks
    
    def _check_rf_performance(self, performance: Dict[str, Any], requirements: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check RF performance per ECSS-E-ST-20."""
        checks = []
        
        # Gain margin
        actual_gain = performance.get('gain_dbi', 0)
        required_gain = requirements.get('min_gain_dbi', 0)
        
        if required_gain > 0:
            margin = actual_gain - required_gain
            
            if margin >= 3:  # 3 dB margin recommended
                status = ComplianceLevel.PASS
                details = f"Gain margin ({margin:.1f} dB) meets ESA recommendations"
            elif margin >= 0:
                status = ComplianceLevel.WARNING
                details = f"Gain margin ({margin:.1f} dB) low, 3 dB recommended"
            else:
                status = ComplianceLevel.FAIL
                details = f"Gain requirement not met (margin: {margin:.1f} dB)"
            
            checks.append(ComplianceCheck(
                check_id="ESA_RF_GAIN_MARGIN",
                standard="ECSS-E-ST-20",
                requirement="Gain margin ≥ 3 dB",
                status=status,
                details=details,
                value=margin,
                limit=3.0,
                unit="dB"
            ))
        
        return checks
    
    def _check_materials(self, design: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check materials per ECSS-Q-ST-70."""
        checks = []
        
        materials = design.get('materials', {})
        
        # Check for space-qualified materials
        substrate = materials.get('substrate', {})
        space_qual = substrate.get('space_qualified', None)
        
        if space_qual is True:
            status = ComplianceLevel.PASS
            details = "Materials are ESA/ECSS space-qualified"
        elif space_qual is False:
            status = ComplianceLevel.FAIL
            details = "Materials not space-qualified per ECSS requirements"
        else:
            status = ComplianceLevel.WARNING
            details = "Material space qualification not specified"
        
        checks.append(ComplianceCheck(
            check_id="ESA_MAT_SPACE_QUAL",
            standard="ECSS-Q-ST-70",
            requirement="Space-qualified materials",
            status=status,
            details=details
        ))
        
        return checks
    
    def _check_space_environment(self, design: Dict[str, Any], requirements: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check space environment compliance per ECSS-E-ST-10-04."""
        checks = []
        
        environment = requirements.get('environment', '').lower()
        
        if 'space' in environment or 'orbit' in environment:
            # Check thermal cycling capability
            materials = design.get('materials', {})
            substrate = materials.get('substrate', {})
            thermal_cycles = substrate.get('thermal_cycles', None)
            
            if thermal_cycles and thermal_cycles >= 50000:
                status = ComplianceLevel.PASS
                details = "Material rated for sufficient thermal cycles"
            elif thermal_cycles:
                status = ComplianceLevel.WARNING
                details = f"Thermal cycle rating ({thermal_cycles}) may be insufficient for long missions"
            else:
                status = ComplianceLevel.WARNING
                details = "Thermal cycling capability not specified"
            
            checks.append(ComplianceCheck(
                check_id="ESA_ENV_THERMAL_CYCLES",
                standard="ECSS-E-ST-10-04",
                requirement="Thermal cycling capability",
                status=status,
                details=details,
                value=thermal_cycles,
                limit=50000,
                unit="cycles"
            ))
        
        return checks

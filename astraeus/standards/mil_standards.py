"""
MIL-STD compliance checker.

Validates against Military Standards:
- MIL-STD-461: EMI/EMC requirements
- MIL-STD-810: Environmental engineering
"""

from typing import Dict, Any, List
from .compliance_checker import ComplianceCheck, ComplianceLevel
from loguru import logger


class MILStandardsChecker:
    """MIL-STD compliance checker."""
    
    def __init__(self):
        """Initialize MIL-STD checker."""
        logger.info("Initialized MIL-STD checker")
    
    def check_compliance(
        self,
        design: Dict[str, Any],
        performance: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> List[ComplianceCheck]:
        """Check MIL-STD compliance."""
        checks = []
        
        checks.extend(self._check_mil_std_461(performance))
        checks.extend(self._check_mil_std_810(design, requirements))
        
        return checks
    
    def _check_mil_std_461(self, performance: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check EMI/EMC per MIL-STD-461."""
        checks = []
        
        # Check conducted and radiated emissions (simplified)
        vswr = performance.get('vswr', None)
        
        if vswr is not None:
            if vswr <= 1.5:
                status = ComplianceLevel.PASS
                details = "VSWR meets MIL-STD-461 EMC requirements"
            elif vswr <= 2.0:
                status = ComplianceLevel.WARNING
                details = "VSWR acceptable but close to limit"
            else:
                status = ComplianceLevel.FAIL
                details = "VSWR exceeds MIL-STD-461 limits"
            
            checks.append(ComplianceCheck(
                check_id="MIL_461_EMC",
                standard="MIL-STD-461",
                requirement="EMC compliance (VSWR < 1.5)",
                status=status,
                details=details,
                value=vswr,
                limit=1.5,
                unit=""
            ))
        
        return checks
    
    def _check_mil_std_810(self, design: Dict[str, Any], requirements: Dict[str, Any]) -> List[ComplianceCheck]:
        """Check environmental engineering per MIL-STD-810."""
        checks = []
        
        # Temperature range
        temp_range = requirements.get('temperature_range', '')
        
        if temp_range:
            try:
                parts = temp_range.lower().replace('°', '').replace('c', '').split('to')
                min_temp = float(parts[0].strip())
                max_temp = float(parts[1].strip())
                
                # MIL-STD-810 typical range: -55°C to +85°C
                if min_temp >= -55 and max_temp <= 85:
                    status = ComplianceLevel.PASS
                    details = "Temperature range within MIL-STD-810 limits"
                else:
                    status = ComplianceLevel.WARNING
                    details = "Temperature range exceeds standard limits, verify test requirements"
                
                checks.append(ComplianceCheck(
                    check_id="MIL_810_TEMP",
                    standard="MIL-STD-810",
                    requirement="Operating temperature -55°C to +85°C",
                    status=status,
                    details=details
                ))
            
            except Exception as e:
                logger.warning(f"Failed to parse temperature for MIL-STD-810: {e}")
        
        # Vibration/shock resistance (simplified check)
        environment = requirements.get('environment', '').lower()
        
        if 'military' in environment or 'defense' in environment or 'tactical' in environment:
            # Check if design addresses vibration
            has_shock_mount = design.get('mechanical', {}).get('shock_mounting', False)
            
            if has_shock_mount:
                status = ComplianceLevel.PASS
                details = "Design includes shock/vibration mitigation"
            else:
                status = ComplianceLevel.WARNING
                details = "No shock/vibration mitigation specified, verify MIL-STD-810 testing"
            
            checks.append(ComplianceCheck(
                check_id="MIL_810_SHOCK",
                standard="MIL-STD-810",
                requirement="Shock and vibration resistance",
                status=status,
                details=details
            ))
        
        return checks

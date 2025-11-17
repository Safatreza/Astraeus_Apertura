"""
Standards Compliance Checker Demonstration.

Shows how to validate antenna designs against NASA, ESA, and MIL-STD standards.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from astraeus.standards import (
    ComplianceChecker,
    StandardType,
    NASAStandardsChecker,
    ESAStandardsChecker,
    MILStandardsChecker
)


def example_space_antenna_nasa():
    """Example: LEO satellite antenna NASA compliance."""
    print("="*80)
    print("EXAMPLE 1: LEO Satellite Antenna - NASA Standards")
    print("="*80)
    print()
    
    # Design parameters
    design = {
        'name': 'LEO Satellite Patch Array',
        'type': 'patch_array',
        'frequency_ghz': 2.2,
        'materials': {
            'substrate': {
                'name': 'Rogers RO4003C',
                'tml_percent': 0.5,  # Total Mass Loss
                'cvcm_percent': 0.05,  # Collected Volatile Condensable Material
                'space_qualified': True,
                'radiation_hardened': True
            },
            'conductor': {
                'name': 'Copper with gold plating'
            }
        }
    }
    
    # Performance metrics
    performance = {
        'gain_dbi': 12.5,
        'vswr': 1.4,
        'efficiency': 0.78,
        'bandwidth_mhz': 100
    }
    
    # Requirements
    requirements = {
        'environment': 'LEO',
        'temperature_range': '-100C to +100C',
        'min_gain_dbi': 10.0
    }
    
    # Create compliance checker
    checker = ComplianceChecker()
    checker.register_checker(StandardType.NASA, NASAStandardsChecker())
    
    # Check compliance
    result = checker.check_nasa(design, performance, requirements)
    
    # Print report
    result.print_report()


def example_military_antenna():
    """Example: Tactical communications antenna MIL-STD compliance."""
    print("\n\n")
    print("="*80)
    print("EXAMPLE 2: Tactical Communications Antenna - MIL-STD")
    print("="*80)
    print()
    
    # Design parameters
    design = {
        'name': 'Tactical VHF Antenna',
        'type': 'whip',
        'frequency_ghz': 0.15,  # 150 MHz
        'materials': {
            'substrate': {
                'name': 'Fiberglass composite'
            }
        },
        'mechanical': {
            'shock_mounting': True
        }
    }
    
    # Performance metrics
    performance = {
        'gain_dbi': 2.5,
        'vswr': 1.3,
        'efficiency': 0.85,
        'bandwidth_mhz': 30
    }
    
    # Requirements
    requirements = {
        'environment': 'military tactical',
        'temperature_range': '-40C to +70C',
        'min_gain_dbi': 0.0
    }
    
    # Create compliance checker
    checker = ComplianceChecker()
    checker.register_checker(StandardType.MIL_STD, MILStandardsChecker())
    
    # Check compliance
    result = checker.check_mil_std(design, performance, requirements)
    
    # Print report
    result.print_report()


def example_multi_standard_check():
    """Example: Satellite ground terminal checked against multiple standards."""
    print("\n\n")
    print("="*80)
    print("EXAMPLE 3: Satellite Ground Terminal - NASA & ESA Standards")
    print("="*80)
    print()
    
    # Design parameters
    design = {
        'name': 'X-band Ground Terminal',
        'type': 'parabolic_reflector',
        'frequency_ghz': 8.4,
        'diameter_m': 2.4,
        'materials': {
            'substrate': {
                'name': 'Aluminum alloy',
                'space_qualified': True,
                'tml_percent': 0.3,
                'cvcm_percent': 0.02,
                'thermal_cycles': 100000
            }
        }
    }
    
    # Performance metrics
    performance = {
        'gain_dbi': 42.5,
        'vswr': 1.2,
        'efficiency': 0.65,  # Reflector typical
        'bandwidth_mhz': 500
    }
    
    # Requirements
    requirements = {
        'environment': 'space ground segment',
        'temperature_range': '-20C to +50C',
        'min_gain_dbi': 40.0
    }
    
    # Create compliance checker with multiple standards
    checker = ComplianceChecker()
    checker.register_checker(StandardType.NASA, NASAStandardsChecker())
    checker.register_checker(StandardType.ESA, ESAStandardsChecker())
    
    # Check all registered standards
    result = checker.check_all(design, performance, requirements)
    
    # Print report
    result.print_report()
    
    # Export to JSON
    import json
    report_data = result.to_dict()
    
    with open('compliance_report.json', 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print("\nCompliance report exported to: compliance_report.json")


def example_failing_design():
    """Example: Design that fails compliance checks."""
    print("\n\n")
    print("="*80)
    print("EXAMPLE 4: Non-Compliant Design - Demonstration of Failures")
    print("="*80)
    print()
    
    # Poor design parameters
    design = {
        'name': 'Non-Compliant Antenna',
        'type': 'patch',
        'frequency_ghz': 10.0,
        'materials': {
            'substrate': {
                'name': 'Standard FR4',
                'tml_percent': 2.5,  # Too high!
                'cvcm_percent': 0.5,  # Too high!
                'space_qualified': False,
                'radiation_hardened': False
            }
        }
    }
    
    # Poor performance
    performance = {
        'gain_dbi': 3.5,
        'vswr': 3.2,  # Too high!
        'efficiency': 0.35,  # Too low!
        'bandwidth_mhz': 50
    }
    
    # Demanding requirements
    requirements = {
        'environment': 'GEO',
        'temperature_range': '-150C to +150C',
        'min_gain_dbi': 8.0  # Not met!
    }
    
    # Check all standards
    checker = ComplianceChecker()
    checker.register_checker(StandardType.NASA, NASAStandardsChecker())
    checker.register_checker(StandardType.ESA, ESAStandardsChecker())
    
    result = checker.check_all(design, performance, requirements)
    
    # Print report
    result.print_report()


if __name__ == '__main__':
    print("\n")
    print("="*80)
    print("ANTENNA DESIGN STANDARDS COMPLIANCE DEMONSTRATION")
    print("="*80)
    print("\nDemonstrating validation against:")
    print("  - NASA standards (outgassing, thermal, EMC)")
    print("  - ESA/ECSS standards (RF performance, materials, space environment)")
    print("  - MIL-STD (EMC, environmental)")
    print()
    
    try:
        # Run all examples
        example_space_antenna_nasa()
        example_military_antenna()
        example_multi_standard_check()
        example_failing_design()
        
        print("\n\n")
        print("="*80)
        print("DEMONSTRATION COMPLETE")
        print("="*80)
        print("\nKey takeaways:")
        print("  ✓ Automated standards compliance checking")
        print("  ✓ Support for NASA, ESA, and MIL-STD requirements")
        print("  ✓ Detailed pass/warning/fail reporting")
        print("  ✓ Exportable compliance reports")
        print("  ✓ Early detection of non-compliant designs")
        print()
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

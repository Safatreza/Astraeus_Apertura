#!/usr/bin/env python3
"""Validate consistency across SE artifacts.

This script loads existing ATLAS-III artifacts and runs
comprehensive consistency checks, generating a detailed report.

Usage:
    python validate_artifact_consistency.py
    python validate_artifact_consistency.py --report output_report.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from artifacts.requirements import RequirementsSet
from artifacts.pbs import ProductBreakdownStructure
from artifacts.wbs import WorkBreakdownStructure
from tools.validation import (
    validate_requirements_completeness,
    validate_pbs_coverage,
    validate_wbs_derivation,
)
from tools.consistency_checker import (
    check_cross_artifact_consistency,
    verify_traceability,
    generate_consistency_summary,
)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def load_artifacts(data_dir: Path) -> dict:
    """Load all artifacts from baseline files."""
    atlas_dir = data_dir / "atlas_iii"

    artifacts = {}

    # Load requirements
    req_file = atlas_dir / "requirements_baseline.json"
    if req_file.exists():
        with open(req_file, "r") as f:
            data = json.load(f)
            artifacts["requirements"] = RequirementsSet(**data)

    # Load PBS
    pbs_file = atlas_dir / "pbs_baseline.json"
    if pbs_file.exists():
        with open(pbs_file, "r") as f:
            data = json.load(f)
            artifacts["pbs"] = ProductBreakdownStructure.from_dict(data)

    # Load WBS
    wbs_file = atlas_dir / "wbs_baseline.json"
    if wbs_file.exists():
        with open(wbs_file, "r") as f:
            data = json.load(f)
            artifacts["wbs"] = WorkBreakdownStructure.from_dict(data)

    return artifacts


def print_validation_result(name: str, result) -> None:
    """Print a validation result."""
    status = "PASS" if result.is_valid else "FAIL"
    print(f"\n{name}: [{status}]")
    print("-" * 40)

    if result.errors:
        print("Errors:")
        for error in result.errors[:5]:  # Limit output
            print(f"  - {error}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings[:5]:
            print(f"  - {warning}")
        if len(result.warnings) > 5:
            print(f"  ... and {len(result.warnings) - 5} more")

    if result.statistics:
        print("Statistics:")
        for key, value in result.statistics.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")


def print_traceability_matrix(matrix) -> None:
    """Print traceability matrix summary."""
    print("\n" + "=" * 70)
    print("TRACEABILITY MATRIX")
    print("=" * 70)

    summary = matrix.summary
    print(f"Total Requirements: {summary.get('total_requirements', 0)}")
    print(f"Complete Traceability: {summary.get('complete_traceability', 0)}")
    print(f"Incomplete Traceability: {summary.get('incomplete_traceability', 0)}")
    print(f"Completeness: {summary.get('completeness_percentage', 0):.1f}%")

    # Show incomplete entries
    incomplete = matrix.get_incomplete_entries()
    if incomplete:
        print("\nIncomplete Traceability:")
        for entry in incomplete[:10]:
            print(f"  {entry.requirement_id}:")
            print(f"    PBS: {entry.pbs_nodes or 'None'}")
            print(f"    WBS: {entry.work_packages or 'None'}")
        if len(incomplete) > 10:
            print(f"  ... and {len(incomplete) - 10} more")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate ATLAS-III artifact consistency"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Output report to JSON file",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory path",
    )

    args = parser.parse_args()
    setup_logging(logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger("astraeus.examples")

    # Paths
    project_root = Path(__file__).parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else project_root / "data"

    # Load artifacts
    print("\n" + "=" * 70)
    print("ARTIFACT CONSISTENCY VALIDATION")
    print("=" * 70)

    try:
        artifacts = load_artifacts(data_dir)
        logger.info(f"Loaded {len(artifacts)} artifacts")
    except Exception as e:
        logger.error(f"Failed to load artifacts: {e}")
        sys.exit(1)

    # Report what we loaded
    print("\nLoaded Artifacts:")
    if "requirements" in artifacts:
        print(f"  Requirements: {len(artifacts['requirements'])} items")
    if "pbs" in artifacts:
        print(f"  PBS: {len(artifacts['pbs'].nodes)} nodes")
    if "wbs" in artifacts:
        print(f"  WBS: {len(artifacts['wbs'].work_packages)} work packages")

    results = {}

    # Run individual validations
    print("\n" + "=" * 70)
    print("INDIVIDUAL VALIDATIONS")
    print("=" * 70)

    if "requirements" in artifacts:
        req_result = validate_requirements_completeness(artifacts["requirements"])
        results["requirements_completeness"] = req_result
        print_validation_result("Requirements Completeness", req_result)

    if "requirements" in artifacts and "pbs" in artifacts:
        pbs_result = validate_pbs_coverage(artifacts["pbs"], artifacts["requirements"])
        results["pbs_coverage"] = pbs_result
        print_validation_result("PBS Coverage", pbs_result)

    if "pbs" in artifacts and "wbs" in artifacts:
        wbs_result = validate_wbs_derivation(artifacts["wbs"], artifacts["pbs"])
        results["wbs_derivation"] = wbs_result
        print_validation_result("WBS Derivation", wbs_result)

    # Cross-artifact consistency
    print("\n" + "=" * 70)
    print("CROSS-ARTIFACT CONSISTENCY")
    print("=" * 70)

    consistency_report = check_cross_artifact_consistency(artifacts)
    results["consistency"] = consistency_report

    print(generate_consistency_summary(consistency_report))

    # Traceability matrix
    if all(k in artifacts for k in ["requirements", "pbs", "wbs"]):
        trace_matrix = verify_traceability(
            artifacts["requirements"],
            artifacts["pbs"],
            artifacts["wbs"],
        )
        results["traceability"] = trace_matrix
        print_traceability_matrix(trace_matrix)

    # Overall summary
    print("\n" + "=" * 70)
    print("OVERALL SUMMARY")
    print("=" * 70)

    all_valid = all(
        r.is_valid for r in results.values()
        if hasattr(r, "is_valid")
    )
    print(f"Overall Status: {'PASS' if all_valid else 'FAIL'}")

    # Save report if requested
    if args.report:
        report_data = {
            "validation_results": {
                name: result.model_dump() if hasattr(result, "model_dump") else str(result)
                for name, result in results.items()
            },
            "overall_valid": all_valid,
        }
        with open(args.report, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\nReport saved to: {args.report}")

    print("\n" + "=" * 70)
    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())

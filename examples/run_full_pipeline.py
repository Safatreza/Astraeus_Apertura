#!/usr/bin/env python3
"""Run the complete SE pipeline for ATLAS-III mission.

This script demonstrates the full workflow from mission inputs
through requirements, PBS, WBS, dependencies, to timeline.

Usage:
    python run_full_pipeline.py
    python run_full_pipeline.py --verbose
    python run_full_pipeline.py --output ./custom_output
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestration.workflow import SEWorkflow, WorkflowResult


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the pipeline run."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_mission_inputs(data_dir: Path) -> dict:
    """Load mission inputs from JSON file."""
    mission_file = data_dir / "atlas_iii" / "mission_inputs.json"
    with open(mission_file, "r") as f:
        return json.load(f)


def print_summary(result: WorkflowResult) -> None:
    """Print a formatted summary of the workflow result."""
    print("\n" + "=" * 70)
    print("ASTRAEUS APERTURA - WORKFLOW EXECUTION SUMMARY")
    print("=" * 70)
    print(f"\nMission: {result.mission_name}")
    print(f"Status:  {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Time:    {result.total_execution_time_seconds:.2f} seconds")

    print("\n" + "-" * 40)
    print("STAGE RESULTS:")
    print("-" * 40)
    for stage_name, stage_result in result.stage_results.items():
        status = "PASS" if stage_result.success else "FAIL"
        time_str = f"{stage_result.execution_time_seconds:.2f}s"
        print(f"  {stage_name:15} [{status}] ({time_str})")
        if stage_result.error:
            print(f"    Error: {stage_result.error}")

    print("\n" + "-" * 40)
    print("ARTIFACTS GENERATED:")
    print("-" * 40)

    summary = result.summary
    print(f"  Requirements:    {summary.get('total_requirements', 'N/A')}")
    print(f"  PBS Nodes:       {summary.get('total_pbs_nodes', 'N/A')}")
    print(f"  Work Packages:   {summary.get('total_work_packages', 'N/A')}")
    print(f"  Project End:     {summary.get('project_end_date', 'N/A')}")
    print(f"  Duration (days): {summary.get('project_duration_days', 'N/A')}")

    print("\n" + "=" * 70)


def print_artifact_details(result: WorkflowResult) -> None:
    """Print detailed artifact information."""
    artifacts = result.final_artifacts

    # Requirements breakdown
    if "requirements" in artifacts:
        reqs = artifacts["requirements"]
        print("\nREQUIREMENTS BREAKDOWN:")
        print("-" * 40)
        requirements_list = reqs.get("requirements", [])
        categories = {}
        for req in requirements_list:
            cat = req.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1
        for cat, count in sorted(categories.items()):
            print(f"  {cat:15}: {count}")

    # PBS structure
    if "pbs" in artifacts:
        pbs = artifacts["pbs"]
        print("\nPBS STRUCTURE:")
        print("-" * 40)
        nodes = pbs.get("nodes", {})
        levels = {}
        for node in nodes.values():
            level = node.get("level", 0)
            levels[level] = levels.get(level, 0) + 1
        for level, count in sorted(levels.items()):
            print(f"  Level {level}: {count} nodes")

        # Mission critical
        critical = sum(1 for n in nodes.values() if n.get("is_mission_critical"))
        print(f"  Mission Critical: {critical}")

    # WBS summary
    if "wbs" in artifacts:
        wbs = artifacts["wbs"]
        print("\nWBS SUMMARY:")
        print("-" * 40)
        work_packages = wbs.get("work_packages", {})
        work_types = {}
        total_effort = 0
        for wp in work_packages.values():
            wt = wp.get("work_type", "unknown")
            work_types[wt] = work_types.get(wt, 0) + 1
            total_effort += wp.get("effort_hours", 0)
        for wt, count in sorted(work_types.items()):
            print(f"  {wt:15}: {count} packages")
        print(f"  Total Effort: {total_effort:,} hours")

    # Timeline summary
    if "timeline" in artifacts:
        timeline = artifacts["timeline"]
        print("\nTIMELINE SUMMARY:")
        print("-" * 40)
        print(f"  Start Date: {timeline.get('start_date', 'N/A')}")
        print(f"  End Date:   {timeline.get('project_end_date', 'N/A')}")
        print(f"  Duration:   {timeline.get('total_duration_days', 0)} days")

        critical_path = timeline.get("critical_path", [])
        print(f"  Critical Path: {len(critical_path)} tasks")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Astraeus Apertura SE pipeline for ATLAS-III"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output directory for artifacts (default: data/atlas_iii/outputs)",
    )
    parser.add_argument(
        "-d", "--details",
        action="store_true",
        help="Print detailed artifact information",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Data directory (default: project data/)",
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.verbose)
    logger = logging.getLogger("astraeus.examples")

    # Determine paths
    project_root = Path(__file__).parent.parent
    data_dir = Path(args.data_dir) if args.data_dir else project_root / "data"

    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = data_dir / "atlas_iii" / "outputs"

    logger.info(f"Project root: {project_root}")
    logger.info(f"Data directory: {data_dir}")
    logger.info(f"Output directory: {output_dir}")

    # Load mission inputs
    try:
        mission_inputs = load_mission_inputs(data_dir)
        logger.info(f"Loaded mission inputs for: {mission_inputs.get('mission_name')}")
    except Exception as e:
        logger.error(f"Failed to load mission inputs: {e}")
        sys.exit(1)

    # Run workflow
    print("\n" + "=" * 70)
    print("STARTING ASTRAEUS APERTURA PIPELINE")
    print("=" * 70)
    print(f"Mission: {mission_inputs.get('mission_name')}")
    print(f"Launch Target: {mission_inputs.get('launch_target')}")
    print(f"Objective: {mission_inputs.get('primary_objective')}")
    print("=" * 70 + "\n")

    workflow = SEWorkflow(output_dir=output_dir)
    result = workflow.run_pipeline(mission_inputs)

    # Print results
    print_summary(result)

    if args.details:
        print_artifact_details(result)

    # Final status
    if result.success:
        print(f"\nArtifacts saved to: {output_dir}")
        print("\nPipeline completed successfully!")
        return 0
    else:
        print(f"\nPipeline failed: {result.summary.get('error', 'Unknown error')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

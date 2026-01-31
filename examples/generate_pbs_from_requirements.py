#!/usr/bin/env python3
"""Demonstrate single-stage execution: PBS generation from requirements.

This script shows how to use the DecompositionAgent to generate
a Product Breakdown Structure from requirements, displaying the
reasoning trace throughout the process.

Usage:
    python generate_pbs_from_requirements.py
    python generate_pbs_from_requirements.py --show-trace
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.base_agent import Task
from agents.decomposition_agent import DecompositionAgent
from orchestration.react_loop import ReActLoop


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )


def load_requirements(data_dir: Path) -> dict:
    """Load requirements from baseline file."""
    req_file = data_dir / "atlas_iii" / "requirements_baseline.json"
    with open(req_file, "r") as f:
        return json.load(f)


def print_trace(trace: list) -> None:
    """Print formatted reasoning trace."""
    print("\n" + "=" * 70)
    print("REASONING TRACE")
    print("=" * 70)

    for entry in trace:
        iteration = entry.get("iteration", "?")
        thought = entry.get("thought", {})
        action = entry.get("action", {})
        observation = entry.get("observation", {})

        print(f"\n--- Iteration {iteration} ---")
        print(f"THOUGHT: {thought.get('content', 'N/A')[:200]}...")
        print(f"RATIONALE: {thought.get('next_action_rationale', 'N/A')}")

        if action:
            print(f"ACTION: {action.get('tool_name', 'N/A')}")
            params = action.get("parameters", {})
            if params:
                param_str = json.dumps(params, default=str)[:100]
                print(f"PARAMS: {param_str}...")

        if observation:
            status = "SUCCESS" if observation.get("success") else "FAILED"
            print(f"RESULT: {status}")
            if observation.get("error"):
                print(f"ERROR: {observation['error']}")


def print_pbs_tree(pbs: dict) -> None:
    """Print PBS as a tree structure."""
    print("\n" + "=" * 70)
    print("GENERATED PBS STRUCTURE")
    print("=" * 70)

    nodes = pbs.get("nodes", {})
    root_id = pbs.get("root_id")

    def print_node(node_id: str, indent: int = 0) -> None:
        node = nodes.get(node_id)
        if not node:
            return

        prefix = "  " * indent
        name = node.get("name", "Unknown")
        critical = " [CRITICAL]" if node.get("is_mission_critical") else ""
        print(f"{prefix}{node_id}: {name}{critical}")

        for child_id in node.get("children", []):
            print_node(child_id, indent + 1)

    if root_id:
        print_node(root_id)
    else:
        print("No root node defined")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate PBS from requirements with reasoning trace"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--show-trace",
        action="store_true",
        help="Display full reasoning trace",
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

    # Load requirements
    try:
        requirements = load_requirements(data_dir)
        logger.info(f"Loaded {len(requirements.get('requirements', []))} requirements")
    except Exception as e:
        logger.error(f"Failed to load requirements: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("PBS GENERATION FROM REQUIREMENTS")
    print("=" * 70)
    print(f"Mission: {requirements.get('mission_name')}")
    print(f"Requirements: {len(requirements.get('requirements', []))}")
    print("=" * 70)

    # Create agent and task
    agent = DecompositionAgent(
        name="DecompositionDemo",
        max_iterations=10,
        trace_enabled=True,
    )

    task = Task(
        id="demo-pbs-generation",
        name="Generate PBS from Requirements",
        description="Create Product Breakdown Structure from mission requirements",
        inputs={
            "mission_name": requirements.get("mission_name", "ATLAS-III"),
            "requirements_set": requirements,
        },
    )

    # Execute with ReAct loop
    react_loop = ReActLoop(
        agent=agent,
        max_iterations=10,
        trace_enabled=True,
    )

    print("\nExecuting DecompositionAgent...")
    result = react_loop.execute(task)

    # Show results
    print("\n" + "-" * 40)
    print(f"Execution Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Execution Time: {result.execution_time_seconds:.2f}s")
    print(f"Iterations: {len(result.thoughts)}")

    if result.error:
        print(f"Error: {result.error}")

    # Show trace if requested
    if args.show_trace:
        trace = react_loop.get_trace_as_dicts()
        print_trace(trace)

    # Show PBS result
    if "pbs" in result.outputs:
        print_pbs_tree(result.outputs["pbs"])

        # Summary
        pbs = result.outputs["pbs"]
        nodes = pbs.get("nodes", {})
        print("\n" + "-" * 40)
        print("SUMMARY:")
        print(f"  Total Nodes: {len(nodes)}")
        print(f"  Mission Critical: {sum(1 for n in nodes.values() if n.get('is_mission_critical'))}")

        if "pbs_summary" in result.outputs:
            summary = result.outputs["pbs_summary"]
            print(f"  Leaf Nodes: {summary.get('total_leaves', 'N/A')}")

    # WBS summary if available
    if "wbs" in result.outputs:
        wbs = result.outputs["wbs"]
        wp_count = len(wbs.get("work_packages", {}))
        print(f"\nWBS Generated: {wp_count} work packages")

    print("\n" + "=" * 70)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())

"""Product Breakdown Structure (PBS) artifact models.

This module defines the hierarchical data structures for representing
the physical decomposition of the ATLAS-III space segment.
"""

import json
from typing import Any, Callable, Dict, Iterator, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class PBSNode(BaseModel):
    """A node in the Product Breakdown Structure.

    Represents a physical element of the space system at any level
    of the hierarchy (system, subsystem, component, etc.).

    Attributes:
        id: Unique hierarchical identifier (e.g., "PBS-1.1.1").
        name: Short descriptive name.
        description: Detailed description of the element.
        parent_id: ID of the parent node (None for root).
        level: Depth in the hierarchy (0 = root).
        children: List of child node IDs.
        allocated_requirements: Requirement IDs allocated to this element.
        mass_kg: Estimated mass in kilograms.
        power_w: Estimated power consumption in watts.
        is_mission_critical: Whether this element is mission-critical.
        heritage: Technology heritage level (1=flight-proven, 2=modified, 3=new).
    """

    id: str = Field(..., pattern=r"^PBS-[0-9.]+$")
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    parent_id: Optional[str] = Field(default=None, pattern=r"^PBS-[0-9.]+$")
    level: int = Field(default=0, ge=0, le=10)
    children: List[str] = Field(default_factory=list)
    allocated_requirements: List[str] = Field(default_factory=list)
    mass_kg: Optional[float] = Field(default=None, ge=0)
    power_w: Optional[float] = Field(default=None, ge=0)
    is_mission_critical: bool = Field(default=False)
    heritage: int = Field(default=3, ge=1, le=3)

    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate PBS ID follows hierarchical numbering."""
        parts = v.replace("PBS-", "").split(".")
        for part in parts:
            if not part.isdigit():
                raise ValueError(f"Invalid PBS ID format: {v}")
        return v

    def get_level_from_id(self) -> int:
        """Infer level from ID structure."""
        parts = self.id.replace("PBS-", "").split(".")
        return len(parts) - 1

    def is_leaf(self) -> bool:
        """Check if this node has no children."""
        return len(self.children) == 0

    def is_root(self) -> bool:
        """Check if this node is the root."""
        return self.parent_id is None


class ProductBreakdownStructure(BaseModel):
    """Complete Product Breakdown Structure tree.

    Represents the full hierarchical decomposition of the space system
    from the top-level segment down to individual components.

    Attributes:
        mission_name: Name of the mission.
        version: PBS version identifier.
        root_id: ID of the root node.
        nodes: Dictionary mapping node IDs to PBSNode objects.
    """

    mission_name: str
    version: str = Field(default="1.0")
    root_id: Optional[str] = Field(default=None, pattern=r"^PBS-[0-9.]+$")
    nodes: Dict[str, PBSNode] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tree_structure(self) -> "ProductBreakdownStructure":
        """Validate the tree structure integrity."""
        if not self.nodes:
            return self

        # Validate root exists
        if self.root_id and self.root_id not in self.nodes:
            raise ValueError(f"Root node {self.root_id} not found in nodes")

        # Validate parent references
        for node_id, node in self.nodes.items():
            if node.parent_id and node.parent_id not in self.nodes:
                raise ValueError(
                    f"Node {node_id} references non-existent parent {node.parent_id}"
                )

        # Validate child references
        for node_id, node in self.nodes.items():
            for child_id in node.children:
                if child_id not in self.nodes:
                    raise ValueError(
                        f"Node {node_id} references non-existent child {child_id}"
                    )

        return self

    def add_node(self, node: PBSNode) -> None:
        """Add a node to the structure."""
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists")

        self.nodes[node.id] = node

        # Set as root if first node or no parent
        if self.root_id is None and node.parent_id is None:
            self.root_id = node.id

        # Update parent's children list
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.children:
                parent.children.append(node.id)

    def get_node(self, node_id: str) -> Optional[PBSNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> List[PBSNode]:
        """Get all direct children of a node."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[child_id] for child_id in node.children if child_id in self.nodes]

    def get_descendants(self, node_id: str) -> List[PBSNode]:
        """Get all descendants of a node (recursive)."""
        descendants: List[PBSNode] = []
        children = self.get_children(node_id)
        for child in children:
            descendants.append(child)
            descendants.extend(self.get_descendants(child.id))
        return descendants

    def get_ancestors(self, node_id: str) -> List[PBSNode]:
        """Get all ancestors of a node from immediate parent to root."""
        ancestors: List[PBSNode] = []
        node = self.nodes.get(node_id)
        while node and node.parent_id:
            parent = self.nodes.get(node.parent_id)
            if parent:
                ancestors.append(parent)
                node = parent
            else:
                break
        return ancestors

    def get_leaves(self) -> List[PBSNode]:
        """Get all leaf nodes (no children)."""
        return [node for node in self.nodes.values() if node.is_leaf()]

    def get_by_level(self, level: int) -> List[PBSNode]:
        """Get all nodes at a specific level."""
        return [node for node in self.nodes.values() if node.level == level]

    def get_mission_critical(self) -> List[PBSNode]:
        """Get all mission-critical nodes."""
        return [node for node in self.nodes.values() if node.is_mission_critical]

    def traverse_preorder(
        self,
        node_id: Optional[str] = None,
        visit: Optional[Callable[[PBSNode], None]] = None
    ) -> Iterator[PBSNode]:
        """Traverse tree in pre-order (parent before children)."""
        start_id = node_id or self.root_id
        if not start_id or start_id not in self.nodes:
            return

        node = self.nodes[start_id]
        if visit:
            visit(node)
        yield node

        for child_id in node.children:
            yield from self.traverse_preorder(child_id, visit)

    def traverse_postorder(
        self,
        node_id: Optional[str] = None,
        visit: Optional[Callable[[PBSNode], None]] = None
    ) -> Iterator[PBSNode]:
        """Traverse tree in post-order (children before parent)."""
        start_id = node_id or self.root_id
        if not start_id or start_id not in self.nodes:
            return

        node = self.nodes[start_id]

        for child_id in node.children:
            yield from self.traverse_postorder(child_id, visit)

        if visit:
            visit(node)
        yield node

    def validate_completeness(self, requirements_ids: List[str]) -> Dict[str, Any]:
        """Check if all requirements are allocated.

        Args:
            requirements_ids: List of requirement IDs to check.

        Returns:
            Dictionary with validation results.
        """
        allocated_reqs: set = set()
        for node in self.nodes.values():
            allocated_reqs.update(node.allocated_requirements)

        unallocated = set(requirements_ids) - allocated_reqs
        orphaned = allocated_reqs - set(requirements_ids)

        return {
            "is_complete": len(unallocated) == 0,
            "unallocated_requirements": list(unallocated),
            "orphaned_allocations": list(orphaned),
            "total_nodes": len(self.nodes),
            "total_leaves": len(self.get_leaves()),
        }

    def calculate_total_mass(self) -> float:
        """Calculate total mass from leaf nodes."""
        return sum(
            node.mass_kg or 0
            for node in self.get_leaves()
        )

    def calculate_total_power(self) -> float:
        """Calculate total power from leaf nodes."""
        return sum(
            node.power_w or 0
            for node in self.get_leaves()
        )

    def to_tree_string(self, node_id: Optional[str] = None, indent: int = 0) -> str:
        """Generate ASCII tree representation."""
        start_id = node_id or self.root_id
        if not start_id:
            return ""

        node = self.nodes.get(start_id)
        if not node:
            return ""

        prefix = "  " * indent + ("├── " if indent > 0 else "")
        result = f"{prefix}{node.id}: {node.name}\n"

        for child_id in node.children:
            result += self.to_tree_string(child_id, indent + 1)

        return result

    def export_to_dict(self) -> Dict[str, Any]:
        """Export PBS to dictionary format."""
        return {
            "mission_name": self.mission_name,
            "version": self.version,
            "root_id": self.root_id,
            "nodes": {
                node_id: node.model_dump()
                for node_id, node in self.nodes.items()
            },
        }

    def export_to_json(self, indent: int = 2) -> str:
        """Export PBS to JSON string."""
        return json.dumps(self.export_to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductBreakdownStructure":
        """Create PBS from dictionary."""
        nodes = {
            node_id: PBSNode(**node_data)
            for node_id, node_data in data.get("nodes", {}).items()
        }
        return cls(
            mission_name=data["mission_name"],
            version=data.get("version", "1.0"),
            root_id=data.get("root_id"),
            nodes=nodes,
        )

    def __len__(self) -> int:
        """Return the number of nodes."""
        return len(self.nodes)

    def __contains__(self, node_id: str) -> bool:
        """Check if a node ID exists."""
        return node_id in self.nodes

"""CRUD operations for SE artifacts.

This module provides create, read, update, delete operations
for all artifact types with a unified interface.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel

from artifacts.requirements import RequirementItem, RequirementsSet
from artifacts.pbs import PBSNode, ProductBreakdownStructure
from artifacts.wbs import WorkPackage, WorkBreakdownStructure
from artifacts.dependencies import Dependency, DependencyGraph
from artifacts.timeline import ScheduledTask, ExecutionTimeline


logger = logging.getLogger("astraeus.tools.crud")


# Type mapping for artifact types
ARTIFACT_TYPES: Dict[str, Type[BaseModel]] = {
    "requirements_set": RequirementsSet,
    "requirement": RequirementItem,
    "pbs": ProductBreakdownStructure,
    "pbs_node": PBSNode,
    "wbs": WorkBreakdownStructure,
    "work_package": WorkPackage,
    "dependency_graph": DependencyGraph,
    "dependency": Dependency,
    "timeline": ExecutionTimeline,
    "scheduled_task": ScheduledTask,
}


class ArtifactStore:
    """In-memory artifact storage with persistence support.

    Provides a simple key-value store for artifacts with
    optional file-based persistence.

    Attributes:
        storage_path: Optional path for file persistence.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the artifact store.

        Args:
            storage_path: Optional path to persist artifacts.
        """
        self.storage_path = storage_path
        self._store: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

        if storage_path and storage_path.exists():
            self._load_from_disk()

    def _generate_id(self, artifact_type: str) -> str:
        """Generate a unique artifact ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"{artifact_type}-{timestamp}"

    def create(
        self,
        artifact_type: str,
        data: Union[Dict[str, Any], BaseModel],
        artifact_id: Optional[str] = None,
    ) -> str:
        """Create a new artifact.

        Args:
            artifact_type: Type of artifact to create.
            data: Artifact data (dict or Pydantic model).
            artifact_id: Optional custom ID.

        Returns:
            The artifact ID.

        Raises:
            ValueError: If artifact type is unknown or ID exists.
        """
        if artifact_type not in ARTIFACT_TYPES:
            raise ValueError(f"Unknown artifact type: {artifact_type}")

        if artifact_id is None:
            artifact_id = self._generate_id(artifact_type)

        if artifact_id in self._store:
            raise ValueError(f"Artifact {artifact_id} already exists")

        # Convert Pydantic model to dict if necessary
        if isinstance(data, BaseModel):
            data = data.model_dump()

        # Validate data against model
        model_class = ARTIFACT_TYPES[artifact_type]
        try:
            validated = model_class(**data)
            data = validated.model_dump()
        except Exception as e:
            raise ValueError(f"Invalid data for {artifact_type}: {e}")

        self._store[artifact_id] = data
        self._metadata[artifact_id] = {
            "type": artifact_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": 1,
        }

        logger.info(f"Created artifact: {artifact_id}")
        self._persist()

        return artifact_id

    def read(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Read an artifact by ID.

        Args:
            artifact_id: The artifact ID.

        Returns:
            Artifact data as dictionary, or None if not found.
        """
        return self._store.get(artifact_id)

    def read_as_model(self, artifact_id: str) -> Optional[BaseModel]:
        """Read an artifact and return as Pydantic model.

        Args:
            artifact_id: The artifact ID.

        Returns:
            Artifact as Pydantic model, or None if not found.
        """
        data = self.read(artifact_id)
        if data is None:
            return None

        metadata = self._metadata.get(artifact_id, {})
        artifact_type = metadata.get("type")

        if artifact_type and artifact_type in ARTIFACT_TYPES:
            model_class = ARTIFACT_TYPES[artifact_type]
            return model_class(**data)

        return None

    def update(
        self,
        artifact_id: str,
        updates: Dict[str, Any],
        merge: bool = True,
    ) -> bool:
        """Update an existing artifact.

        Args:
            artifact_id: The artifact ID.
            updates: Dictionary of updates to apply.
            merge: If True, merge with existing data; if False, replace.

        Returns:
            True if updated, False if artifact not found.
        """
        if artifact_id not in self._store:
            logger.warning(f"Artifact not found: {artifact_id}")
            return False

        if merge:
            current = self._store[artifact_id]
            self._deep_merge(current, updates)
        else:
            self._store[artifact_id] = updates

        # Update metadata
        self._metadata[artifact_id]["updated_at"] = datetime.now().isoformat()
        self._metadata[artifact_id]["version"] = (
            self._metadata[artifact_id].get("version", 0) + 1
        )

        logger.info(f"Updated artifact: {artifact_id}")
        self._persist()

        return True

    def delete(self, artifact_id: str) -> bool:
        """Delete an artifact.

        Args:
            artifact_id: The artifact ID.

        Returns:
            True if deleted, False if not found.
        """
        if artifact_id not in self._store:
            return False

        del self._store[artifact_id]
        del self._metadata[artifact_id]

        logger.info(f"Deleted artifact: {artifact_id}")
        self._persist()

        return True

    def list_artifacts(
        self,
        artifact_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all artifacts, optionally filtered by type.

        Args:
            artifact_type: Optional type to filter by.

        Returns:
            List of artifact summaries with ID and metadata.
        """
        results = []

        for artifact_id, metadata in self._metadata.items():
            if artifact_type and metadata.get("type") != artifact_type:
                continue

            results.append({
                "id": artifact_id,
                **metadata,
            })

        return results

    def get_metadata(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for an artifact.

        Args:
            artifact_id: The artifact ID.

        Returns:
            Metadata dictionary or None if not found.
        """
        return self._metadata.get(artifact_id)

    def _deep_merge(self, base: Dict, updates: Dict) -> None:
        """Deep merge updates into base dictionary."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _persist(self) -> None:
        """Persist store to disk if storage path is configured."""
        if not self.storage_path:
            return

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Save store
        store_file = self.storage_path / "artifacts.json"
        with open(store_file, "w") as f:
            json.dump({
                "store": self._store,
                "metadata": self._metadata,
            }, f, indent=2, default=str)

    def _load_from_disk(self) -> None:
        """Load store from disk."""
        if not self.storage_path:
            return

        store_file = self.storage_path / "artifacts.json"
        if store_file.exists():
            with open(store_file, "r") as f:
                data = json.load(f)
                self._store = data.get("store", {})
                self._metadata = data.get("metadata", {})

            logger.info(f"Loaded {len(self._store)} artifacts from disk")


# Global store instance
_global_store: Optional[ArtifactStore] = None


def get_store() -> ArtifactStore:
    """Get or create the global artifact store."""
    global _global_store
    if _global_store is None:
        _global_store = ArtifactStore()
    return _global_store


def set_store(store: ArtifactStore) -> None:
    """Set the global artifact store."""
    global _global_store
    _global_store = store


# Convenience functions using global store
def create_artifact(
    artifact_type: str,
    data: Union[Dict[str, Any], BaseModel],
    artifact_id: Optional[str] = None,
) -> str:
    """Create a new artifact in the global store."""
    return get_store().create(artifact_type, data, artifact_id)


def read_artifact(artifact_id: str) -> Optional[Dict[str, Any]]:
    """Read an artifact from the global store."""
    return get_store().read(artifact_id)


def update_artifact(
    artifact_id: str,
    updates: Dict[str, Any],
    merge: bool = True,
) -> bool:
    """Update an artifact in the global store."""
    return get_store().update(artifact_id, updates, merge)


def delete_artifact(artifact_id: str) -> bool:
    """Delete an artifact from the global store."""
    return get_store().delete(artifact_id)


def list_artifacts(artifact_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """List artifacts in the global store."""
    return get_store().list_artifacts(artifact_type)

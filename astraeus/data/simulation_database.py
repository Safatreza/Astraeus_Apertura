"""Database for storing and querying simulation results."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import hashlib

from loguru import logger


class SimulationDatabase:
    """
    SQLite database for storing simulation configurations and results.

    Features:
    - Store design parameters and simulation results
    - Cache duplicate simulations
    - Query historical results
    - Track simulation metadata (runtime, convergence, etc.)
    """

    def __init__(self, db_path: str = "simulations.db"):
        """
        Initialize simulation database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

        # Create database
        self._create_database()

        logger.info(f"Simulation database initialized: {self.db_path}")

    def _create_database(self) -> None:
        """Create database schema if it doesn't exist."""
        self.conn = sqlite3.connect(str(self.db_path))
        cursor = self.conn.cursor()

        # Designs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS designs (
                design_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                mission_name TEXT,
                requirements_json TEXT,
                design_params_json TEXT,
                parameter_hash TEXT UNIQUE,
                tags TEXT,
                created_by TEXT
            )
        """)

        # Simulations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulations (
                simulation_id TEXT PRIMARY KEY,
                design_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                frequency_ghz REAL,
                configuration_json TEXT,
                status TEXT,
                runtime_seconds REAL,
                convergence_data_json TEXT,
                FOREIGN KEY (design_id) REFERENCES designs(design_id)
            )
        """)

        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                result_id TEXT PRIMARY KEY,
                simulation_id TEXT NOT NULL,
                gain_dbi REAL,
                directivity_dbi REAL,
                efficiency_percent REAL,
                vswr REAL,
                beamwidth_az_deg REAL,
                beamwidth_el_deg REAL,
                sidelobe_level_db REAL,
                cross_pol_db REAL,
                performance_metrics_json TEXT,
                s_parameters_json TEXT,
                radiation_pattern_file TEXT,
                FOREIGN KEY (simulation_id) REFERENCES simulations(simulation_id)
            )
        """)

        # Agent decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_decisions (
                decision_id TEXT PRIMARY KEY,
                design_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                decision_type TEXT,
                proposal_json TEXT,
                rationale TEXT,
                accepted INTEGER,
                FOREIGN KEY (design_id) REFERENCES designs(design_id)
            )
        """)

        # Create indices for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_designs_hash
            ON designs(parameter_hash)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_simulations_design
            ON simulations(design_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_results_simulation
            ON results(simulation_id)
        """)

        self.conn.commit()
        logger.info("Database schema created/verified")

    def _compute_parameter_hash(self, design_params: Dict[str, Any]) -> str:
        """
        Compute hash of design parameters for duplicate detection.

        Args:
            design_params: Design parameter dictionary

        Returns:
            SHA256 hash string
        """
        # Sort keys for consistent hashing
        param_str = json.dumps(design_params, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()

    def add_design(
        self,
        requirements: Dict[str, Any],
        design_params: Dict[str, Any],
        mission_name: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Add a new design to the database.

        Args:
            requirements: Mission requirements
            design_params: Design parameters
            mission_name: Mission name
            tags: List of tags for categorization

        Returns:
            design_id
        """
        design_id = str(uuid4())
        param_hash = self._compute_parameter_hash(design_params)
        timestamp = datetime.now().isoformat()

        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO designs (
                    design_id, timestamp, mission_name,
                    requirements_json, design_params_json,
                    parameter_hash, tags, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                design_id,
                timestamp,
                mission_name,
                json.dumps(requirements),
                json.dumps(design_params),
                param_hash,
                json.dumps(tags or []),
                "astraeus_system"
            ))

            self.conn.commit()
            logger.info(f"Design added: {design_id}")
            return design_id

        except sqlite3.IntegrityError:
            # Design with same parameters already exists
            logger.warning("Design with identical parameters already exists")
            cursor.execute(
                "SELECT design_id FROM designs WHERE parameter_hash = ?",
                (param_hash,)
            )
            existing_id = cursor.fetchone()[0]
            return existing_id

    def add_simulation(
        self,
        design_id: str,
        tool_name: str,
        frequency_ghz: float,
        configuration: Dict[str, Any],
        status: str = "pending"
    ) -> str:
        """
        Add a simulation record.

        Args:
            design_id: Associated design ID
            tool_name: Simulation tool name
            frequency_ghz: Solution frequency
            configuration: Simulation configuration
            status: Simulation status

        Returns:
            simulation_id
        """
        simulation_id = str(uuid4())
        timestamp = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO simulations (
                simulation_id, design_id, tool_name, timestamp,
                frequency_ghz, configuration_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            simulation_id,
            design_id,
            tool_name,
            timestamp,
            frequency_ghz,
            json.dumps(configuration),
            status
        ))

        self.conn.commit()
        logger.info(f"Simulation added: {simulation_id}")
        return simulation_id

    def update_simulation_status(
        self,
        simulation_id: str,
        status: str,
        runtime_seconds: Optional[float] = None,
        convergence_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update simulation status and metadata."""
        cursor = self.conn.cursor()

        update_fields = ["status = ?"]
        values = [status]

        if runtime_seconds is not None:
            update_fields.append("runtime_seconds = ?")
            values.append(runtime_seconds)

        if convergence_data is not None:
            update_fields.append("convergence_data_json = ?")
            values.append(json.dumps(convergence_data))

        values.append(simulation_id)

        cursor.execute(f"""
            UPDATE simulations
            SET {', '.join(update_fields)}
            WHERE simulation_id = ?
        """, values)

        self.conn.commit()

    def add_results(
        self,
        simulation_id: str,
        performance_metrics: Dict[str, Any],
        s_parameters: Optional[Dict[str, Any]] = None,
        radiation_pattern_file: Optional[str] = None
    ) -> str:
        """
        Add simulation results.

        Args:
            simulation_id: Associated simulation ID
            performance_metrics: Performance metrics dictionary
            s_parameters: S-parameter data
            radiation_pattern_file: Path to radiation pattern data file

        Returns:
            result_id
        """
        result_id = str(uuid4())

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO results (
                result_id, simulation_id,
                gain_dbi, directivity_dbi, efficiency_percent,
                vswr, beamwidth_az_deg, beamwidth_el_deg,
                sidelobe_level_db, cross_pol_db,
                performance_metrics_json, s_parameters_json,
                radiation_pattern_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result_id,
            simulation_id,
            performance_metrics.get("gain_dbi"),
            performance_metrics.get("directivity_dbi"),
            performance_metrics.get("efficiency_percent"),
            performance_metrics.get("vswr"),
            performance_metrics.get("beamwidth_az_deg"),
            performance_metrics.get("beamwidth_el_deg"),
            performance_metrics.get("sidelobe_level_db"),
            performance_metrics.get("cross_pol_db"),
            json.dumps(performance_metrics),
            json.dumps(s_parameters) if s_parameters else None,
            radiation_pattern_file
        ))

        self.conn.commit()
        logger.info(f"Results added: {result_id}")
        return result_id

    def find_cached_simulation(
        self,
        design_params: Dict[str, Any],
        tool_name: str,
        frequency_ghz: float
    ) -> Optional[Dict[str, Any]]:
        """
        Find cached simulation results for identical design.

        Args:
            design_params: Design parameters
            tool_name: Simulation tool name
            frequency_ghz: Solution frequency

        Returns:
            Cached results if found, None otherwise
        """
        param_hash = self._compute_parameter_hash(design_params)

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.simulation_id, r.performance_metrics_json
            FROM designs d
            JOIN simulations s ON d.design_id = s.design_id
            JOIN results r ON s.simulation_id = r.simulation_id
            WHERE d.parameter_hash = ?
            AND s.tool_name = ?
            AND s.frequency_ghz = ?
            AND s.status = 'completed'
            ORDER BY s.timestamp DESC
            LIMIT 1
        """, (param_hash, tool_name, frequency_ghz))

        result = cursor.fetchone()

        if result:
            logger.info(f"Found cached simulation: {result[0]}")
            return {
                "simulation_id": result[0],
                "performance_metrics": json.loads(result[1])
            }

        return None

    def query_designs(
        self,
        tags: Optional[List[str]] = None,
        gain_min: Optional[float] = None,
        gain_max: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query designs with filters.

        Args:
            tags: Filter by tags
            gain_min: Minimum gain filter
            gain_max: Maximum gain filter
            limit: Maximum results to return

        Returns:
            List of design dictionaries
        """
        query = """
            SELECT DISTINCT d.design_id, d.mission_name, d.timestamp,
                   d.design_params_json, r.gain_dbi
            FROM designs d
            LEFT JOIN simulations s ON d.design_id = s.design_id
            LEFT JOIN results r ON s.simulation_id = r.simulation_id
            WHERE 1=1
        """
        params = []

        if gain_min is not None:
            query += " AND r.gain_dbi >= ?"
            params.append(gain_min)

        if gain_max is not None:
            query += " AND r.gain_dbi <= ?"
            params.append(gain_max)

        query += " ORDER BY d.timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            results.append({
                "design_id": row[0],
                "mission_name": row[1],
                "timestamp": row[2],
                "design_params": json.loads(row[3]) if row[3] else {},
                "gain_dbi": row[4]
            })

        return results

    def get_design_history(self, design_id: str) -> Dict[str, Any]:
        """
        Get complete history for a design.

        Args:
            design_id: Design ID

        Returns:
            Dictionary with design info and all simulations
        """
        cursor = self.conn.cursor()

        # Get design info
        cursor.execute("""
            SELECT mission_name, timestamp, requirements_json, design_params_json
            FROM designs WHERE design_id = ?
        """, (design_id,))

        design_row = cursor.fetchone()
        if not design_row:
            return {}

        # Get all simulations
        cursor.execute("""
            SELECT s.simulation_id, s.tool_name, s.timestamp, s.status,
                   s.runtime_seconds, r.performance_metrics_json
            FROM simulations s
            LEFT JOIN results r ON s.simulation_id = r.simulation_id
            WHERE s.design_id = ?
            ORDER BY s.timestamp
        """, (design_id,))

        simulations = []
        for sim_row in cursor.fetchall():
            simulations.append({
                "simulation_id": sim_row[0],
                "tool_name": sim_row[1],
                "timestamp": sim_row[2],
                "status": sim_row[3],
                "runtime_seconds": sim_row[4],
                "performance_metrics": json.loads(sim_row[5]) if sim_row[5] else {}
            })

        return {
            "design_id": design_id,
            "mission_name": design_row[0],
            "timestamp": design_row[1],
            "requirements": json.loads(design_row[2]),
            "design_params": json.loads(design_row[3]),
            "simulations": simulations
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()

        stats = {}

        # Total designs
        cursor.execute("SELECT COUNT(*) FROM designs")
        stats["total_designs"] = cursor.fetchone()[0]

        # Total simulations
        cursor.execute("SELECT COUNT(*) FROM simulations")
        stats["total_simulations"] = cursor.fetchone()[0]

        # Completed simulations
        cursor.execute("SELECT COUNT(*) FROM simulations WHERE status = 'completed'")
        stats["completed_simulations"] = cursor.fetchone()[0]

        # Tools used
        cursor.execute("SELECT tool_name, COUNT(*) FROM simulations GROUP BY tool_name")
        stats["simulations_by_tool"] = dict(cursor.fetchall())

        return stats

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def __del__(self):
        """Destructor to ensure connection is closed."""
        self.close()

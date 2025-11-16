"""Particle Swarm Optimization implementation."""

import numpy as np
from typing import Callable, Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class PSOConfig:
    """Configuration for Particle Swarm Optimization."""

    num_particles: int = 30
    max_iterations: int = 100
    inertia_weight: float = 0.7
    cognitive_coeff: float = 1.5  # c1
    social_coeff: float = 1.5  # c2
    velocity_clamp: float = 0.5  # Fraction of search space
    convergence_threshold: float = 1e-6
    stall_iterations: int = 20


class Particle:
    """Represents a particle in the swarm."""

    def __init__(self, position: np.ndarray, velocity: np.ndarray):
        """
        Initialize particle.

        Args:
            position: Current position
            velocity: Current velocity
        """
        self.position = position
        self.velocity = velocity
        self.best_position = position.copy()
        self.best_fitness = float('inf')
        self.fitness = float('inf')


class ParticleSwarmOptimizer:
    """
    Particle Swarm Optimization for antenna design.

    Implements PSO with:
    - Inertia weight for exploration/exploitation balance
    - Velocity clamping
    - Global best tracking
    """

    def __init__(self, config: Optional[PSOConfig] = None):
        """
        Initialize PSO optimizer.

        Args:
            config: PSO configuration
        """
        self.config = config or PSOConfig()
        self.swarm: List[Particle] = []
        self.global_best_position: Optional[np.ndarray] = None
        self.global_best_fitness = float('inf')
        self.history: List[Dict[str, Any]] = []

    def optimize(
        self,
        objective_func: Callable,
        bounds: List[Tuple[float, float]],
        constraint_func: Optional[Callable] = None
    ) -> Tuple[np.ndarray, float]:
        """
        Run PSO optimization.

        Args:
            objective_func: Function to minimize f(x) -> float
            bounds: List of (min, max) tuples for each variable
            constraint_func: Optional constraint function

        Returns:
            Tuple of (best_solution, best_fitness)
        """
        n_vars = len(bounds)
        bounds_array = np.array(bounds)
        search_range = bounds_array[:, 1] - bounds_array[:, 0]

        logger.info(f"Starting PSO optimization: {n_vars} variables, "
                   f"{self.config.num_particles} particles, "
                   f"{self.config.max_iterations} iterations")

        # Initialize swarm
        self._initialize_swarm(bounds_array, search_range)

        # Evaluate initial swarm
        self._evaluate_swarm(objective_func, constraint_func)

        # Optimization loop
        stall_count = 0
        prev_best_fitness = float('inf')

        for iteration in range(self.config.max_iterations):
            # Update velocities and positions
            self._update_swarm(bounds_array, search_range)

            # Evaluate swarm
            self._evaluate_swarm(objective_func, constraint_func)

            # Update personal and global bests
            self._update_bests()

            # Log progress
            avg_fitness = np.mean([p.fitness for p in self.swarm])
            self.history.append({
                'iteration': iteration,
                'best_fitness': self.global_best_fitness,
                'avg_fitness': avg_fitness,
                'best_solution': self.global_best_position.copy()
            })

            if iteration % 10 == 0:
                logger.info(f"Iter {iteration}: Best={self.global_best_fitness:.6f}, "
                           f"Avg={avg_fitness:.6f}")

            # Check convergence
            improvement = abs(prev_best_fitness - self.global_best_fitness)
            if improvement < self.config.convergence_threshold:
                stall_count += 1
            else:
                stall_count = 0

            if stall_count >= self.config.stall_iterations:
                logger.info(f"Converged at iteration {iteration}")
                break

            prev_best_fitness = self.global_best_fitness

        logger.info(f"PSO optimization complete. Best fitness: {self.global_best_fitness:.6f}")

        return self.global_best_position, self.global_best_fitness

    def _initialize_swarm(
        self,
        bounds: np.ndarray,
        search_range: np.ndarray
    ) -> None:
        """Initialize particle swarm."""
        n_vars = bounds.shape[0]

        for _ in range(self.config.num_particles):
            # Random position within bounds
            position = np.random.uniform(bounds[:, 0], bounds[:, 1])

            # Random velocity
            v_max = self.config.velocity_clamp * search_range
            velocity = np.random.uniform(-v_max, v_max)

            particle = Particle(position, velocity)
            self.swarm.append(particle)

    def _evaluate_swarm(
        self,
        objective_func: Callable,
        constraint_func: Optional[Callable] = None
    ) -> None:
        """Evaluate all particles."""
        for particle in self.swarm:
            # Evaluate objective
            fitness = objective_func(particle.position)

            # Handle constraints with penalty method
            if constraint_func:
                violation = constraint_func(particle.position)
                if violation > 0:
                    fitness += 1e6 * violation

            particle.fitness = fitness

    def _update_swarm(
        self,
        bounds: np.ndarray,
        search_range: np.ndarray
    ) -> None:
        """Update particle velocities and positions."""
        w = self.config.inertia_weight
        c1 = self.config.cognitive_coeff
        c2 = self.config.social_coeff
        v_max = self.config.velocity_clamp * search_range

        for particle in self.swarm:
            # Random factors
            r1 = np.random.random(len(particle.position))
            r2 = np.random.random(len(particle.position))

            # Velocity update
            cognitive = c1 * r1 * (particle.best_position - particle.position)
            social = c2 * r2 * (self.global_best_position - particle.position)

            particle.velocity = w * particle.velocity + cognitive + social

            # Velocity clamping
            particle.velocity = np.clip(particle.velocity, -v_max, v_max)

            # Position update
            particle.position += particle.velocity

            # Boundary handling (reflection)
            for i in range(len(particle.position)):
                if particle.position[i] < bounds[i, 0]:
                    particle.position[i] = bounds[i, 0]
                    particle.velocity[i] *= -0.5
                elif particle.position[i] > bounds[i, 1]:
                    particle.position[i] = bounds[i, 1]
                    particle.velocity[i] *= -0.5

    def _update_bests(self) -> None:
        """Update personal and global bests."""
        for particle in self.swarm:
            # Update personal best
            if particle.fitness < particle.best_fitness:
                particle.best_fitness = particle.fitness
                particle.best_position = particle.position.copy()

            # Update global best
            if particle.fitness < self.global_best_fitness:
                self.global_best_fitness = particle.fitness
                self.global_best_position = particle.position.copy()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get optimization history."""
        return self.history

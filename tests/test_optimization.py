"""Tests for optimization algorithms."""

import pytest
import numpy as np
from astraeus.optimization.genetic_algorithm import GeneticAlgorithm, GeneticAlgorithmConfig
from astraeus.optimization.particle_swarm import ParticleSwarmOptimizer, PSOConfig
from astraeus.optimization.sensitivity import SensitivityAnalyzer


class TestGeneticAlgorithm:
    """Test Genetic Algorithm optimizer."""

    def test_initialization(self):
        """Test GA initialization."""
        ga = GeneticAlgorithm()
        assert ga.config.population_size == 50
        assert len(ga.population) == 0

    def test_simple_optimization(self):
        """Test GA on simple sphere function."""
        # Minimize sphere function: f(x) = sum(x^2)
        def sphere(x):
            return np.sum(x ** 2)

        bounds = [(-5, 5), (-5, 5)]

        config = GeneticAlgorithmConfig(
            population_size=20,
            num_generations=50,
            convergence_threshold=1e-3
        )

        ga = GeneticAlgorithm(config)
        best_x, best_f = ga.optimize(sphere, bounds)

        # Should find solution near origin
        assert best_f < 0.1  # Close to zero
        assert np.all(np.abs(best_x) < 1.0)  # Near origin

    def test_constrained_optimization(self):
        """Test GA with constraints."""
        def objective(x):
            return x[0] ** 2 + x[1] ** 2

        def constraint(x):
            # Constraint: x[0] + x[1] >= 1
            violation = max(0, 1 - (x[0] + x[1]))
            return violation

        bounds = [(0, 5), (0, 5)]

        config = GeneticAlgorithmConfig(
            population_size=20,
            num_generations=30
        )

        ga = GeneticAlgorithm(config)
        best_x, best_f = ga.optimize(objective, bounds, constraint_func=constraint)

        # Should satisfy constraint
        assert best_x[0] + best_x[1] >= 0.9  # Close to constraint boundary


class TestParticleSwarm:
    """Test Particle Swarm Optimizer."""

    def test_initialization(self):
        """Test PSO initialization."""
        pso = ParticleSwarmOptimizer()
        assert pso.config.num_particles == 30
        assert len(pso.swarm) == 0

    def test_simple_optimization(self):
        """Test PSO on Rosenbrock function."""
        def rosenbrock(x):
            return (1 - x[0]) ** 2 + 100 * (x[1] - x[0] ** 2) ** 2

        bounds = [(-2, 2), (-2, 2)]

        config = PSOConfig(
            num_particles=20,
            max_iterations=50
        )

        pso = ParticleSwarmOptimizer(config)
        best_x, best_f = pso.optimize(rosenbrock, bounds)

        # Should find minimum near (1, 1)
        assert best_f < 0.5  # Reasonably close to minimum
        assert abs(best_x[0] - 1.0) < 0.5
        assert abs(best_x[1] - 1.0) < 0.5


class TestSensitivityAnalyzer:
    """Test sensitivity analysis."""

    def test_local_sensitivity(self):
        """Test local sensitivity analysis."""
        def quadratic(x):
            return x[0] ** 2 + 2 * x[1] ** 2 + 3 * x[2] ** 2

        nominal = np.array([1.0, 1.0, 1.0])
        param_names = ["x0", "x1", "x2"]

        analyzer = SensitivityAnalyzer()
        sensitivities = analyzer.local_sensitivity(
            quadratic,
            nominal,
            param_names
        )

        # x2 should be most sensitive (coefficient 3)
        assert sensitivities["x2"]["absolute"] > sensitivities["x1"]["absolute"]
        assert sensitivities["x1"]["absolute"] > sensitivities["x0"]["absolute"]

    def test_morris_screening(self):
        """Test Morris screening method."""
        def additive(x):
            return x[0] + 2 * x[1] + 0.1 * x[2]

        bounds = [(0, 1), (0, 1), (0, 1)]
        param_names = ["x0", "x1", "x2"]

        analyzer = SensitivityAnalyzer()
        sensitivities = analyzer.morris_screening(
            additive,
            bounds,
            param_names,
            num_trajectories=10
        )

        # x1 should be most important (coefficient 2)
        assert sensitivities["x1"]["mu_star"] > sensitivities["x0"]["mu_star"]
        assert sensitivities["x0"]["mu_star"] > sensitivities["x2"]["mu_star"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

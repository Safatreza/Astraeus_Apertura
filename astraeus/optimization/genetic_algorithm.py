"""Genetic Algorithm implementation for antenna optimization."""

import numpy as np
from typing import Callable, Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class GeneticAlgorithmConfig:
    """Configuration for Genetic Algorithm."""

    population_size: int = 50
    num_generations: int = 100
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    elitism_ratio: float = 0.1
    tournament_size: int = 3
    convergence_threshold: float = 1e-6
    stall_generations: int = 20


class Individual:
    """Represents an individual in the population."""

    def __init__(self, genes: np.ndarray):
        """
        Initialize individual.

        Args:
            genes: Parameter values (genotype)
        """
        self.genes = genes
        self.fitness: Optional[float] = None
        self.constraint_violation: float = 0.0

    def evaluate(
        self,
        objective_func: Callable,
        constraint_func: Optional[Callable] = None
    ) -> float:
        """
        Evaluate fitness.

        Args:
            objective_func: Objective function to minimize
            constraint_func: Optional constraint function

        Returns:
            Fitness value
        """
        # Evaluate objective
        self.fitness = objective_func(self.genes)

        # Evaluate constraints
        if constraint_func:
            self.constraint_violation = constraint_func(self.genes)

        # Penalty method for constraint handling
        if self.constraint_violation > 0:
            self.fitness += 1e6 * self.constraint_violation

        return self.fitness

    def copy(self) -> 'Individual':
        """Create a copy of this individual."""
        new_ind = Individual(self.genes.copy())
        new_ind.fitness = self.fitness
        new_ind.constraint_violation = self.constraint_violation
        return new_ind


class GeneticAlgorithm:
    """
    Genetic Algorithm optimizer for antenna design.

    Implements a real-coded GA with:
    - Tournament selection
    - Simulated binary crossover (SBX)
    - Polynomial mutation
    - Elitism
    """

    def __init__(self, config: Optional[GeneticAlgorithmConfig] = None):
        """
        Initialize GA optimizer.

        Args:
            config: GA configuration
        """
        self.config = config or GeneticAlgorithmConfig()
        self.population: List[Individual] = []
        self.best_individual: Optional[Individual] = None
        self.history: List[Dict[str, Any]] = []

    def optimize(
        self,
        objective_func: Callable,
        bounds: List[Tuple[float, float]],
        constraint_func: Optional[Callable] = None,
        initial_population: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, float]:
        """
        Run genetic algorithm optimization.

        Args:
            objective_func: Function to minimize f(x) -> float
            bounds: List of (min, max) tuples for each variable
            constraint_func: Optional constraint function g(x) -> violation (0 if satisfied)
            initial_population: Optional initial population (pop_size x n_vars)

        Returns:
            Tuple of (best_solution, best_fitness)
        """
        n_vars = len(bounds)
        bounds_array = np.array(bounds)

        logger.info(f"Starting GA optimization: {n_vars} variables, "
                   f"{self.config.population_size} population, "
                   f"{self.config.num_generations} generations")

        # Initialize population
        self._initialize_population(bounds_array, initial_population)

        # Evaluate initial population
        for ind in self.population:
            ind.evaluate(objective_func, constraint_func)

        self._update_best()

        # Evolution loop
        stall_count = 0
        prev_best_fitness = float('inf')

        for gen in range(self.config.num_generations):
            # Selection
            parents = self._selection()

            # Crossover and mutation
            offspring = self._variation(parents, bounds_array)

            # Evaluation
            for ind in offspring:
                ind.evaluate(objective_func, constraint_func)

            # Survival selection (elitism + offspring)
            self._survival_selection(offspring)

            # Update best
            prev_best = self.best_individual.fitness if self.best_individual else float('inf')
            self._update_best()

            # Log progress
            avg_fitness = np.mean([ind.fitness for ind in self.population])
            self.history.append({
                'generation': gen,
                'best_fitness': self.best_individual.fitness,
                'avg_fitness': avg_fitness,
                'best_solution': self.best_individual.genes.copy()
            })

            if gen % 10 == 0:
                logger.info(f"Gen {gen}: Best={self.best_individual.fitness:.6f}, "
                           f"Avg={avg_fitness:.6f}")

            # Check convergence
            improvement = abs(prev_best - self.best_individual.fitness)
            if improvement < self.config.convergence_threshold:
                stall_count += 1
            else:
                stall_count = 0

            if stall_count >= self.config.stall_generations:
                logger.info(f"Converged at generation {gen}")
                break

        logger.info(f"GA optimization complete. Best fitness: {self.best_individual.fitness:.6f}")

        return self.best_individual.genes, self.best_individual.fitness

    def _initialize_population(
        self,
        bounds: np.ndarray,
        initial_pop: Optional[np.ndarray] = None
    ) -> None:
        """Initialize population."""
        n_vars = bounds.shape[0]

        if initial_pop is not None:
            # Use provided initial population
            for genes in initial_pop:
                self.population.append(Individual(genes))
        else:
            # Random initialization
            for _ in range(self.config.population_size):
                genes = np.random.uniform(bounds[:, 0], bounds[:, 1])
                self.population.append(Individual(genes))

    def _selection(self) -> List[Individual]:
        """Tournament selection."""
        parents = []
        pop_size = len(self.population)

        for _ in range(pop_size):
            # Select tournament competitors
            competitors_idx = np.random.choice(pop_size, self.config.tournament_size, replace=False)
            competitors = [self.population[i] for i in competitors_idx]

            # Select best from tournament
            winner = min(competitors, key=lambda ind: ind.fitness)
            parents.append(winner.copy())

        return parents

    def _variation(
        self,
        parents: List[Individual],
        bounds: np.ndarray
    ) -> List[Individual]:
        """Apply crossover and mutation."""
        offspring = []
        n_parents = len(parents)

        for i in range(0, n_parents - 1, 2):
            parent1 = parents[i]
            parent2 = parents[i + 1]

            # Crossover
            if np.random.random() < self.config.crossover_rate:
                child1_genes, child2_genes = self._sbx_crossover(
                    parent1.genes, parent2.genes, bounds
                )
            else:
                child1_genes = parent1.genes.copy()
                child2_genes = parent2.genes.copy()

            # Mutation
            child1_genes = self._polynomial_mutation(child1_genes, bounds)
            child2_genes = self._polynomial_mutation(child2_genes, bounds)

            offspring.append(Individual(child1_genes))
            offspring.append(Individual(child2_genes))

        return offspring

    def _sbx_crossover(
        self,
        parent1: np.ndarray,
        parent2: np.ndarray,
        bounds: np.ndarray,
        eta: float = 20.0
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulated Binary Crossover (SBX)."""
        child1 = parent1.copy()
        child2 = parent2.copy()

        for i in range(len(parent1)):
            if np.random.random() < 0.5:
                if abs(parent1[i] - parent2[i]) > 1e-14:
                    # Calculate beta
                    u = np.random.random()
                    if u <= 0.5:
                        beta = (2.0 * u) ** (1.0 / (eta + 1.0))
                    else:
                        beta = (1.0 / (2.0 * (1.0 - u))) ** (1.0 / (eta + 1.0))

                    # Create offspring
                    child1[i] = 0.5 * ((1.0 + beta) * parent1[i] + (1.0 - beta) * parent2[i])
                    child2[i] = 0.5 * ((1.0 - beta) * parent1[i] + (1.0 + beta) * parent2[i])

                    # Apply bounds
                    child1[i] = np.clip(child1[i], bounds[i, 0], bounds[i, 1])
                    child2[i] = np.clip(child2[i], bounds[i, 0], bounds[i, 1])

        return child1, child2

    def _polynomial_mutation(
        self,
        individual: np.ndarray,
        bounds: np.ndarray,
        eta: float = 20.0
    ) -> np.ndarray:
        """Polynomial mutation."""
        mutated = individual.copy()

        for i in range(len(individual)):
            if np.random.random() < self.config.mutation_rate:
                u = np.random.random()
                delta_max = bounds[i, 1] - bounds[i, 0]

                if u < 0.5:
                    delta = (2.0 * u) ** (1.0 / (eta + 1.0)) - 1.0
                else:
                    delta = 1.0 - (2.0 * (1.0 - u)) ** (1.0 / (eta + 1.0))

                mutated[i] += delta * delta_max
                mutated[i] = np.clip(mutated[i], bounds[i, 0], bounds[i, 1])

        return mutated

    def _survival_selection(self, offspring: List[Individual]) -> None:
        """Select survivors (elitism + offspring)."""
        # Sort current population by fitness
        self.population.sort(key=lambda ind: ind.fitness)

        # Keep elite individuals
        n_elite = int(self.config.elitism_ratio * self.config.population_size)
        elite = self.population[:n_elite]

        # Fill rest with best offspring
        offspring.sort(key=lambda ind: ind.fitness)
        n_offspring = self.config.population_size - n_elite
        new_population = elite + offspring[:n_offspring]

        self.population = new_population

    def _update_best(self) -> None:
        """Update best individual."""
        best = min(self.population, key=lambda ind: ind.fitness)

        if self.best_individual is None or best.fitness < self.best_individual.fitness:
            self.best_individual = best.copy()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get optimization history."""
        return self.history

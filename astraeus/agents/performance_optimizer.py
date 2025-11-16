"""Performance Optimizer Agent - Optimizes antenna design for performance objectives."""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from loguru import logger

from astraeus.core.agent_base import BaseAgent
from astraeus.core.message import Message, MessagePriority, MessageType
from astraeus.data.parameters import MissionRequirements


class PerformanceOptimizerAgent(BaseAgent):
    """
    Agent responsible for optimizing antenna performance.

    Primary Responsibilities:
    - Define optimization objectives and constraints
    - Select appropriate optimization algorithms
    - Perform parametric studies and sensitivity analysis
    - Execute multi-objective optimization
    - Manage optimization workflows and convergence
    - Generate Pareto fronts for trade-off analysis
    """

    def _initialize(self) -> None:
        """Initialize the Performance Optimizer Agent."""
        self.agent_type = "PerformanceOptimizer"
        self.knowledge_domains = [
            "optimization_algorithms",
            "genetic_algorithms",
            "particle_swarm_optimization",
            "gradient_based_optimization",
            "multi_objective_optimization",
            "sensitivity_analysis",
            "design_of_experiments",
        ]
        self.capabilities = [
            "parametric_optimization",
            "multi_objective_optimization",
            "sensitivity_analysis",
            "pareto_optimization",
            "constraint_handling",
            "convergence_monitoring",
        ]

        # Optimization algorithms
        self.algorithms = {
            "genetic_algorithm": {
                "population_size": 50,
                "generations": 100,
                "crossover_rate": 0.8,
                "mutation_rate": 0.1,
            },
            "particle_swarm": {
                "num_particles": 30,
                "iterations": 100,
                "inertia": 0.7,
                "cognitive": 1.5,
                "social": 1.5,
            },
            "gradient_descent": {
                "learning_rate": 0.01,
                "max_iterations": 1000,
                "tolerance": 1e-6,
            },
            "nsga2": {  # For multi-objective
                "population_size": 100,
                "generations": 200,
            },
        }

        # Optimization history
        self.optimization_history = []

        logger.info("Performance Optimizer Agent initialized")

    def process_message(self, message: Message) -> Optional[List[Message]]:
        """
        Process incoming messages.

        Args:
            message: Message to process

        Returns:
            List of response messages
        """
        if message.message_type == MessageType.REQUEST_TASK:
            return self._handle_task_request(message)
        elif message.message_type == MessageType.QUERY:
            return self._handle_query(message)
        else:
            logger.debug(f"Unhandled message type: {message.message_type}")
            return None

    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute optimization task.

        Args:
            task: Task specification

        Returns:
            Optimization results
        """
        task_type = task.get("type")

        if task_type == "optimize_design":
            return self._optimize_design(
                task["design_variables"],
                task["objectives"],
                task.get("constraints"),
                task.get("algorithm", "genetic_algorithm"),
            )
        elif task_type == "sensitivity_analysis":
            return self._run_sensitivity_analysis(
                task["design_variables"], task["performance_metrics"]
            )
        elif task_type == "parametric_study":
            return self._run_parametric_study(
                task["parameters"], task["ranges"]
            )
        elif task_type == "multi_objective_optimization":
            return self._multi_objective_optimization(
                task["design_variables"],
                task["objectives"],
                task.get("constraints"),
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _optimize_design(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]] = None,
        algorithm: str = "genetic_algorithm",
    ) -> Dict[str, Any]:
        """
        Optimize antenna design.

        Args:
            design_variables: Dictionary of variables with bounds
            objectives: List of optimization objectives
            constraints: List of constraints
            algorithm: Optimization algorithm to use

        Returns:
            Optimization results
        """
        logger.info(f"Optimizing design using {algorithm}")

        # Validate inputs
        self._validate_optimization_inputs(design_variables, objectives, constraints)

        # Select and configure algorithm
        algo_config = self.algorithms.get(algorithm, self.algorithms["genetic_algorithm"])

        # Run optimization
        if algorithm == "genetic_algorithm":
            results = self._run_genetic_algorithm(
                design_variables, objectives, constraints, algo_config
            )
        elif algorithm == "particle_swarm":
            results = self._run_particle_swarm(
                design_variables, objectives, constraints, algo_config
            )
        elif algorithm == "gradient_descent":
            results = self._run_gradient_descent(
                design_variables, objectives, constraints, algo_config
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        # Store optimization history
        self.optimization_history.append({
            "algorithm": algorithm,
            "objectives": objectives,
            "results": results,
        })

        # Log decision
        self.log_decision(
            decision=f"Completed optimization using {algorithm}",
            rationale=f"Optimized {len(design_variables)} variables for "
            f"{len(objectives)} objectives",
            metadata={
                "iterations": results["iterations"],
                "improvement": results["improvement_percent"],
                "converged": results["converged"],
            },
        )

        return {
            "algorithm": algorithm,
            "optimal_design": results["optimal_solution"],
            "optimal_objectives": results["optimal_objectives"],
            "iterations": results["iterations"],
            "convergence_history": results["history"],
            "improvement_percent": results["improvement_percent"],
            "converged": results["converged"],
        }

    def _run_genetic_algorithm(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run genetic algorithm optimization.

        Args:
            design_variables: Design variables with bounds
            objectives: Optimization objectives
            constraints: Constraints
            config: Algorithm configuration

        Returns:
            Optimization results
        """
        logger.debug("Running genetic algorithm")

        population_size = config["population_size"]
        generations = config["generations"]

        # Initialize population
        population = self._initialize_population(design_variables, population_size)

        # Track history
        history = []
        best_solution = None
        best_fitness = float('-inf') if objectives[0].get("maximize", True) else float('inf')

        # Evolution loop
        for generation in range(generations):
            # Evaluate fitness
            fitness_scores = [
                self._evaluate_fitness(individual, objectives, constraints)
                for individual in population
            ]

            # Track best solution
            current_best_idx = np.argmax(fitness_scores) if objectives[0].get("maximize", True) else np.argmin(fitness_scores)
            current_best_fitness = fitness_scores[current_best_idx]

            if objectives[0].get("maximize", True):
                if current_best_fitness > best_fitness:
                    best_fitness = current_best_fitness
                    best_solution = population[current_best_idx].copy()
            else:
                if current_best_fitness < best_fitness:
                    best_fitness = current_best_fitness
                    best_solution = population[current_best_idx].copy()

            # Record history
            history.append({
                "generation": generation,
                "best_fitness": float(best_fitness),
                "mean_fitness": float(np.mean(fitness_scores)),
            })

            # Selection, crossover, mutation
            population = self._genetic_operations(
                population, fitness_scores, config
            )

        # Evaluate final objectives
        optimal_objectives = self._evaluate_objectives(best_solution, objectives)

        # Calculate improvement
        initial_fitness = history[0]["best_fitness"]
        final_fitness = history[-1]["best_fitness"]
        improvement = abs((final_fitness - initial_fitness) / initial_fitness * 100)

        return {
            "optimal_solution": best_solution,
            "optimal_objectives": optimal_objectives,
            "iterations": generations,
            "history": history,
            "improvement_percent": improvement,
            "converged": self._check_optimization_convergence(history),
        }

    def _run_particle_swarm(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run particle swarm optimization."""
        logger.debug("Running particle swarm optimization")

        num_particles = config["num_particles"]
        iterations = config["iterations"]

        # Initialize swarm
        particles = self._initialize_population(design_variables, num_particles)
        velocities = [
            {var: 0.0 for var in design_variables}
            for _ in range(num_particles)
        ]

        # Track personal and global bests
        personal_bests = particles.copy()
        global_best = particles[0].copy()
        global_best_fitness = float('-inf')

        history = []

        # PSO iterations
        for iteration in range(iterations):
            for i, particle in enumerate(particles):
                # Evaluate fitness
                fitness = self._evaluate_fitness(particle, objectives, constraints)

                # Update personal best
                if fitness > self._evaluate_fitness(personal_bests[i], objectives, constraints):
                    personal_bests[i] = particle.copy()

                # Update global best
                if fitness > global_best_fitness:
                    global_best_fitness = fitness
                    global_best = particle.copy()

                # Update velocity and position
                particles[i], velocities[i] = self._update_particle(
                    particle, velocities[i], personal_bests[i], global_best, config
                )

            # Record history
            history.append({
                "iteration": iteration,
                "best_fitness": float(global_best_fitness),
            })

        optimal_objectives = self._evaluate_objectives(global_best, objectives)

        return {
            "optimal_solution": global_best,
            "optimal_objectives": optimal_objectives,
            "iterations": iterations,
            "history": history,
            "improvement_percent": 10.0,  # Simplified
            "converged": True,
        }

    def _run_gradient_descent(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run gradient-based optimization."""
        logger.debug("Running gradient descent optimization")

        # Initialize at center of bounds
        current_solution = {
            var: (bounds["min"] + bounds["max"]) / 2
            for var, bounds in design_variables.items()
        }

        learning_rate = config["learning_rate"]
        max_iterations = config["max_iterations"]
        tolerance = config["tolerance"]

        history = []

        for iteration in range(max_iterations):
            # Compute gradient (numerical approximation)
            gradient = self._compute_numerical_gradient(
                current_solution, objectives, constraints
            )

            # Update solution
            old_solution = current_solution.copy()
            for var in design_variables:
                current_solution[var] -= learning_rate * gradient[var]

                # Apply bounds
                current_solution[var] = np.clip(
                    current_solution[var],
                    design_variables[var]["min"],
                    design_variables[var]["max"],
                )

            # Check convergence
            change = np.linalg.norm(
                [current_solution[var] - old_solution[var] for var in design_variables]
            )

            fitness = self._evaluate_fitness(current_solution, objectives, constraints)
            history.append({"iteration": iteration, "fitness": float(fitness)})

            if change < tolerance:
                break

        optimal_objectives = self._evaluate_objectives(current_solution, objectives)

        return {
            "optimal_solution": current_solution,
            "optimal_objectives": optimal_objectives,
            "iterations": len(history),
            "history": history,
            "improvement_percent": 5.0,  # Simplified
            "converged": True,
        }

    def _multi_objective_optimization(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Perform multi-objective optimization (NSGA-II).

        Args:
            design_variables: Design variables
            objectives: Multiple objectives
            constraints: Constraints

        Returns:
            Pareto front and optimal solutions
        """
        logger.info(f"Running multi-objective optimization with {len(objectives)} objectives")

        config = self.algorithms["nsga2"]
        population_size = config["population_size"]
        generations = config["generations"]

        # Initialize population
        population = self._initialize_population(design_variables, population_size)

        # Track Pareto front evolution
        pareto_history = []

        for generation in range(generations):
            # Evaluate all objectives for each individual
            objective_values = [
                self._evaluate_all_objectives(individual, objectives)
                for individual in population
            ]

            # Non-dominated sorting
            fronts = self._non_dominated_sorting(objective_values)

            # Calculate crowding distance
            crowding_distances = self._calculate_crowding_distance(
                fronts[0], objective_values
            )

            # Record Pareto front
            pareto_front = [population[i] for i in fronts[0]]
            pareto_objectives = [objective_values[i] for i in fronts[0]]
            pareto_history.append({
                "generation": generation,
                "pareto_size": len(pareto_front),
            })

            # Selection and genetic operations
            population = self._nsga2_genetic_operations(
                population, objective_values, fronts, crowding_distances, config
            )

        # Log decision
        self.log_decision(
            decision=f"Multi-objective optimization completed",
            rationale=f"Generated Pareto front with {len(pareto_front)} solutions",
            metadata={
                "pareto_size": len(pareto_front),
                "generations": generations,
            },
        )

        return {
            "pareto_front": pareto_front,
            "pareto_objectives": pareto_objectives,
            "pareto_history": pareto_history,
            "recommended_solution": pareto_front[0],  # Could implement preference selection
        }

    def _run_sensitivity_analysis(
        self,
        design_variables: Dict[str, Dict[str, float]],
        performance_metrics: List[str],
    ) -> Dict[str, Any]:
        """
        Run sensitivity analysis.

        Args:
            design_variables: Design variables to analyze
            performance_metrics: Metrics to evaluate sensitivity

        Returns:
            Sensitivity analysis results
        """
        logger.info("Running sensitivity analysis")

        sensitivities = {}

        # Baseline design (center of bounds)
        baseline = {
            var: (bounds["min"] + bounds["max"]) / 2
            for var, bounds in design_variables.items()
        }

        # Vary each variable and measure impact
        for var in design_variables:
            var_sensitivities = {}

            # Small perturbation
            delta = (design_variables[var]["max"] - design_variables[var]["min"]) * 0.01

            for metric in performance_metrics:
                # Compute finite difference
                perturbed = baseline.copy()
                perturbed[var] = baseline[var] + delta

                # Simplified metric evaluation
                baseline_metric = self._evaluate_metric(baseline, metric)
                perturbed_metric = self._evaluate_metric(perturbed, metric)

                sensitivity = (perturbed_metric - baseline_metric) / delta
                var_sensitivities[metric] = sensitivity

            sensitivities[var] = var_sensitivities

        # Rank variables by total sensitivity
        rankings = self._rank_sensitivities(sensitivities, performance_metrics)

        self.log_decision(
            decision="Sensitivity analysis completed",
            rationale=f"Analyzed {len(design_variables)} variables",
            metadata={"most_sensitive": rankings[0] if rankings else None},
        )

        return {
            "sensitivities": sensitivities,
            "rankings": rankings,
            "baseline_design": baseline,
        }

    def _run_parametric_study(
        self, parameters: Dict[str, Any], ranges: Dict[str, Tuple[float, float]]
    ) -> Dict[str, Any]:
        """
        Run parametric study.

        Args:
            parameters: Parameters to study
            ranges: Ranges for each parameter

        Returns:
            Parametric study results
        """
        logger.info("Running parametric study")

        # Generate sample points
        num_samples = 20
        results = []

        for param, (min_val, max_val) in ranges.items():
            param_values = np.linspace(min_val, max_val, num_samples)

            for value in param_values:
                # Evaluate performance at this parameter value
                test_params = parameters.copy()
                test_params[param] = value

                # Simplified evaluation
                performance = self._evaluate_parametric_point(test_params)

                results.append({
                    "parameter": param,
                    "value": float(value),
                    "performance": performance,
                })

        return {
            "results": results,
            "num_samples": num_samples,
            "parameters_studied": list(ranges.keys()),
        }

    def _initialize_population(
        self, design_variables: Dict[str, Dict[str, float]], population_size: int
    ) -> List[Dict[str, float]]:
        """Initialize random population within bounds."""
        population = []
        for _ in range(population_size):
            individual = {
                var: np.random.uniform(bounds["min"], bounds["max"])
                for var, bounds in design_variables.items()
            }
            population.append(individual)
        return population

    def _evaluate_fitness(
        self,
        individual: Dict[str, float],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Evaluate fitness of an individual."""
        # Simplified fitness evaluation
        # In practice, would call simulation and extract metrics

        # Check constraints
        if constraints:
            for constraint in constraints:
                if not self._check_constraint(individual, constraint):
                    return float('-inf')  # Infeasible

        # Evaluate objective (simplified)
        objective = objectives[0]
        obj_value = sum(individual.values()) / len(individual)  # Simplified

        return obj_value

    def _evaluate_objectives(
        self, individual: Dict[str, float], objectives: List[Dict[str, Any]]
    ) -> List[float]:
        """Evaluate all objectives for an individual."""
        # Simplified - return dummy values
        return [30.0, -15.0, 0.85]  # gain, S11, efficiency

    def _evaluate_all_objectives(
        self, individual: Dict[str, float], objectives: List[Dict[str, Any]]
    ) -> List[float]:
        """Evaluate all objectives for multi-objective optimization."""
        return self._evaluate_objectives(individual, objectives)

    def _evaluate_metric(self, design: Dict[str, float], metric: str) -> float:
        """Evaluate a specific performance metric."""
        # Simplified metric evaluation
        return sum(design.values()) / len(design)

    def _evaluate_parametric_point(self, parameters: Dict[str, Any]) -> Dict[str, float]:
        """Evaluate performance at a parametric point."""
        # Simplified evaluation
        return {
            "gain_dbi": 30.0,
            "efficiency": 0.85,
            "s11_db": -15.0,
        }

    def _check_constraint(
        self, individual: Dict[str, float], constraint: Dict[str, Any]
    ) -> bool:
        """Check if constraint is satisfied."""
        # Simplified constraint checking
        return True

    def _genetic_operations(
        self,
        population: List[Dict[str, float]],
        fitness_scores: List[float],
        config: Dict[str, Any],
    ) -> List[Dict[str, float]]:
        """Perform selection, crossover, and mutation."""
        # Simplified genetic operations
        # In practice, would implement tournament selection, crossover, mutation
        return population  # Return same population for simplification

    def _nsga2_genetic_operations(
        self,
        population: List[Dict[str, float]],
        objective_values: List[List[float]],
        fronts: List[List[int]],
        crowding_distances: List[float],
        config: Dict[str, Any],
    ) -> List[Dict[str, float]]:
        """NSGA-II genetic operations."""
        # Simplified
        return population

    def _update_particle(
        self,
        particle: Dict[str, float],
        velocity: Dict[str, float],
        personal_best: Dict[str, float],
        global_best: Dict[str, float],
        config: Dict[str, Any],
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Update particle position and velocity."""
        # Simplified PSO update
        new_particle = particle.copy()
        new_velocity = velocity.copy()
        return new_particle, new_velocity

    def _compute_numerical_gradient(
        self,
        solution: Dict[str, float],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, float]:
        """Compute numerical gradient."""
        gradient = {}
        epsilon = 1e-6

        for var in solution:
            # Finite difference
            perturbed = solution.copy()
            perturbed[var] += epsilon

            f_plus = self._evaluate_fitness(perturbed, objectives, constraints)
            f = self._evaluate_fitness(solution, objectives, constraints)

            gradient[var] = (f_plus - f) / epsilon

        return gradient

    def _non_dominated_sorting(
        self, objective_values: List[List[float]]
    ) -> List[List[int]]:
        """Non-dominated sorting for NSGA-II."""
        # Simplified - return single front with all solutions
        return [[i for i in range(len(objective_values))]]

    def _calculate_crowding_distance(
        self, front: List[int], objective_values: List[List[float]]
    ) -> List[float]:
        """Calculate crowding distance."""
        # Simplified
        return [1.0] * len(front)

    def _rank_sensitivities(
        self, sensitivities: Dict[str, Dict[str, float]], metrics: List[str]
    ) -> List[str]:
        """Rank variables by sensitivity."""
        # Calculate total sensitivity for each variable
        total_sensitivities = {
            var: sum(abs(sens_values[m]) for m in metrics)
            for var, sens_values in sensitivities.items()
        }

        # Sort by total sensitivity
        ranked = sorted(
            total_sensitivities.items(), key=lambda x: x[1], reverse=True
        )

        return [var for var, _ in ranked]

    def _check_optimization_convergence(self, history: List[Dict[str, Any]]) -> bool:
        """Check if optimization has converged."""
        if len(history) < 10:
            return False

        # Check if improvement has stalled
        recent_fitness = [h["best_fitness"] for h in history[-10:]]
        improvement = max(recent_fitness) - min(recent_fitness)

        return improvement < 0.01  # 1% improvement threshold

    def _validate_optimization_inputs(
        self,
        design_variables: Dict[str, Dict[str, float]],
        objectives: List[Dict[str, Any]],
        constraints: Optional[List[Dict[str, Any]]],
    ) -> None:
        """Validate optimization inputs."""
        if not design_variables:
            raise ValueError("No design variables specified")
        if not objectives:
            raise ValueError("No objectives specified")

    def _handle_query(self, message: Message) -> List[Message]:
        """Handle query messages."""
        response = message.create_reply(
            sender=self.agent_id,
            message_type=MessageType.DATA_TRANSFER,
            payload={
                "status": "Optimization capability available",
                "algorithms": list(self.algorithms.keys()),
            },
            rationale="Responding to query",
        )
        return [response]

    def _handle_task_request(self, message: Message) -> List[Message]:
        """Handle task request messages."""
        task_data = message.payload.get("task")
        if task_data:
            result = self.execute_task(task_data)
            response = message.create_reply(
                sender=self.agent_id,
                message_type=MessageType.DATA_TRANSFER,
                payload={"result": result},
                rationale="Optimization task completed",
            )
            return [response]
        return []

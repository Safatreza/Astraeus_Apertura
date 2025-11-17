"""
Parametric Sweep Example using Parallel Job Scheduler.

This example demonstrates how to use the job scheduling system to run
a parametric sweep of antenna designs in parallel, exploring the design
space efficiently across multiple workers.

We'll sweep patch antenna dimensions and frequency to find optimal designs.
"""

import sys
import time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from astraeus.scheduling import (
    SimulationJob,
    JobQueue,
    JobPriority,
    WorkerPool,
    JobMonitor
)
from astraeus.data.parameters import DesignParameters, PerformanceMetrics
from astraeus.utils.antenna_math import AntennaMath


def simulate_patch_antenna(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a patch antenna (simplified analytical model).

    In production, this would call ANSYS HFSS or other EM simulator.

    Args:
        params: Dictionary with 'width', 'length', 'frequency_ghz', 'substrate_height'

    Returns:
        Dictionary with performance metrics
    """
    width = params['width']
    length = params['length']
    freq_ghz = params['frequency_ghz']
    substrate_height = params.get('substrate_height', 1.6)  # mm
    epsilon_r = params.get('epsilon_r', 4.4)  # FR4

    # Simulate some execution time
    time.sleep(np.random.uniform(0.1, 0.5))

    # Calculate wavelength
    c = 3e8  # m/s
    wavelength_m = c / (freq_ghz * 1e9)
    wavelength_mm = wavelength_m * 1000

    # Resonant frequency (simplified)
    # For rectangular patch: f_r = c / (2 * L_eff * sqrt(epsilon_eff))
    L_eff = length + 2 * substrate_height  # Simplified fringe extension
    epsilon_eff = (epsilon_r + 1) / 2 + (epsilon_r - 1) / 2 * (1 + 12 * substrate_height / width) ** (-0.5)

    resonant_freq_ghz = c / (2 * L_eff * 1e-3 * np.sqrt(epsilon_eff)) / 1e9

    # Calculate metrics based on how close we are to resonance
    freq_error = abs(resonant_freq_ghz - freq_ghz)

    # Gain (simplified model based on aperture)
    aperture_area_m2 = (width * length) / 1e6
    efficiency = 0.8 * np.exp(-freq_error / 0.5)  # Drops off away from resonance
    gain_dbi = AntennaMath.gain_from_aperture(aperture_area_m2, wavelength_m, efficiency)

    # VSWR (lower near resonance)
    vswr = 1.0 + freq_error * 5.0

    # Beamwidth
    beamwidth_deg = AntennaMath.beamwidth_from_gain(gain_dbi)

    # Bandwidth (simplified)
    bandwidth_mhz = 50 * efficiency

    # Directivity
    directivity_dbi = gain_dbi / efficiency if efficiency > 0 else 0

    return {
        'gain_dbi': gain_dbi,
        'vswr': vswr,
        'bandwidth_mhz': bandwidth_mhz,
        'beamwidth_deg': beamwidth_deg,
        'efficiency': efficiency,
        'directivity_dbi': directivity_dbi,
        'resonant_freq_ghz': resonant_freq_ghz,
        'freq_error_ghz': freq_error,
    }


def run_parametric_sweep():
    """
    Run a parametric sweep of patch antenna designs.

    Sweeps:
    - Patch width: 30-50 mm
    - Patch length: 30-50 mm
    - Frequency: 2.0-2.5 GHz
    """
    print("="*70)
    print("PARAMETRIC SWEEP: Patch Antenna Design Space Exploration")
    print("="*70)
    print()

    # Define parameter ranges
    widths = np.linspace(30, 50, 5)  # mm
    lengths = np.linspace(30, 50, 5)  # mm
    frequencies = np.linspace(2.0, 2.5, 5)  # GHz

    print(f"Parameter Space:")
    print(f"  Width:     {widths[0]:.1f} - {widths[-1]:.1f} mm ({len(widths)} values)")
    print(f"  Length:    {lengths[0]:.1f} - {lengths[-1]:.1f} mm ({len(lengths)} values)")
    print(f"  Frequency: {frequencies[0]:.1f} - {frequencies[-1]:.1f} GHz ({len(frequencies)} values)")
    print(f"  Total combinations: {len(widths) * len(lengths) * len(frequencies)}")
    print()

    # Initialize job queue and worker pool
    print("Initializing job scheduler...")
    job_queue = JobQueue(db_path="parametric_sweep_jobs.db")
    worker_pool = WorkerPool(job_queue, num_workers=4)

    # Register executor for patch antenna simulations
    worker_pool.register_executor('patch_antenna', simulate_patch_antenna)

    # Initialize job monitor
    monitor = JobMonitor(
        job_queue,
        update_interval=2.0,
        stats_file="parametric_sweep_stats.json"
    )

    # Start workers and monitor
    worker_pool.start()
    monitor.start()

    print(f"Started {worker_pool.num_workers} workers")
    print()

    # Submit jobs for parameter sweep
    print("Submitting jobs...")
    job_ids = []
    job_count = 0

    for width in widths:
        for length in lengths:
            for freq in frequencies:
                # Create job
                job = SimulationJob(
                    job_type='patch_antenna',
                    parameters={
                        'width': width,
                        'length': length,
                        'frequency_ghz': freq,
                        'substrate_height': 1.6,
                        'epsilon_r': 4.4,
                    },
                    priority=JobPriority.NORMAL,
                    max_retries=3,
                    timeout=10.0,
                    metadata={
                        'width': width,
                        'length': length,
                        'frequency_ghz': freq,
                    }
                )

                job_id = job_queue.submit_job(job)
                job_ids.append(job_id)
                job_count += 1

    print(f"Submitted {job_count} jobs to queue")
    print()

    # Wait for completion with progress updates
    print("Executing jobs...")
    print()

    start_time = time.time()
    last_progress = -1

    while True:
        stats = monitor.get_statistics()

        # Calculate progress
        progress = (stats.completed_jobs + stats.failed_jobs) / stats.total_jobs * 100 if stats.total_jobs > 0 else 0

        # Print progress every 10%
        if int(progress / 10) > last_progress:
            last_progress = int(progress / 10)
            elapsed = time.time() - start_time

            print(f"Progress: {progress:.0f}% ({stats.completed_jobs}/{stats.total_jobs} completed, "
                  f"{stats.failed_jobs} failed, {stats.running_jobs} running) - {elapsed:.1f}s elapsed")

        # Check if done
        if stats.pending_jobs == 0 and stats.running_jobs == 0:
            break

        time.sleep(1.0)

    # Wait for all jobs to complete
    worker_pool.wait_for_completion()

    execution_time = time.time() - start_time

    print()
    print("="*70)
    print("EXECUTION COMPLETE")
    print("="*70)
    print()

    # Print summary
    monitor.print_summary()

    # Collect results
    print("Collecting results...")
    results = []

    for job_id in job_ids:
        job = job_queue.get_job(job_id)
        if job and job.result:
            results.append({
                'width': job.metadata['width'],
                'length': job.metadata['length'],
                'frequency_ghz': job.metadata['frequency_ghz'],
                **job.result
            })

    print(f"Collected {len(results)} results")
    print()

    # Analyze results
    if results:
        analyze_results(results, widths, lengths, frequencies)

    # Export report
    print("Exporting reports...")
    monitor.export_report("parametric_sweep_report.md")
    monitor.export_report("parametric_sweep_report.json")
    print("Reports exported")
    print()

    # Stop workers and monitor
    monitor.stop()
    worker_pool.stop()

    print(f"Total execution time: {execution_time:.2f} seconds")
    print()


def analyze_results(results, widths, lengths, frequencies):
    """Analyze and visualize parametric sweep results."""
    print("="*70)
    print("RESULTS ANALYSIS")
    print("="*70)
    print()

    # Convert to numpy arrays for analysis
    gains = np.array([r['gain_dbi'] for r in results])
    vswrs = np.array([r['vswr'] for r in results])
    efficiencies = np.array([r['efficiency'] for r in results])

    # Find best designs
    best_gain_idx = np.argmax(gains)
    best_vswr_idx = np.argmin(vswrs)

    print("Best Designs:")
    print()
    print(f"Highest Gain: {gains[best_gain_idx]:.2f} dBi")
    print(f"  Width:     {results[best_gain_idx]['width']:.1f} mm")
    print(f"  Length:    {results[best_gain_idx]['length']:.1f} mm")
    print(f"  Frequency: {results[best_gain_idx]['frequency_ghz']:.2f} GHz")
    print(f"  VSWR:      {results[best_gain_idx]['vswr']:.2f}")
    print(f"  Efficiency: {results[best_gain_idx]['efficiency']:.1%}")
    print()

    print(f"Best VSWR: {vswrs[best_vswr_idx]:.2f}")
    print(f"  Width:     {results[best_vswr_idx]['width']:.1f} mm")
    print(f"  Length:    {results[best_vswr_idx]['length']:.1f} mm")
    print(f"  Frequency: {results[best_vswr_idx]['frequency_ghz']:.2f} GHz")
    print(f"  Gain:      {results[best_vswr_idx]['gain_dbi']:.2f} dBi")
    print(f"  Efficiency: {results[best_vswr_idx]['efficiency']:.1%}")
    print()

    # Statistics
    print("Overall Statistics:")
    print(f"  Gain:       {np.mean(gains):.2f} ± {np.std(gains):.2f} dBi")
    print(f"  VSWR:       {np.mean(vswrs):.2f} ± {np.std(vswrs):.2f}")
    print(f"  Efficiency: {np.mean(efficiencies):.1%} ± {np.std(efficiencies):.1%}")
    print()

    # Filter for good designs (gain > 6 dBi, VSWR < 2.0)
    good_designs = [r for r in results if r['gain_dbi'] > 6.0 and r['vswr'] < 2.0]
    print(f"Designs meeting criteria (Gain > 6 dBi, VSWR < 2.0): {len(good_designs)}/{len(results)}")
    print()

    # Create visualization
    try:
        visualize_results(results, widths, lengths, frequencies)
        print("Visualizations saved to 'parametric_sweep_results.png'")
        print()
    except Exception as e:
        print(f"Failed to create visualizations: {e}")
        print()


def visualize_results(results, widths, lengths, frequencies):
    """Create visualization of parametric sweep results."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    fig.suptitle('Parametric Sweep Results: Patch Antenna Design Space', fontsize=14, fontweight='bold')

    # Extract data
    W = np.array([r['width'] for r in results])
    L = np.array([r['length'] for r in results])
    F = np.array([r['frequency_ghz'] for r in results])
    G = np.array([r['gain_dbi'] for r in results])
    V = np.array([r['vswr'] for r in results])
    E = np.array([r['efficiency'] for r in results])

    # 1. Gain vs Width and Length (at middle frequency)
    mid_freq = frequencies[len(frequencies)//2]
    mask = np.abs(F - mid_freq) < 0.01

    scatter1 = axes[0, 0].scatter(W[mask], L[mask], c=G[mask], s=100, cmap='viridis', edgecolors='black')
    axes[0, 0].set_xlabel('Width (mm)')
    axes[0, 0].set_ylabel('Length (mm)')
    axes[0, 0].set_title(f'Gain vs Dimensions @ {mid_freq:.2f} GHz')
    axes[0, 0].grid(True, alpha=0.3)
    plt.colorbar(scatter1, ax=axes[0, 0], label='Gain (dBi)')

    # 2. VSWR vs Width and Length
    scatter2 = axes[0, 1].scatter(W[mask], L[mask], c=V[mask], s=100, cmap='coolwarm_r', edgecolors='black')
    axes[0, 1].set_xlabel('Width (mm)')
    axes[0, 1].set_ylabel('Length (mm)')
    axes[0, 1].set_title(f'VSWR vs Dimensions @ {mid_freq:.2f} GHz')
    axes[0, 1].grid(True, alpha=0.3)
    plt.colorbar(scatter2, ax=axes[0, 1], label='VSWR')

    # 3. Efficiency vs Width and Length
    scatter3 = axes[0, 2].scatter(W[mask], L[mask], c=E[mask], s=100, cmap='RdYlGn', edgecolors='black')
    axes[0, 2].set_xlabel('Width (mm)')
    axes[0, 2].set_ylabel('Length (mm)')
    axes[0, 2].set_title(f'Efficiency vs Dimensions @ {mid_freq:.2f} GHz')
    axes[0, 2].grid(True, alpha=0.3)
    plt.colorbar(scatter3, ax=axes[0, 2], label='Efficiency')

    # 4. Gain vs Frequency (at middle dimensions)
    mid_width = widths[len(widths)//2]
    mid_length = lengths[len(lengths)//2]
    mask_dim = (np.abs(W - mid_width) < 0.1) & (np.abs(L - mid_length) < 0.1)

    axes[1, 0].plot(F[mask_dim], G[mask_dim], 'o-', linewidth=2, markersize=8)
    axes[1, 0].set_xlabel('Frequency (GHz)')
    axes[1, 0].set_ylabel('Gain (dBi)')
    axes[1, 0].set_title(f'Gain vs Frequency @ W={mid_width:.1f}mm, L={mid_length:.1f}mm')
    axes[1, 0].grid(True, alpha=0.3)

    # 5. Pareto front: Gain vs VSWR
    axes[1, 1].scatter(V, G, c=E, s=100, cmap='plasma', edgecolors='black', alpha=0.6)
    axes[1, 1].set_xlabel('VSWR')
    axes[1, 1].set_ylabel('Gain (dBi)')
    axes[1, 1].set_title('Trade-off: Gain vs VSWR')
    axes[1, 1].grid(True, alpha=0.3)

    # Highlight good designs
    good_mask = (G > 6.0) & (V < 2.0)
    axes[1, 1].scatter(V[good_mask], G[good_mask], s=200, facecolors='none', edgecolors='red', linewidths=2, label='Good Designs')
    axes[1, 1].legend()

    # 6. Histogram of gain distribution
    axes[1, 2].hist(G, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
    axes[1, 2].axvline(np.mean(G), color='red', linestyle='--', linewidth=2, label=f'Mean: {np.mean(G):.2f} dBi')
    axes[1, 2].axvline(np.median(G), color='green', linestyle='--', linewidth=2, label=f'Median: {np.median(G):.2f} dBi')
    axes[1, 2].set_xlabel('Gain (dBi)')
    axes[1, 2].set_ylabel('Frequency')
    axes[1, 2].set_title('Gain Distribution')
    axes[1, 2].legend()
    axes[1, 2].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('parametric_sweep_results.png', dpi=300, bbox_inches='tight')
    print("Saved visualization to 'parametric_sweep_results.png'")


if __name__ == '__main__':
    try:
        run_parametric_sweep()

        print()
        print("="*70)
        print("PARAMETRIC SWEEP COMPLETE")
        print("="*70)
        print()
        print("Output files:")
        print("  - parametric_sweep_jobs.db (job database)")
        print("  - parametric_sweep_stats.json (statistics)")
        print("  - parametric_sweep_report.md (markdown report)")
        print("  - parametric_sweep_report.json (JSON report)")
        print("  - parametric_sweep_results.png (visualizations)")
        print()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

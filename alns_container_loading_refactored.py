"""
ALNS framework for container loading using the official ALNS library.
Refactored from custom ALNS loop to use alns library.
"""
import copy
import json
import time
import os
import sys
from collections import defaultdict

# ALNS library imports
from alns import ALNS
from alns.accept import HillClimbing, RecordToRecordTravel, SimulatedAnnealing
from alns.select import RouletteWheel
from alns.stop import MaxRuntime, MaxIterations, NoImprovement


class CombinedStoppingCriterion:
    """Combines multiple stopping criteria - stops when ANY criterion is met."""
    
    def __init__(self, *criteria):
        self.criteria = criteria
        
    def __call__(self, rng, best, current):
        """Return True if any of the criteria say to stop."""
        return any(criterion(rng, best, current) for criterion in self.criteria)

import numpy as np
import numpy.random as rnd

# Existing imports
from step2_container_box_placement_in_container import run_phase_2
from assignment_model import build_step1_assignment_model
from print_utils import dump_phase1_results


class ContainerLoadingState:
    """
    State class for ALNS that represents a container loading solution.
    Implements the required objective() method for the ALNS library.
    """
    
    def __init__(self, assignment, container_size, container_weight, step2_settings_file, verbose=False):
        """
        assignment: list of containers, each is a dict with 'id', 'boxes' (list of box dicts)
        container_size: [L, W, H]
        container_weight: max weight for the container
        step2_settings_file: path to settings JSON for step 2
        verbose: bool, controls solver logging
        """
        self.assignment = copy.deepcopy(assignment)
        self.container_size = container_size
        self.container_weight = container_weight
        self.step2_settings_file = step2_settings_file
        self.verbose = verbose
        self.statuses = []  # 'OPTIMAL', 'FEASIBLE', 'UNFEASIBLE' per container
        self.soft_scores = []  # soft objective scores per container (to be filled)
        self.aggregate_score = None
        self.visualization_data = []  # store visualization info per container
        self._objective_computed = False

    def objective(self) -> float:
        """
        Required method for ALNS library. Returns the objective value (lower is better).
        Since ALNS assumes minimization, we return the aggregate score directly.
        """
        if not self._objective_computed:
            self.evaluate()
        return self.aggregate_score

    def evaluate(self, verbose=False):
        """
        For each container, run step 2 and collect status and soft objective score.
        Also update each box in the assignment with its actual orientation and position.
        Store visualization info for each container.
        """
        self.statuses = []
        self.soft_scores = []
        self.visualization_data = []
        container_volume = self.container_size[0] * self.container_size[1] * self.container_size[2]
        if container_volume <= 0:
            raise ValueError(f"Invalid container volume: {container_volume}. Container dimensions: {self.container_size}")
        
        for container in self.assignment:
            print(f'**** Running phase 2 for container {container["id"]} with size {self.container_size}')
            boxes = container.get('boxes', [])
            if not boxes:
                self.statuses.append('UNFEASIBLE')
                self.soft_scores.append(1)  # worst utilization
                self.visualization_data.append(None)
                continue
            
            # Run step 2 placement and get placements and visualization info
            status, placements, vis_data = run_phase_2(
                container['id'], self.container_size, boxes, 
                self.step2_settings_file, self.verbose, False
            )
            print(f'Completed run of phase 2 for container {container["id"]} with size {self.container_size}')
            self.statuses.append(status)
            self.visualization_data.append(vis_data)
            
            # Update each box in container['boxes'] with its actual orientation and position
            # placements is a list of dicts with 'id', 'position', 'orientation', 'size', ...
            placement_map = {p['id']: p for p in placements}
            for box in boxes:
                p = placement_map.get(box['id'])
                if p is not None:
                    box['final_position'] = p['position']
                    box['final_orientation'] = p['orientation']
                    box['final_size'] = p['size']
            
            # Soft score: 1 - volume utilization (per container, for variance calculation)
            # Note: Individual scores will be used to calculate variance of utilization across containers
            # Use placements data to get the actual volume utilization after step 2 optimization
            if status in ['OPTIMAL', 'FEASIBLE'] and placements:
                # Calculate total volume of successfully placed boxes using their actual sizes from placements
                total_placed_volume = sum(p['size'][0] * p['size'][1] * p['size'][2] for p in placements)
                volume_utilization = total_placed_volume / container_volume if container_volume > 0 else 0
            else:
                # If step 2 failed, use original box volumes as fallback (worst case)
                total_box_volume = sum(box['size'][0] * box['size'][1] * box['size'][2] for box in boxes)
                volume_utilization = total_box_volume / container_volume if container_volume > 0 else 0
            
            score = 1 - volume_utilization  # lower is better
            self.soft_scores.append(score)
            print(f'Container {container["id"]}: status={status}, volume_utilization={volume_utilization:.3f}, soft_score={score:.3f}, n_boxes={len(boxes)}, n_placements={len(placements) if placements else 0}')
        
        # NEW SOFT SCORE: Minimize variance of container utilization percentages
        # This rewards balanced loading across containers (lower variance = better balance)
        if self.soft_scores:  # Only if we have containers
            utilization_percentages = [(1 - score) * 100 for score in self.soft_scores]  # Convert back to percentages
            mean_utilization = sum(utilization_percentages) / len(utilization_percentages)
            variance = sum((util - mean_utilization) ** 2 for util in utilization_percentages) / len(utilization_percentages)
            balance_penalty = variance / 100  # Normalize variance (0-100 range becomes 0-1)
        else:
            balance_penalty = 0
            variance = 0
            mean_utilization = 0
        
        # Aggregate score: penalize UNFEASIBLE, add balance penalty, subtract bonuses
        penalty = 1000 * self.statuses.count('UNFEASIBLE') + 500 * self.statuses.count('UNKNOWN')
        optimal_bonus = 2 * self.statuses.count('OPTIMAL')
        feasible_bonus = 1 * self.statuses.count('FEASIBLE')
        self.aggregate_score = penalty + balance_penalty - optimal_bonus - feasible_bonus
        
        # Print in blue color using ANSI escape code
        print('')
        print(f'\033[94mAggregate score: {self.aggregate_score} (penalty={penalty} + balance_penalty={balance_penalty:.3f} - optimal_bonus={optimal_bonus} - feasible_bonus={feasible_bonus})\033[0m')
        print(f'\033[94mUtilization stats: mean={mean_utilization:.1f}%, variance={variance:.1f}, percentages={[f"{p:.1f}%" for p in utilization_percentages]}\033[0m')
        
        self._objective_computed = True
        return self.aggregate_score

    def is_feasible(self):
        """Check if all containers have feasible solutions."""
        if not self._objective_computed:
            self.evaluate()
        return 'UNFEASIBLE' not in self.statuses

    def copy(self):
        """Create a deep copy of this state."""
        new_state = ContainerLoadingState(
            self.assignment, self.container_size, self.container_weight, 
            self.step2_settings_file, self.verbose
        )
        new_state.statuses = self.statuses.copy()
        new_state.soft_scores = self.soft_scores.copy()
        new_state.aggregate_score = self.aggregate_score
        new_state.visualization_data = copy.deepcopy(self.visualization_data)
        new_state._objective_computed = self._objective_computed
        return new_state


# --- ALNS Destroy Operator ---
def create_destroy_random_items(num_remove):
    """
    Factory function to create a destroy operator with configurable num_remove.
    Returns a destroy operator function compatible with ALNS library.
    """
    def destroy_random_items(current: ContainerLoadingState, rng: rnd.Generator) -> ContainerLoadingState:
        """
        ALNS destroy operator: Randomly select items and unassign them from their containers.
        Returns a new partial assignment (deep copy with some boxes removed).
        """
        # Create a deep copy first (required by ALNS)
        destroyed_state = current.copy()
        
        # Flatten all boxes with their container index
        all_boxes = [(c_idx, box_idx) for c_idx, container in enumerate(destroyed_state.assignment)
                     for box_idx in range(len(container['boxes']))]
        
        if len(all_boxes) == 0:
            return destroyed_state
        
        # Randomly select items to remove (now configurable via closure)
        remove_count = min(num_remove, len(all_boxes))
        remove_indices = rng.choice(len(all_boxes), remove_count, replace=False)
        
        removed_items = []
        for idx in remove_indices:
            c_idx, box_idx = all_boxes[idx]
            removed_items.append(destroyed_state.assignment[c_idx]['boxes'][box_idx])
            destroyed_state.assignment[c_idx]['boxes'][box_idx] = None  # Mark for removal
        
        # Remove None entries
        for container in destroyed_state.assignment:
            container['boxes'] = [box for box in container['boxes'] if box is not None]
        
        # Store removed items for the repair operator
        destroyed_state._removed_items = removed_items
        destroyed_state._objective_computed = False  # Invalidate cached objective
        
        return destroyed_state
    
    return destroy_random_items


# --- ALNS Repair Operator ---
def repair_cpsat(destroyed: ContainerLoadingState, rng: rnd.Generator) -> ContainerLoadingState:
    """
    ALNS repair operator: Use CP-SAT to optimally reassign removed items.
    Returns a new complete assignment.
    """
    # Get removed items from the destroyed state
    removed_items = getattr(destroyed, '_removed_items', [])
    if not removed_items:
        # Nothing to repair
        return destroyed
    
    # Prepare items: combine removed_items and fixed items
    all_items = []
    item_id_to_idx = {}
    
    # Add removed items first
    for i, item in enumerate(removed_items):
        all_items.append({
            'id': item['id'],
            'size': item['size'],
            'weight': item['weight'],
            'group_id': item.get('group_id'),
            'rotation': item.get('rotation')
        })
        item_id_to_idx[item['id']] = i
    
    # Add fixed items (from partial_assignment)
    fixed_assignments = {}
    fixed_item_ids = set()
    
    # Build container mapping: original container id -> zero-based index for CP-SAT
    container_id_to_cpsat_idx = {}
    for cpsat_idx, container in enumerate(destroyed.assignment):
        container_id_to_cpsat_idx[container['id']] = cpsat_idx
    
    for container in destroyed.assignment:
        for box in container['boxes']:
            if box['id'] not in item_id_to_idx:
                idx = len(all_items)
                all_items.append({
                    'id': box['id'],
                    'size': box['size'],
                    'weight': box['weight'],
                    'group_id': box.get('group_id'),
                    'rotation': box.get('rotation')
                })
                item_id_to_idx[box['id']] = idx
            # Use the correct CP-SAT container index
            fixed_assignments[box['id']] = container_id_to_cpsat_idx[container['id']]
            fixed_item_ids.add(box['id'])
    
    # Build group_to_items mapping
    group_to_items = defaultdict(list)
    for idx, item in enumerate(all_items):
        gid = item.get('group_id')
        if gid is not None:
            group_to_items[gid].append(idx)
    
    # Container count: allow new containers for removed items
    max_containers = len(destroyed.assignment) + len(removed_items)
    
    # Get container weight from the state
    container_weight = destroyed.container_weight
    
    # Build model
    group_penalty_lambda = 1
    model, x, y, group_in_containers, group_ids = build_step1_assignment_model(
        all_items,
        destroyed.container_size,
        container_weight,
        max_containers,
        group_to_items=group_to_items,
        fixed_assignments=fixed_assignments,
        group_penalty_lambda=group_penalty_lambda,
        dump_inputs=False    
    )
    
    from ortools.sat.python import cp_model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    dump_phase1_results(
        solver, status, x, y, group_in_containers, group_ids, group_to_items,
        all_items, destroyed.container_size, container_weight, verbose=False)

    # Build new assignment structure - use sequential container IDs
    new_assignment = []
    used_cpsat_indices = [j for j in range(max_containers) if solver.Value(y[j])]
    
    for cpsat_idx in used_cpsat_indices:
        new_assignment.append({'id': len(new_assignment) + 1, 'size': destroyed.container_size, 'boxes': []})
    
    # Assign items to containers using correct mapping
    for i in range(len(all_items)):
        for cpsat_idx in used_cpsat_indices:
            if solver.Value(x[i, cpsat_idx]):
                # Find which new_assignment container corresponds to this cpsat_idx
                new_container_idx = used_cpsat_indices.index(cpsat_idx)
                new_assignment[new_container_idx]['boxes'].append(all_items[i])
                break
    
    # Create new state with repaired assignment
    repaired_state = ContainerLoadingState(
        new_assignment, destroyed.container_size, destroyed.container_weight, 
        destroyed.step2_settings_file, destroyed.verbose
    )
    return repaired_state





class StoppingCriterionWithProgress:
    """
    A custom stopping criterion that wraps other criteria and prints progress.
    """
    def __init__(self, max_iterations, max_no_improve):
        self.max_iterations = max_iterations
        self.max_no_improve = max_no_improve
        self.iteration = 0
        self.no_improve = 0

    def __call__(self, rng, best, current):
        self.iteration += 1
        
        # Check if the best solution has improved
        if best.objective() < getattr(self, '_last_best_obj', float('inf')):
            self._last_best_obj = best.objective()
            self.no_improve = 0
        else:
            self.no_improve += 1
            
        # Print progress
        progress_bar = f"Iteration {self.iteration}/{self.max_iterations} | "
        progress_bar += f"No improvement {self.no_improve}/{self.max_no_improve}"
        print(progress_bar, end='\r') # Use carriage return to print on the same line

        # Check stopping conditions
        if self.iteration >= self.max_iterations:
            print("\nStopping: Max iterations reached.")
            return True
        if self.no_improve >= self.max_no_improve:
            print("\nStopping: Max no improvement reached.")
            return True
            
        return False

# --- Custom ALNS Acceptance Criterion ---
class CustomContainerAcceptance:
    """
    Custom acceptance criterion that mimics the original acceptance_criteria function.
    Accept if all containers are at least FEASIBLE and aggregate score improves, 
    or with a 5% random chance.
    """
    
    def __call__(self, rng, best, current, candidate):
        """
        ALNS acceptance criterion interface.
        
        Args:
            rng: Random number generator
            best: Best state found so far
            current: Current state
            candidate: Candidate state to evaluate
            
        Returns:
            bool: True if candidate should be accepted
        """
        import random
        
        # Check if candidate is feasible
        if not candidate.is_feasible():
            return False
            
        candidate_score = candidate.objective()
        best_score = best.objective()
        
        print(f'New solution aggregate score: {candidate_score}, current best score: {best_score}')
        
        # Accept if better or with 5% random chance
        accept = candidate_score < best_score or random.random() < 0.05
        
        # Print in green if True, red if False
        color = '\033[92m' if accept else '\033[91m'
        print(f'{color}Acceptance return value: {accept}\033[0m')
        
        return accept


# --- Main ALNS Function ---
def run_alns_with_library(
    initial_assignment, container_size, container_weight, step2_settings_file,
    num_iterations, num_remove, time_limit, max_no_improve, seed=42, verbose=False):
    """
    Run ALNS using the official ALNS library.
    
    Args:
        initial_assignment: list of containers (output of step 1 or greedy fit)
        container_size: [L, W, H]
        container_weight: maximum weight per container
        step2_settings_file: path to step2 settings JSON
        num_iterations: maximum iterations
        num_remove: number of items to remove in destroy operator
        time_limit: time limit in seconds
        max_no_improve: max iterations without improvement
        seed: random seed
    
    Returns:
        best_solution: ContainerLoadingState
        result: ALNS result object with statistics
    """
    
    # Convert relative path to absolute path for step2_settings_file
    import os
    if not os.path.isabs(step2_settings_file):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        step2_settings_file = os.path.join(base_dir, step2_settings_file)
    print('***** Starting ALNS with official library ...')
    
    # Create initial state, passing the weight needed for repair.
    initial_state = ContainerLoadingState(
        initial_assignment, container_size, container_weight, step2_settings_file, verbose
    )
    print('***** Getting step 2 baseline ...')
    initial_score = initial_state.objective()
    print(f'Initial step 2 solution: aggregate_score={initial_score}, statuses={initial_state.statuses}')
    
    # Create ALNS instance
    alns = ALNS(np.random.default_rng(seed=seed))
    
    # Add destroy and repair operators (use factory to make destroy operator configurable)
    destroy_op = create_destroy_random_items(num_remove)
    alns.add_destroy_operator(destroy_op)
    alns.add_repair_operator(repair_cpsat)
    
    # Configure ALNS components with realistic scoring that rewards better outcomes
    # [new_global_best, better_than_current, accepted_but_not_better, rejected]
    select = RouletteWheel([10, 6, 3, 1], decay=0.8, num_destroy=1, num_repair=1)
    accept = CustomContainerAcceptance()  # Use custom acceptance criterion matching original logic
    
    stop = StoppingCriterionWithProgress(num_iterations, max_no_improve)
    
    print(f'Starting ALNS iterations with {num_iterations} max iterations, {max_no_improve} max no-improvement iterations, {time_limit}s time limit')
    
    # Run the ALNS algorithm
    result = alns.iterate(initial_state, select, accept, stop)
    
    # Get the best solution
    best_solution = result.best_state
    best_score = best_solution.objective()
    
    print(f'ALNS finished. Best aggregate_score={best_score}, statuses={best_solution.statuses}')
    
    # --- Visualization of best solution ---
    try:
        from visualization_utils import visualize_solution
        import matplotlib.pyplot as plt
        for vis_data in getattr(best_solution, 'visualization_data', []):
            if vis_data is not None:
                plt_obj = visualize_solution(
                    vis_data['elapsed_time'],
                    vis_data['container'],
                    vis_data['boxes'],
                    vis_data['perms_list'],
                    vis_data['placements'],
                    vis_data['n'],
                    vis_data['status_str'],
                    vis_data['container_id']
                )
                plt_obj.show(block=False)
    except Exception as e:
        print(f"Visualization failed: {e}")
    
    return best_solution, result


# --- Example main entry point ---


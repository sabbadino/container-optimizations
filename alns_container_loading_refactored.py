"""
ALNS framework for container loading using the official ALNS library.
Refactored from custom ALNS loop to use alns library.

Loop summary (iterate):
    1) select (RouletteWheel) a destroy + repair pair (only one pair registered).
    2) destroy: copy state, remove num_remove items, set _removed_items.
    3) repair: build Step-1 CP-SAT with fixed and free items, solve, rebuild assignment → new state.
    4) evaluate: candidate.objective() runs Phase-2 per container; compute aggregate_score.
    5) accept: CustomContainerAcceptance (feasible + better or 5% chance).
    6) stop: StoppingCriterionWithProgress (max iterations or max no-improve).
"""
import json
import time
import os
import sys
from collections import defaultdict

# ALNS library imports
from alns import ALNS
from alns.select import RouletteWheel

import numpy as np
import numpy.random as rnd

# Local modules
from container_loading_state import ContainerLoadingState
from alns_criteria import StoppingCriterionWithProgress
from alns_acceptance import CustomContainerAcceptance

# Step1 model utilities
from step1_model_builder import build_step1_model
from print_utils import dump_phase1_results


# --- ALNS Destroy Operator ---
def create_destroy_random_items(num_remove):
    """
        Factory for a destroy operator that removes up to `num_remove` items.

        Contract:
        - Input: current ContainerLoadingState (immutable by convention), rng
        - Output: new ContainerLoadingState deep copy with some boxes removed
        - Side-effects on returned state: sets `_removed_items` list and
            `_objective_computed=False` to force re-evaluation when needed.
    """
    def destroy_random_items(state, rng, **kwargs):
        """
        ALNS destroy operator: Randomly select items and unassign them from their containers.
        Returns a new partial assignment (deep copy with some boxes removed).
        """
        # Create a deep copy first (required by ALNS)
        destroyed_state = state.copy()

        # Flatten all boxes with their container index
        all_boxes = [
            (c_idx, box_idx)
            for c_idx, container in enumerate(destroyed_state.assignment)
            for box_idx in range(len(container['boxes']))
        ]

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

        try:
            print(f"Destroy removed {len(removed_items)} items across containers")
        except Exception:
            pass

        return destroyed_state

    return destroy_random_items


# --- ALNS Repair Operator ---
def create_repair_cpsat(max_time_in_seconds):
    """
        Factory for a repair operator that uses CP-SAT Step-1 to reassign removed items.

        Contract:
        - Input: destroyed ContainerLoadingState with `_removed_items`, rng
        - Build: combines removed (free) + currently placed (fixed) items; constructs
            fixed_assignments and group_to_items; allows opening extra containers.
        - Solve: Step-1 CP-SAT with a time limit (`max_time_in_seconds`).
        - Output: new ContainerLoadingState with a full, repaired assignment.
    """

    def repair_cpsat(state, rng, **kwargs):
        """
        ALNS repair operator: Use CP-SAT to optimally reassign removed items.
        Returns a new complete assignment.
        """
        # Get removed items from the destroyed state
        destroyed = state
        removed_items = getattr(destroyed, '_removed_items', [])
        if not removed_items:
            # Nothing to repair
            return destroyed

        # Prepare items: combine removed_items and fixed items
        all_items = []
        item_id_to_idx = {}

        # Add removed items first
        for i, item in enumerate(removed_items):
            all_items.append(
                {
                    'id': item['id'],
                    'size': item['size'],
                    'weight': item['weight'],
                    'group_id': item.get('group_id'),
                    'rotation': item.get('rotation'),
                }
            )
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
                    all_items.append(
                        {
                            'id': box['id'],
                            'size': box['size'],
                            'weight': box['weight'],
                            'group_id': box.get('group_id'),
                            'rotation': box.get('rotation'),
                        }
                    )
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
        model, x, y, group_in_containers, group_ids = build_step1_model(
            all_items,
            destroyed.container_size,
            container_weight,
            max_containers,
            group_to_items=group_to_items,
            fixed_assignments=fixed_assignments,
            group_penalty_lambda=group_penalty_lambda,
            dump_inputs=False,
        )

        from ortools.sat.python import cp_model

        solver = cp_model.CpSolver()
        # Set time limit for the repair operator (configurable via factory)
        print(f'repair_cp_sat max_time_in_seconds {max_time_in_seconds}')
        solver.parameters.max_time_in_seconds = max_time_in_seconds
        print(f'ALNS repair CP-SAT max_time_in_seconds: {max_time_in_seconds}')
        status = solver.Solve(model)
        dump_phase1_results(
            solver,
            status,
            x,
            y,
            group_in_containers,
            group_ids,
            group_to_items,
            all_items,
            destroyed.container_size,
            container_weight,
            verbose=False,
        )

        # Build new assignment structure - use sequential container IDs
        new_assignment = []
        used_cpsat_indices = [j for j in range(max_containers) if solver.Value(y[j])]

        for cpsat_idx in used_cpsat_indices:
            new_assignment.append(
                {'id': len(new_assignment) + 1, 'size': destroyed.container_size, 'boxes': []}
            )

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
            new_assignment, destroyed.container, destroyed.step2_settings_file, destroyed.verbose
        )
        return repaired_state

    return repair_cpsat


# --- Main ALNS Function ---
def run_alns_with_library(
    initial_assignment,
    container,
    step2_settings_file,
    num_iterations,
    num_remove,
    time_limit,
    max_no_improve,
    phase1_time_limit=60,
    seed=42,
    verbose=False,
):
    """
    Run ALNS using the official ALNS library.

    Args:
        initial_assignment: list of containers (output of step 1 or greedy fit)
        container: dict-like with keys 'size' ([L, W, H]) and 'weight' (max kg)
        step2_settings_file: path to step2 settings JSON
        num_iterations: maximum iterations
        num_remove: number of items to remove in destroy operator
        time_limit: time limit in seconds
        max_no_improve: max iterations without improvement
        phase1_time_limit: time limit for CP-SAT solver in repair operator
        seed: random seed

    Returns:
        best_solution: ContainerLoadingState
        result: ALNS result object with statistics
    """
    # Convert relative path to absolute path for step2_settings_file
    if not os.path.isabs(step2_settings_file):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        step2_settings_file = os.path.join(base_dir, step2_settings_file)
    print('***** Starting ALNS with official library ...')

    # Create initial state, passing the weight needed for repair.
    initial_state = ContainerLoadingState(
        initial_assignment, container, step2_settings_file, verbose
    )
    print('***** Getting step 2 baseline ...')
    initial_score = initial_state.objective()
    print(
        f'Initial step 2 solution: aggregate_score={initial_score}, statuses={initial_state.statuses}'
    )

    # --- ALNS Parameters & Search (iterate-style API) ---
    alns = ALNS(np.random.default_rng(seed=seed))

    # Add destroy and repair operators
    alns.add_destroy_operator(create_destroy_random_items(num_remove))
    alns.add_repair_operator(create_repair_cpsat(phase1_time_limit))

    # Selection, acceptance, and stopping criteria

    # ABOUT selection:
    # With one destroy and one repair operator, RouletteWheel selection is trivial:
    # it always picks the only pair. The reward vector [1,0,0,0] is conventional
    # (update weights only on new global best). Decay controls smoothing, but
    # with a single pair it has no effect on which operators are chosen.


    select = RouletteWheel([1, 0, 0, 0], decay=1.0, num_destroy=1, num_repair=1)
    accept = CustomContainerAcceptance()
    stop = StoppingCriterionWithProgress(num_iterations, max_no_improve)

    print(
        f'Starting ALNS iterations with {num_iterations} max iterations, {max_no_improve} max no-improvement iterations, {time_limit}s time limit'
    )
    # Note: time_limit can also be enforced via a separate stopping criterion if needed

    result = alns.iterate(initial_state, select, accept, stop)
    best_solution = result.best_state
    best_score = best_solution.objective()
    statuses = getattr(best_solution, 'statuses', None)
    if statuses is not None:
        print(f'ALNS finished. Best aggregate_score={best_score}, statuses={statuses}')
    else:
        print(f'ALNS finished. Best aggregate_score={best_score}')

    return best_solution, result


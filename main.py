import json
import sys
import os
import time
from collections import defaultdict
from ortools.sat.python import cp_model

from step1_model_builder import build_step1_model
from print_utils import dump_phase1_results
from alns_loop import run_alns_with_library
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from container_loading_state import ContainerLoadingState
from step2_box_placement_in_container import run_phase_2
from visualization_utils import visualize_solution

def main():
    """
    Main entry point for the container loading optimization process.
    Orchestrates the entire workflow from input to output.
    """
    import argparse
    parser = argparse.ArgumentParser(description="3D Container Loading Optimization using a multi-phase approach.")
    parser.add_argument('--input', type=str, required=True, help="Path to the input JSON file.")
    parser.add_argument('--output', type=str, required=True, help="Path to the output JSON file for the final solution.")
    parser.add_argument('--no-alns', action='store_true', help="Skip the ALNS refinement step and go straight from Phase 1 to Phase 2.")
    parser.add_argument('--verbose', action='store_true', help="Enable detailed logging throughout the process.")
    args = parser.parse_args()

    # Utility: map orientation index -> axis order string
    def _orientation_desc(o):
        try:
            mapping = {
                0: "L,W,H",
                1: "L,H,W",
                2: "W,L,H",
                3: "W,H,L",
                4: "H,L,W",
                5: "H,W,L",
            }
            return mapping.get(int(o)) if o is not None else None
        except Exception:
            return None

    # --- 1. Load Input Data ---
    print(f"--- Loading Input Data from {args.input} ---")
    if not os.path.exists(args.input):
        print(f"Error: Input file not found at {args.input}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(args.input, 'r') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Basic validation
    if 'container' not in data or 'items' not in data:
        print("Error: Input JSON must contain 'container' and 'items' keys.", file=sys.stderr)
        sys.exit(1)

    container_size = data['container']['size']
    container_weight = data['container']['weight']
    items = data['items']
    
    # Assign unique IDs if not present
    for i, item in enumerate(items):
        item['id'] = item.get('id', i + 1)

    print(f"Successfully loaded {len(items)} items and container definition.")

    # --- 2. Phase 1: Initial Box Assignment ---
    print("\n--- Phase 1: Running Initial Box Assignment ---")
    
    group_to_items = defaultdict(list)
    for idx, item in enumerate(items):
        gid = item.get('group_id')
        if gid is not None:
            group_to_items[gid].append(idx)

    max_containers = len(items)
    group_penalty_lambda = 1.0 # This could be made configurable

    model, x, y, group_in_containers, group_ids = build_step1_model(
        items, container_size, container_weight, max_containers,
        group_to_items=group_to_items,
        group_penalty_lambda=group_penalty_lambda,
        dump_inputs=args.verbose
    )

    solver = cp_model.CpSolver()
    #solver.parameters.log_search_progress = args.verbose
    phase1_time_limit = data.get('solver_phase1_max_time_in_seconds', 60)
    print(f'Running Phase 1 baseline with time limit {phase1_time_limit} seconds')
    solver.parameters.max_time_in_seconds = phase1_time_limit
    status = solver.Solve(model)

    dump_phase1_results(
        solver, status, x, y, group_in_containers, group_ids, group_to_items,
        items, container_size, container_weight, verbose=args.verbose
    )

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("Error: Phase 1 failed to find a feasible assignment. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Extract the initial assignment
    initial_assignment = []
    used_container_indices = [j for j in range(max_containers) if solver.Value(y[j])]
    container_rebase = {old_idx: new_idx + 1 for new_idx, old_idx in enumerate(used_container_indices)}
    for old_j in used_container_indices:
        new_j = container_rebase[old_j]
        items_in_container = [i for i in range(len(items)) if solver.Value(x[i, old_j])]
        container_entry = {
            'id': new_j,
            'size': container_size,
            'boxes': [items[i] for i in items_in_container]
        }
        initial_assignment.append(container_entry)

    best_assignment = initial_assignment

    # --- 3. ALNS Refinement (Optional) ---
    if not args.no_alns:
        print("\n--- ALNS Refinement Step ---")
        step2_settings_file = data.get('step2_settings_file')
        if not step2_settings_file:
            print("Warning: 'step2_settings_file' not found in input. Skipping ALNS.", file=sys.stderr)
        else:
            alns_params = data.get('alns_params', {})
            num_iterations = alns_params.get('num_iterations', 100)
            num_can_be_moved_percentage = alns_params.get('num_can_be_moved_percentage', 10)
            time_limit = alns_params.get('time_limit', 60)
            max_no_improve = alns_params.get('max_no_improve', 20)
            
            num_remove = max(1, int(len(items) * num_can_be_moved_percentage / 100))

            # Run ALNS; it evaluates step 2 internally and stores placements per container
            best_state: "ContainerLoadingState" = run_alns_with_library(
                initial_assignment,
                {"size": container_size, "weight": container_weight},
                step2_settings_file,
                num_iterations, num_remove, time_limit, max_no_improve, phase1_time_limit, verbose=args.verbose
            )
            # Extract best assignment and attach placements/status so orientations are present in the output
            best_assignment = best_state.assignment
            vis_list = getattr(best_state, 'visualization_data', []) or []
            for c_idx, container in enumerate(best_assignment):
                if c_idx < len(vis_list) and vis_list[c_idx] is not None:
                    container['placements'] = vis_list[c_idx].get('placements', [])
                    container['status'] = vis_list[c_idx].get('status_str')

            # Visualize ALNS best solution per container using stored phase-2 info
            try:
                import matplotlib.pyplot as plt  # ensure matplotlib is available
                for c_idx, container in enumerate(best_assignment):
                    if c_idx < len(vis_list) and vis_list[c_idx] is not None and container.get('boxes'):
                        step2_viz = vis_list[c_idx]
                        plt_obj = visualize_solution(
                            step2_viz.get('elapsed_time'),
                            {"id": container.get('id'), "size": container_size},
                            container.get('boxes', []),
                            step2_viz.get('placements', []),
                            step2_viz.get('status_str'),
                        )
                        plt_obj.show(block=False)
            except ImportError:
                print("matplotlib not available; skipping ALNS visualization.")
            except Exception as e:
                print(f"Visualization error: {e}")
           
    else:
        print("\n--- Skipping ALNS Refinement Step ---")


    # --- 4. Handle No-ALNS Case ---
    # If ALNS was skipped, we still need to run Phase 2 on the initial assignment.
    if args.no_alns:
        print("\n--- Phase 2: Running 3D Placement on Initial Assignment ---")
        step2_settings_file = data.get('step2_settings_file')
        if not step2_settings_file:
            print("Error: 'step2_settings_file' not found. Cannot run Phase 2.", file=sys.stderr)
            sys.exit(1)

        for container_to_pack in best_assignment:
            container_id = container_to_pack['id']
            boxes_in_container = container_to_pack['boxes']
            
            if not boxes_in_container:
                print(f"Container {container_id} is empty, skipping placement.")
                continue

            print(f"--- Packing Container ID: {container_id} ---")
            status_str, step2_results = run_phase_2(
                {"id": container_id, "size": container_size}, boxes_in_container,
                step2_settings_file, verbose=args.verbose
            )
            placements = step2_results.get('placements', []) if isinstance(step2_results, dict) else []
            container_to_pack['placements'] = placements
            container_to_pack['status'] = status_str
            # Visualize Phase 2 result for this container (show container id in title)
            try:
                import matplotlib.pyplot as plt  # gate visualization to avoid visualize_solution exiting on ImportError
                plt_obj = visualize_solution(
                    step2_results.get('elapsed_time'),
                    {"id": container_id, "size": container_size},
                    boxes_in_container,
                    placements,
                    status_str,
                )
                plt_obj.show(block=False)
            except ImportError:
                print("matplotlib not available; skipping Phase 2 visualization.")
            except Exception as e:
                print(f"Visualization error: {e}")
           
        # Add rotation description to each placement before saving output
        for container in best_assignment:
            placements = container.get('placements', [])
            for placement in placements:
                rotation_idx = placement.get('rotation_idx')
                placement['rotation_desc'] = _orientation_desc(rotation_idx)

    # --- 5. Save Output ---
    print(f"\n--- Saving Final Solution to {args.output} ---")
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

  
    # Remove 'boxes' from each container before saving output
    output_assignment = []
    for container in best_assignment:
        container_copy = dict(container)
        container_copy.pop('boxes', None)
        output_assignment.append(container_copy)
    with open(args.output, 'w') as f:
        json.dump(output_assignment, f, indent=2)

    print("Process completed.")
    
    # Check final solution feasibility
    if not all(c.get('status') in ('OPTIMAL', 'FEASIBLE') for c in best_assignment if c.get('boxes')):
        print("Warning: One or more containers could not be feasibly packed.", file=sys.stderr)
    
    print("Press Enter to close visualization windows and exit.")
    input()


if __name__ == "__main__":
    main()

"""
ALNS framework for container loading: solution evaluation and acceptance criteria template
"""
import copy
import random
from step2_container_box_placement_in_container import run_phase_2 
from print_utils import dump_phase1_results

class ContainerLoadingSolution:
    def __init__(self, assignment, container_size, step2_settings_file):
        """
        assignment: list of containers, each is a dict with 'id', 'boxes' (list of box dicts)
        container_size: [L, W, H]
        step2_settings_file: path to settings JSON for step 2
        """
        self.assignment = copy.deepcopy(assignment)
        self.container_size = container_size
        self.step2_settings_file = step2_settings_file
        self.statuses = []  # 'OPTIMAL', 'FEASIBLE', 'UNFEASIBLE' per container
        self.soft_scores = []  # soft objective scores per container (to be filled)
        self.aggregate_score = None
        self.visualization_data = []  # store visualization info per container

    def evaluate(self,verbose=False):
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
            status, placements, vis_data = run_phase_2(container['id'], self.container_size, boxes, self.step2_settings_file,verbose,False)
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
        penalty = 1000 * self.statuses.count('UNFEASIBLE')
        optimal_bonus = 2 * self.statuses.count('OPTIMAL')
        feasible_bonus = 1 * self.statuses.count('FEASIBLE')
        self.aggregate_score = penalty + balance_penalty - optimal_bonus - feasible_bonus
        
        # Print in blue color using ANSI escape code
        print('')
        print(f'\033[94mAggregate score: {self.aggregate_score} (penalty={penalty} + balance_penalty={balance_penalty:.3f} - optimal_bonus={optimal_bonus} - feasible_bonus={feasible_bonus})\033[0m')
        print(f'\033[94mUtilization stats: mean={mean_utilization:.1f}%, variance={variance:.1f}, percentages={[f"{p:.1f}%" for p in utilization_percentages]}\033[0m')
        return self.aggregate_score

    def is_feasible(self):
        return 'UNFEASIBLE' not in self.statuses

 
def acceptance_criteria(new_solution, current_best_score):
    """
    Accept if all containers are at least FEASIBLE and aggregate score improves.
    """
    if not new_solution.is_feasible():
        return False
    print(f'New solution aggregate score: {new_solution.aggregate_score}, current best score: {current_best_score}')
    return_value =  new_solution.aggregate_score < current_best_score or random.random() < 0.05
    # Print in green if True, red if False
    color = '\033[92m' if return_value else '\033[91m'
    print(f'{color}Acceptance return value: {return_value}\033[0m')
    return return_value

# Example usage:
# solution = ContainerLoadingSolution(assignment, container_size, step2_settings_file)
# score = solution.evaluate()
# if acceptance_criteria(solution, best_score):
#     ...

# You can now build ALNS destroy/repair operators and the main loop around this template.

# --- ALNS Destroy and Repair Operator Templates ---

def destroy_random_items(solution, num_remove=5):
    """
    Randomly select num_remove items and unassign them from their containers.
    Returns a new partial assignment (list of containers with boxes, some boxes removed).
    """
    import numpy as np
    
    # Flatten all boxes with their container index
    all_boxes = [(c_idx, box_idx) for c_idx, container in enumerate(solution.assignment)
                 for box_idx in range(len(container['boxes']))]
    if len(all_boxes) == 0:
        return copy.deepcopy(solution.assignment), []
    
    remove_indices = np.random.choice(len(all_boxes), min(num_remove, len(all_boxes)), replace=False)
    removed_items = []
    new_assignment = copy.deepcopy(solution.assignment)
    
    # Collect removed items first (before marking for removal)
    for idx in remove_indices:
        c_idx, box_idx = all_boxes[idx]
        removed_items.append(new_assignment[c_idx]['boxes'][box_idx])
    
    # Now mark for removal
    for idx in remove_indices:
        c_idx, box_idx = all_boxes[idx]
        new_assignment[c_idx]['boxes'][box_idx] = None  # Mark for removal
    
    # Remove None entries
    for container in new_assignment:
        container['boxes'] = [box for box in container['boxes'] if box is not None]
    
    return new_assignment, removed_items


# Example ALNS iteration


# --- CP-SAT-based Repair Operator Template ---
def repair_cpsat(partial_assignment, removed_items, container_size, container_weight):
    """
    Use CP-SAT to optimally reassign removed items, keeping non-removed items fixed.
    Returns a new complete assignment.
    """
    # Use shared assignment model for consistency
    from assignment_model import build_step1_assignment_model
    import copy
    
    # Validate no duplicate item IDs
    all_item_ids = []
    for item in removed_items:
        all_item_ids.append(item['id'])
    for container in partial_assignment:
        for box in container['boxes']:
            all_item_ids.append(box['id'])
    
    if len(all_item_ids) != len(set(all_item_ids)):
        raise ValueError(f"Duplicate item IDs detected in repair_cpsat: {[id for id in all_item_ids if all_item_ids.count(id) > 1]}")
    
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
    
    # Build container mapping: original container id -> zero-based index for CP-SAT
    container_id_to_cpsat_idx = {}
    cpsat_idx_to_container_id = {}
    for cpsat_idx, container in enumerate(partial_assignment):
        container_id_to_cpsat_idx[container['id']] = cpsat_idx
        cpsat_idx_to_container_id[cpsat_idx] = container['id']
    
    # Add fixed items (from partial_assignment)
    fixed_assignments = {}
    fixed_item_ids = set()
    for container in partial_assignment:
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
    from collections import defaultdict
    group_to_items = defaultdict(list)
    for idx, item in enumerate(all_items):
        gid = item.get('group_id')
        if gid is not None:
            group_to_items[gid].append(idx)
    # Container count: allow new containers for removed items
    max_containers = len(partial_assignment) + len(removed_items)
    # Build model
    group_penalty_lambda = 1
    model, x, y, group_in_containers, group_ids = build_step1_assignment_model(
        all_items,
        container_size,
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
    # Dump results for repair
    dump_phase1_results(
        solver, status, x, y, group_in_containers, group_ids, group_to_items,
        all_items, container_size, container_weight, verbose=False)
    # Build new assignment structure
    # Start with empty containers - use sequential container IDs
    new_assignment = []
    used_cpsat_indices = [j for j in range(max_containers) if solver.Value(y[j])]
    
    print(f'DEBUG: used CP-SAT container indices: {used_cpsat_indices}')
    
    for cpsat_idx in used_cpsat_indices:
        new_assignment.append({'id': len(new_assignment) + 1, 'size': container_size, 'boxes': []})
    
    # Assign items to containers using correct mapping
    for i in range(len(all_items)):
        for cpsat_idx in used_cpsat_indices:
            if solver.Value(x[i, cpsat_idx]):
                # Find which new_assignment container corresponds to this cpsat_idx
                new_container_idx = used_cpsat_indices.index(cpsat_idx)
                new_assignment[new_container_idx]['boxes'].append(all_items[i])
                break
    
    return new_assignment


# --- Main ALNS Loop ---
def run_alns(
    initial_assignment, container_size, container_weight, step2_settings_file,
    num_iterations, num_remove,
    time_limit, max_no_improve):
    """
    Main ALNS loop: iteratively destroy/repair, track best solution, log progress.
    initial_assignment: list of containers (output of step 1 or greedy fit)
    time_limit: seconds
    max_no_improve: stop after N iterations with no improvement
    """
    import time
    print('***** Starting ALNS loop ...')
    print('***** Getting step 2 baseline ...')
    best_solution = ContainerLoadingSolution(initial_assignment, container_size, step2_settings_file)
    best_score = best_solution.evaluate(False)
    print(f'Initial step 2 solution: aggregate_score={best_score}, statuses={best_solution.statuses}')
    current_solution = copy.deepcopy(best_solution)
    history = []
    no_improve_count = 0
    start_time = time.time()
    for it in range(num_iterations):
        t0 = time.time()
        # Early exit guard: if only one container and status is OPTIMAL, break
        if len(best_solution.assignment) == 1 and best_solution.statuses[0] == 'OPTIMAL':
            print(f'Early exit: single container is OPTIMAL at iteration {it+1}.')
            break
        # Time limit check
        elapsed = time.time() - start_time
        # Print in orange color using ANSI escape code (color 208)
        print(f'\033[38;5;208mIteration {it+1}/{num_iterations}, elapsed time: {elapsed:.2f}s, no_improve_count: {no_improve_count}\033[0m')
        if elapsed > time_limit:
            print(f'Early exit: time limit {time_limit}s reached at iteration {it+1}.')
            break
        # No improvement check
        if no_improve_count >= max_no_improve:
            print(f'Early exit: no improvement for {max_no_improve} iterations at iteration {it+1}.')
            break
        # Destroy/repair
        partial_assignment, removed_items = destroy_random_items(current_solution, num_remove)
        new_assignment = repair_cpsat(partial_assignment, removed_items, container_size, container_weight)
        new_solution = ContainerLoadingSolution(new_assignment, container_size, step2_settings_file)
        score = new_solution.evaluate(False)
        accepted = acceptance_criteria(new_solution, best_score)
        # Logging
        print(f'Iter {it+1:03d}: score={score:.2f}, statuses={new_solution.statuses}, accepted={accepted}, time={time.time()-t0:.2f}s')
        history.append({'iter': it+1, 'score': score, 'statuses': new_solution.statuses, 'accepted': accepted})
        if accepted and score < best_score:
            best_solution = copy.deepcopy(new_solution)
            best_score = score
            print(f'\033[92m  New best solution found!\033[0m')
            no_improve_count = 0
        else:
            no_improve_count += 1
        current_solution = copy.deepcopy(new_solution) if accepted else current_solution
        print('***** END OF ONE ALNS LOOP *****')
    print(f'ALNS finished. Best aggregate_score={best_score}, statuses={best_solution.statuses}')

    # --- Visualization of best solution ---
    try:
        from visualization_utils import visualize_solution
        for vis_data in getattr(best_solution, 'visualization_data', []):
            if vis_data is not None:
                plt = visualize_solution(
                    vis_data['elapsed_time'],
                    vis_data['container'],
                    vis_data['boxes'],
                    vis_data['perms_list'],
                    vis_data['placements'],
                    vis_data['n'],
                    vis_data['status_str'],
                    vis_data['container_id']
                )
                plt.show(block=False)
    except Exception as e:
        print(f"Visualization failed: {e}")

    return best_solution, history

# --- Example main entry point ---
if __name__ == "__main__":
    import sys, json, time, os
    
    if len(sys.argv) < 2:
        print('Usage: python alns_container_loading.py <input_json_file>')
        sys.exit(1)
    
    input_filename = sys.argv[1]
    
    # Validate input file exists
    if not os.path.exists(input_filename):
        print(f'Error: Input file "{input_filename}" does not exist.')
        sys.exit(1)
    
    # Validate input file is readable
    if not os.access(input_filename, os.R_OK):
        print(f'Error: Input file "{input_filename}" is not readable.')
        sys.exit(1)
    
    print(f'Reading input from {input_filename}')
    
    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON in input file "{input_filename}": {e}')
        sys.exit(1)
    except IOError as e:
        print(f'Error: Failed to read input file "{input_filename}": {e}')
        sys.exit(1)
    
    # Validate required data structure
    try:
        # Validate container data
        if 'container' not in data:
            print('Error: Missing "container" key in input JSON.')
            sys.exit(1)
        
        container_size = data['container']['size']
        container_weight = data['container']['weight']
        
        # Validate container dimensions
        if not isinstance(container_size, list) or len(container_size) != 3:
            print('Error: Container size must be a list of 3 dimensions [L, W, H].')
            sys.exit(1)
        
        if not all(isinstance(dim, (int, float)) and dim > 0 for dim in container_size):
            print('Error: Container dimensions must be positive numbers.')
            sys.exit(1)
            
        if not isinstance(container_weight, (int, float)) or container_weight <= 0:
            print('Error: Container weight must be a positive number.')
            sys.exit(1)
        
        # Validate items data
        if 'items' not in data:
            print('Error: Missing "items" key in input JSON.')
            sys.exit(1)
            
        if not isinstance(data['items'], list) or len(data['items']) == 0:
            print('Error: Items must be a non-empty list.')
            sys.exit(1)
        
        # Validate each item
        for i, item in enumerate(data['items']):
            if not isinstance(item, dict):
                print(f'Error: Item {i} must be a dictionary.')
                sys.exit(1)
            
            required_keys = ['size', 'weight']
            for key in required_keys:
                if key not in item:
                    print(f'Error: Item {i} missing required key "{key}".')
                    sys.exit(1)
            
            if not isinstance(item['size'], list) or len(item['size']) != 3:
                print(f'Error: Item {i} size must be a list of 3 dimensions [L, W, H].')
                sys.exit(1)
                
            if not all(isinstance(dim, (int, float)) and dim > 0 for dim in item['size']):
                print(f'Error: Item {i} dimensions must be positive numbers.')
                sys.exit(1)
                
            if not isinstance(item['weight'], (int, float)) or item['weight'] <= 0:
                print(f'Error: Item {i} weight must be a positive number.')
                sys.exit(1)
    
    except KeyError as e:
        print(f'Error: Missing required key in input JSON: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error: Invalid data structure in input JSON: {e}')
        sys.exit(1)
    
    # Validate step2_settings_file
    step2_settings_file = data.get('step2_settings_file', None)
    if step2_settings_file is None:
        print('Error: step2_settings_file must be specified in the input JSON file.')
        sys.exit(1)
    
    if not os.path.exists(step2_settings_file):
        print(f'Error: Step2 settings file "{step2_settings_file}" does not exist.')
        sys.exit(1)
    
    if not os.access(step2_settings_file, os.R_OK):
        print(f'Error: Step2 settings file "{step2_settings_file}" is not readable.')
        sys.exit(1)
    
    # Validate step2 settings file is valid JSON
    try:
        with open(step2_settings_file, 'r') as f:
            step2_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON in step2 settings file "{step2_settings_file}": {e}')
        sys.exit(1)
    except IOError as e:
        print(f'Error: Failed to read step2 settings file "{step2_settings_file}": {e}')
        sys.exit(1)
    items = []
    item_ids = [item.get('id', i+1) for i, item in enumerate(data['items'])]
    
    # Validate no duplicate item IDs
    if len(item_ids) != len(set(item_ids)):
        duplicate_ids = [id for id in item_ids if item_ids.count(id) > 1]
        print(f'Error: Duplicate item IDs detected: {duplicate_ids}')
        print('Each item must have a unique ID. Please fix the input data.')
        sys.exit(1)
    item_group_ids = [item.get('group_id') for item in data['items']]
    for i in range(len(data['items'])):
        item = {
            'id': item_ids[i],
            'size': data['items'][i]['size'],
            'weight': data['items'][i]['weight'],
            'group_id': item_group_ids[i],
            'rotation': data['items'][i].get('rotation')
        }
        items.append(item)
    from collections import defaultdict
    group_to_items = defaultdict(list)
    for idx, gid in enumerate(item_group_ids):
        if gid is not None:
            group_to_items[gid].append(idx)
    max_containers = len(items)
    group_penalty_lambda = 1
    from assignment_model import build_step1_assignment_model
    model, x, y, group_in_containers, group_ids = build_step1_assignment_model(
        items,
        container_size,
        container_weight,
        max_containers,
        group_to_items=group_to_items,
        fixed_assignments=None,
        group_penalty_lambda=group_penalty_lambda,dump_inputs=True
    )
    from ortools.sat.python import cp_model
    print (f'Running phase 1 baseline.')
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Dump results for initial assignment
    dump_phase1_results(
        solver, status, x, y, group_in_containers, group_ids, group_to_items,
        items, container_size, container_weight, verbose=False)

    # Extract assignment in same format as step1_box_partition_in_containers.py
    initial_assignment = []
    used_container_indices = [j for j in range(max_containers) if solver.Value(y[j])]
    container_rebase = {old_idx: new_idx+1 for new_idx, old_idx in enumerate(used_container_indices)}
    for old_j in used_container_indices:
        new_j = container_rebase[old_j]
        items_in_container = [i for i in range(len(items)) if solver.Value(x[i, old_j])]
        container_entry = {
            'id': new_j,
            'size': container_size,
            'boxes': [items[i] for i in items_in_container]
        }
        initial_assignment.append(container_entry)
    # Validate ALNS parameters
    alns_params = data.get('alns_params', {})
    if not isinstance(alns_params, dict):
        print('Error: alns_params must be a dictionary.')
        sys.exit(1)
    
    required_alns_keys = ['num_iterations', 'num_can_be_moved_percentage', 'time_limit', 'max_no_improve']
    for key in required_alns_keys:
        if key not in alns_params:
            print(f'Error: Missing required ALNS parameter "{key}".')
            sys.exit(1)
    
    try:
        num_iterations = alns_params['num_iterations']
        num_can_be_moved_percentage = alns_params['num_can_be_moved_percentage']
        time_limit = alns_params['time_limit']
        max_no_improve = alns_params['max_no_improve']
        
        # Calculate num_remove based on total items and percentage
        total_items = len(items)
        num_remove = max(1, int(total_items * num_can_be_moved_percentage / 100))
        print(f'Total items: {total_items}, num_can_be_moved_percentage: {num_can_be_moved_percentage}%, calculated num_remove: {num_remove}')
        
        # Validate ALNS parameter values
        if not isinstance(num_iterations, int) or num_iterations <= 0:
            print('Error: num_iterations must be a positive integer.')
            sys.exit(1)
            
        if not isinstance(num_can_be_moved_percentage, (int, float)) or num_can_be_moved_percentage <= 0 or num_can_be_moved_percentage > 100:
            print('Error: num_can_be_moved_percentage must be a number between 0 and 100.')
            sys.exit(1)
            
        if not isinstance(time_limit, (int, float)) or time_limit <= 0:
            print('Error: time_limit must be a positive number.')
            sys.exit(1)
            
        if not isinstance(max_no_improve, int) or max_no_improve <= 0:
            print('Error: max_no_improve must be a positive integer.')
            sys.exit(1)
            
    except Exception as e:
        print(f'Error: Invalid ALNS parameter values: {e}')
        sys.exit(1)
    
    # Ensure outputs directory exists
    if not os.path.exists('outputs'):
        try:
            os.makedirs('outputs')
            print('Created outputs directory.')
        except Exception as e:
            print(f'Error: Failed to create outputs directory: {e}')
            sys.exit(1)
    # Run ALNS
    print('calling ALNS loop...')
    best_solution, history = run_alns(
        initial_assignment, container_size, container_weight, step2_settings_file,
        num_iterations=num_iterations, num_remove=num_remove,
        time_limit=time_limit, max_no_improve=max_no_improve)
    # Optionally, write best solution to file
    now = time.strftime('%Y-%m-%d-%H-%M-%S')
    out_json = f'outputs/alns_best_solution_{now}.json'
    with open(out_json, 'w', encoding='utf-8') as fout:
        json.dump({'assignment': best_solution.assignment, 'statuses': best_solution.statuses, 'aggregate_score': best_solution.aggregate_score}, fout, indent=2)
    print(f'Best solution written to {out_json}')
    input("Press any key to exit (it will close container visualization windows)")

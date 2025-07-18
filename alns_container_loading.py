# --- Utility: Dump Phase 1 Model Results ---
def dump_phase1_results(
    solver, status, x, y, group_in_containers, group_ids, group_to_items,
    items, container_size, container_weight, input_md=None, filename_prefix='container_bin_packing_result', write_md=True):
    """
    Print and write markdown summary of phase 1 assignment model results.
    """
    import sys, datetime, os
    num_items = len(items)
    item_ids = [item.get('id', i+1) for i, item in enumerate(items)]
    item_weights = [item['weight'] for item in items]
    item_volumes = [item['size'][0] * item['size'][1] * item['size'][2] for item in items]
    item_group_ids = [item.get('group_id') for item in items]
    container_volume = container_size[0] * container_size[1] * container_size[2]
    if container_volume <= 0:
        raise ValueError(f"Invalid container volume: {container_volume}. Container dimensions: {container_size}")
    if container_weight <= 0:
        raise ValueError(f"Invalid container weight: {container_weight}")
    max_containers = len(y)
    from ortools.sat.python import cp_model
    status_dict = {
        cp_model.OPTIMAL: 'OPTIMAL',
        cp_model.FEASIBLE: 'FEASIBLE',
        cp_model.INFEASIBLE: 'INFEASIBLE',
        cp_model.MODEL_INVALID: 'MODEL_INVALID',
        cp_model.UNKNOWN: 'UNKNOWN',
    }
    output_md = []
    output_md.append('## OUTPUTS')
    output_md.append(f'Step 1 Solver status: {status_dict.get(status, status)}')
    print('')
    print(f'******** PHASE 1 OUTPUT ********')
    print(f'Step 1 Solver status: {status_dict.get(status, status)}')
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        min_containers = int(sum(solver.Value(y[j]) for j in range(max_containers)))
        group_splits = {g: solver.Value(group_in_containers[g]) - 1 for g in group_ids}
        total_group_splits = sum(group_splits.values())
        print(f'Minimum containers used: {min_containers}')
        print(f'Total group splits (penalized): {total_group_splits}')
        output_md.append(f'- Minimum containers used: {min_containers}')
        output_md.append(f'- Total group splits (penalized): {total_group_splits}')
        output_md.append('')
        used_container_indices = [j for j in range(max_containers) if solver.Value(y[j])]
        container_rebase = {old_idx: new_idx+1 for new_idx, old_idx in enumerate(used_container_indices)}
        for old_j in used_container_indices:
            new_j = container_rebase[old_j]
            items_in_container = [i for i in range(num_items) if solver.Value(x[i, old_j])]
            total_weight = sum(item_weights[i] for i in items_in_container)
            total_volume = sum(item_volumes[i] for i in items_in_container)
            pct_weight = 100 * total_weight / container_weight if container_weight > 0 else 0
            pct_volume = 100 * total_volume / container_volume if container_volume > 0 else 0
            print('')
            print(f'### Container {new_j}')
            print('| Item id | Weight | Volume | Group id |')
            
            output_md.append(f'### Container {new_j}')
            output_md.append('| Item id | Weight | Volume | Group id |')
            output_md.append('|---------|--------|--------|----------|')
            for i in items_in_container:
                output_md.append(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_group_ids[i]} |')
                print(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_group_ids[i]} |')
            output_md.append(f'**Total for container {new_j}: weight = {total_weight} ({pct_weight:.1f}% of max), volume = {total_volume} ({pct_volume:.1f}% of max)**\n')
            print(f'**Total for container {new_j}: weight = {total_weight} ({pct_weight:.1f}% of max), volume = {total_volume} ({pct_volume:.1f}% of max)**')
        if group_ids:
            print('')
            print('### Group Splits')
            output_md.append('### Group Splits')
            print('| Group id | Containers used | Splits (penalized) | Container numbers |')
            output_md.append('| Group id | Containers used | Splits (penalized) | Container numbers |')
            print('|----------|----------------|--------------------|-------------------|')
            output_md.append('|----------|----------------|--------------------|-------------------|')
            for g in group_ids:
                containers_for_group = []
                for old_j in used_container_indices:
                    if any(solver.Value(x[i, old_j]) for i in group_to_items[g]):
                        containers_for_group.append(str(container_rebase[old_j]))
                containers_str = ', '.join(containers_for_group)
                output_md.append(f'| {g} | {solver.Value(group_in_containers[g])} | {group_splits[g]} | {containers_str} |')
                print(f'| {g} | {solver.Value(group_in_containers[g])} | {group_splits[g]} | {containers_str} |')
            output_md.append('')
            print('')
    else:
        print('No solution found.')
        output_md.append('No solution found.')
    if write_md:
        now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        md_filename = f'outputs/{filename_prefix}_{now}.md'
        if input_md is not None:
            with open(md_filename, 'w', encoding='utf-8') as f:
                f.write('# Container Bin Packing Result\n\n')
                f.write('\n'.join(input_md))
                f.write('\n---\n')
                f.write('\n'.join(output_md))
        else:
            with open(md_filename, 'w', encoding='utf-8') as f:
                f.write('# Container Bin Packing Result\n\n')
                f.write('\n'.join(output_md))
        if sys.platform.startswith('win'):
            os.startfile(os.path.abspath(md_filename))
    print(f'********************************')

"""
ALNS framework for container loading: solution evaluation and acceptance criteria template
"""
import copy
import random
from step2_container_box_placement_in_container import run_phase_2 

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

    def evaluate(self,verbose=True):
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
            # Phase 1 soft score: 1 - volume utilization
            total_box_volume = sum(box['size'][0] * box['size'][1] * box['size'][2] for box in boxes)
            volume_utilization = total_box_volume / container_volume if container_volume > 0 else 0
            score = 1 - volume_utilization  # lower is better
            self.soft_scores.append(score)
            print(f'Container {container["id"]}: status={status}, volume_utilization={volume_utilization:.2f}, soft_score={score:.2f}, n_boxes={len(boxes)}')
        # Aggregate score: penalize UNFEASIBLE, subtract soft_scores so lower is better
        penalty = 1000 * self.statuses.count('UNFEASIBLE')
        optimal_bonus = 2 * self.statuses.count('OPTIMAL')
        feasible_bonus = 1 * self.statuses.count('FEASIBLE')
        self.aggregate_score = penalty - optimal_bonus - feasible_bonus - sum(self.soft_scores)
        # Print in blue color using ANSI escape code
        print('')
        print(f'\033[94mAggregate score: {self.aggregate_score} (equal to penalty={penalty} - optimal_bonus={optimal_bonus} - feasible_bonus={feasible_bonus} - soft_scores={sum(self.soft_scores)})\033[0m')
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
    for idx in remove_indices:
        c_idx, box_idx = all_boxes[idx]
        removed_items.append(new_assignment[c_idx]['boxes'][box_idx])
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
            fixed_assignments[box['id']] = container['id'] - 1  # zero-based container idx
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
        all_items, container_size, container_weight, input_md=None, filename_prefix='alns_repair_result', write_md=False )
    # Build new assignment structure
    # Start with empty containers
    new_assignment = []
    for j in range(max_containers):
        if solver.Value(y[j]):
            new_assignment.append({'id': j+1, 'size': container_size, 'boxes': []})
    # Assign items to containers
    for i in range(len(all_items)):
        for idx, container in enumerate(new_assignment):
            j = container['id'] - 1
            if solver.Value(x[i, j]):
                container['boxes'].append(all_items[i])
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
    best_score = best_solution.evaluate(True)
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
    import sys, json, time
    if len(sys.argv) < 2:
        print('Usage: python alns_container_loading.py <input_json_file>')
        sys.exit(1)
    input_filename = sys.argv[1]
    print (f'Reading input from {input_filename}')
    with open(input_filename, 'r') as f:
        data = json.load(f)
    container_size = data['container']['size']
    container_weight = data['container']['weight']
    step2_settings_file = data.get('step2_settings_file', None)
    if step2_settings_file is None:
        print('Error: step2_settings_file must be specified in the input JSON file.')
        sys.exit(1)
    items = []
    item_ids = [item.get('id', i+1) for i, item in enumerate(data['items'])]
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
    # Prepare input markdown for reporting
    input_md = []
    input_md.append('## INPUTS')
    input_md.append(f'- Container volume capacity: {container_size[0] * container_size[1] * container_size[2]}')
    input_md.append(f'- Container weight capacity: {container_weight}')
    input_md.append(f'- Items:')
    input_md.append('')
    input_md.append('| id | weight | volume | rotation | group_id |')
    input_md.append('|----|--------|--------|----------|----------|')
    for i in range(len(items)):
        volume = items[i]['size'][0] * items[i]['size'][1] * items[i]['size'][2]
        rotation = items[i].get('rotation', None)
        input_md.append(f'| {items[i]["id"]} | {items[i]["weight"]} | {volume} | {rotation} | {items[i].get("group_id", None)} |')
    input_md.append('')
    from ortools.sat.python import cp_model
    print (f'Running phase 1 baseline.')
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    # Dump results for initial assignment
    dump_phase1_results(
        solver, status, x, y, group_in_containers, group_ids, group_to_items,
        items, container_size, container_weight, input_md=input_md, filename_prefix='container_bin_packing_result', write_md=False)

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
    # Read ALNS parameters from input file
    alns_params = data.get('alns_params', {})
    num_iterations = alns_params['num_iterations']
    num_remove = alns_params['num_remove']
    time_limit = alns_params['time_limit']
    max_no_improve = alns_params['max_no_improve']
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

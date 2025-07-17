
import json
import sys
import datetime
from ortools.sat.python import cp_model

from step2_container_box_placement_in_container import run as step2_run 

def run(data):
    # Read rotation property (default to 'free' if not present)
    #rotation = data.get('rotation', 'free')


    container_volume = data['container']['size'][0] * data['container']['size'][1] * data['container']['size'][2]   
    container_weight = data['container']['weight']
    item_ids = [item.get('id', i+1) for i, item in enumerate(data['items'])]
    item_volumes = [item['size'][0] * item['size'][1] * item['size'][2] for item in data['items']]
    item_weights = [item['weight'] for item in data['items']]
    item_rotations = [item['rotation'] for item in data['items']]

    item_group_ids = [item.get('group_id') for item in data['items']]
    num_items = len(data['items'])
    step_2_settings_file = data.get('step2_settings_file', None)

    # dump inputs 

    # Prepare input markdown
    input_md = []
    input_md.append('## INPUTS')
    input_md.append(f'- Container volume capacity: {container_volume}')
    input_md.append(f'- Container weight capacity: {container_weight}')
    input_md.append(f'- Items:')
    input_md.append('')
    input_md.append('| id | weight | volume | rotation | group_id |')
    input_md.append('|----|--------|--------|----------|----------|')
    for i in range(num_items):
        input_md.append(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_rotations[i]} | {item_group_ids[i]} |')
    input_md.append('')


    print(f'****************')
    print(f'INPUTS')
    print(f'Container volume capacity: {container_volume}')
    print(f'Container weight capacity: {container_weight}')
    print('Item details:')
    for i in range(num_items):
        print(f'  Item {item_ids[i]}: weight={item_weights[i]}, volume={item_volumes[i]}, rotation={item_rotations[i]}, group_id={item_group_ids[i]}')
    print(f'****************')


    # Check that each box fits in the container (considering rotation)
    for i, item in enumerate(data['items']):
        box_size = item.get('size', None)
        if box_size is None:
            raise ValueError(f"Box size must be specified for item {item_ids[i]}")
        container_size = data['container']['size']
        fits = False
        if item_rotations[i] == 'free':
            # Try all 6 axis-aligned orientations
            from itertools import permutations
            for perm in set(permutations(box_size)):
                if all(perm[d] <= container_size[d] for d in range(3)):
                    fits = True
                    break
        else:
            # Only check the given orientation
            if all(box_size[d] <= container_size[d] for d in range(3)):
                fits = True
        if not fits:
            raise ValueError("Item {} with size {} does not fit in container of size {} (rotation={})".format(item_ids[i], box_size, container_size, rotation))



    # Build group-to-items mapping (excluding None)
    from collections import defaultdict
    group_to_items = defaultdict(list)
    for idx, gid in enumerate(item_group_ids):
        if gid is not None:
            group_to_items[gid].append(idx)


    # Upper bound on containers: one per item (worst case)
    max_containers = num_items

    model = cp_model.CpModel()

    # Variables
    x = {}  # x[i, j] = 1 if item i in container j
    for i in range(num_items):
        for j in range(max_containers):
            x[i, j] = model.NewBoolVar(f'x_{i}_{j}')

    y = [model.NewBoolVar(f'y_{j}') for j in range(max_containers)]  # y[j] = 1 if container j is used

    # Constraints
    # Each item in exactly one container
    for i in range(num_items):
        model.Add(sum(x[i, j] for j in range(max_containers)) == 1)

    # Container capacity constraints
    for j in range(max_containers):
        model.Add(sum(item_volumes[i] * x[i, j] for i in range(num_items)) <= container_volume * y[j])
        model.Add(sum(item_weights[i] * x[i, j] for i in range(num_items)) <= container_weight * y[j])


    # Link y[j] to usage
    for j in range(max_containers):
        for i in range(num_items):
            model.Add(x[i, j] <= y[j])


    # Soft grouping: penalize splitting a group across multiple containers
    group_penalty_lambda = 1  # Penalty weight for splitting a group (can be parameterized)
    group_ids = list(group_to_items.keys())
    group_in_j = {}  # group_in_j[g, j] = 1 if any item of group g is in container j
    group_in_containers = {}  # group_in_containers[g] = number of containers group g is split across
    for g in group_ids:
        for j in range(max_containers):
            group_in_j[g, j] = model.NewBoolVar(f'group_{g}_in_{j}')
            # group_in_j[g, j] is true iff any item of group g is placed in container j
            item_vars = [x[i, j] for i in group_to_items[g]]
            model.AddMaxEquality(group_in_j[g, j], item_vars)
        # group_in_containers[g] = sum_j group_in_j[g, j]
        group_in_containers[g] = model.NewIntVar(1, max_containers, f'group_{g}_num_containers')
        model.Add(group_in_containers[g] == sum(group_in_j[g, j] for j in range(max_containers)))


    # Objective: minimize number of containers used + penalty for group splits
    # For each group, penalize (number of containers used by group - 1)
    group_split_penalty = sum(group_in_containers[g] - 1 for g in group_ids) if group_ids else 0
    model.Minimize(sum(y[j] for j in range(max_containers)) + group_penalty_lambda * group_split_penalty)


    # Solve
    solver = cp_model.CpSolver()
    # solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    # Print model status
    status_dict = {
        cp_model.OPTIMAL: 'OPTIMAL',
        cp_model.FEASIBLE: 'FEASIBLE',
        cp_model.INFEASIBLE: 'INFEASIBLE',
        cp_model.MODEL_INVALID: 'MODEL_INVALID',
        cp_model.UNKNOWN: 'UNKNOWN',
    }
    # Print solver status with color
    status_str = status_dict.get(status, str(status))
    color_map = {
        'OPTIMAL': '\033[92m',      # Green
        'FEASIBLE': '\033[94m',     # Blue
        'INFEASIBLE': '\033[91m',   # Red
        'MODEL_INVALID': '\033[95m',# Magenta
        'UNKNOWN': '\033[93m',     # Yellow
    }
    color = color_map.get(status_str, '\033[0m')
    endc = '\033[0m'
    print(f'Step 1 Solver status: {color}{status_str}{endc}')

    if status == cp_model.INFEASIBLE:
        print('No feasible solution found for step 2.')
        return

    # Prepare output markdown
    output_md = []
    output_md.append('## OUTPUTS')
    output_md.append(f'Step 1 Solver status: {status_dict.get(status, status)}')


    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        min_containers = int(sum(solver.Value(y[j]) for j in range(max_containers)))
        # Compute group splits
        group_splits = {g: solver.Value(group_in_containers[g]) - 1 for g in group_ids}
        total_group_splits = sum(group_splits.values())
        print(f'\nMinimum containers used: {min_containers}')
        print(f'Total group splits (penalized): {total_group_splits}')
        output_md.append(f'- Minimum containers used: {min_containers}')
        output_md.append(f'- Total group splits (penalized): {total_group_splits}')
        output_md.append('')
        # Rebase container numbers
        used_container_indices = [j for j in range(max_containers) if solver.Value(y[j])]
        container_rebase = {old_idx: new_idx+1 for new_idx, old_idx in enumerate(used_container_indices)}
        for old_j in used_container_indices:
            new_j = container_rebase[old_j]
            items_in_container = [i for i in range(num_items) if solver.Value(x[i, old_j])]
            total_weight = sum(item_weights[i] for i in items_in_container)
            total_volume = sum(item_volumes[i] for i in items_in_container)
            pct_weight = 100 * total_weight / container_weight if container_weight > 0 else 0
            pct_volume = 100 * total_volume / container_volume if container_volume > 0 else 0
            output_md.append(f'### Container {new_j}')
            output_md.append('| Item id | Weight | Volume | Group id |')
            output_md.append('|---------|--------|--------|----------|')
            for i in items_in_container:
                output_md.append(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_group_ids[i]} |')
            output_md.append(f'**Total for container {new_j}: weight = {total_weight} ({pct_weight:.1f}% of max), volume = {total_volume} ({pct_volume:.1f}% of max)**\n')
        # Report group splits
        if group_ids:
            output_md.append('### Group Splits')
            output_md.append('| Group id | Containers used | Splits (penalized) | Container numbers |')
            output_md.append('|----------|----------------|--------------------|-------------------|')
            for g in group_ids:
                # Find which rebased containers this group appears in
                containers_for_group = []
                for old_j in used_container_indices:
                    # If any item of group g is in old_j, group appears in this container
                    if any(solver.Value(x[i, old_j]) for i in group_to_items[g]):
                        containers_for_group.append(str(container_rebase[old_j]))
                containers_str = ', '.join(containers_for_group)
                output_md.append(f'| {g} | {solver.Value(group_in_containers[g])} | {group_splits[g]} | {containers_str} |')
            output_md.append('')
        #print(f'Container {new_j}: items {[f"{item_ids[i]}(group_id={item_group_ids[i]})" for i in items_in_container]}, total loaded weight: {total_weight} ({pct_weight:.1f}% of max), total loaded volume: {total_volume} ({pct_volume:.1f}% of max)')
        #print(output_md)

    else:
        print('No solution found.')
        output_md.append('No solution found.')

    # Write markdown file
    now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    md_filename = f'outputs/container_bin_packing_result_{now}.md'
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write('# Container Bin Packing Result\n\n')
        f.write('\n'.join(input_md))
        f.write('\n---\n')
        f.write('\n'.join(output_md))

    # open markdown file in default editor
    import os  
    if sys.platform.startswith('win'):
        os.startfile(os.path.abspath(md_filename))

    # --- Write JSON output file ---
    output_json = {}
    output_json["containers"] = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Use the same container size for all containers (from input, if available)
        container_size = data['container'].get('size', None)
        # If not present, try to infer from volume (cube root), else use None
        if container_size is None:
            raise ValueError("Container size must be specified in input data.")
        # If container size is not provided, we cannot proceed
        # For each used container, build the output structure
        for old_j in used_container_indices:
            new_j = container_rebase[old_j]
            items_in_container = [i for i in range(num_items) if solver.Value(x[i, old_j])]
            container_entry = {
                "id": new_j,
                "size": container_size,
                "boxes": []
            }
            for i in items_in_container:
                # Try to get size and rotation from input, fallback to None/defaults
                box_size = data['items'][i].get('size', None)
                if box_size is None:
                    raise ValueError("Box size must be specified in input data.")
                box_rotation = data['items'][i].get('rotation')
                box_entry = {
                    "id": item_ids[i],
                    "size": box_size,
                    "rotation": box_rotation,
                    "weight": item_weights[i]
                }
                container_entry["boxes"].append(box_entry)
            output_json["containers"].append(container_entry)

    # Write JSON file

    with open(ouput_filename, 'w', encoding='utf-8') as fjson:
        import json as _json
        _json.dump(output_json, fjson, indent=2)
    print(f'JSON results also written to {ouput_filename}')

    # Run step 2: box placement in containers
    if step_2_settings_file is None:
        print('No step 2 settings file specified, skipping step 2.')
    else:
        for container in output_json["containers"]:
            boxes = container.get('boxes', [])
            if not boxes:
                print(f'No boxes in container {container["id"]}, skipping step 2.')
                continue
            print(f'Running step 2 for container {container["id"]} with {len(boxes)} boxes...')     

            status_str2 = step2_run(container["id"],data['container']['size'], boxes, step_2_settings_file)
            if( status_str2 != 'OPTIMAL' and status_str2 != 'FEASIBLE'):
                print(f'Step 2 failed for container {container["id"]}: {status_str2}')
                input("Press any key to continue loop ...")

    input("Press any key to exit ...")  # Keeps the plot open until you press Enter

if __name__ == "__main__": 
    # Get input filename from command line
    if len(sys.argv) < 3:
        print('Usage: python container_bin_packing.py <input_json_file> <output_json_file>')
        sys.exit(1)
    input_filename = sys.argv[1]
    ouput_filename = sys.argv[2]
    # Read input data from JSON file

    with open(input_filename, 'r') as f:
        data = json.load(f)
        run(data)

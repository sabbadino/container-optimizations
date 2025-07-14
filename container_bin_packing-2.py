

import json
import sys
import datetime
from ortools.sat.python import cp_model

# Get input filename from command line
if len(sys.argv) < 2:
    print('Usage: python container_bin_packing.py <input_json_file>')
    sys.exit(1)
input_filename = sys.argv[1]

# Read input data from JSON file
with open(input_filename, 'r') as f:
    data = json.load(f)


container_volume = data['container']['volume']
container_weight = data['container']['weight']
item_ids = [item.get('id', i+1) for i, item in enumerate(data['items'])]
item_volumes = [item['volume'] for item in data['items']]
item_weights = [item['weight'] for item in data['items']]
item_group_ids = [item.get('group_id') for item in data['items']]
num_items = len(data['items'])

# dump inputs 

# Prepare input markdown
input_md = []
input_md.append('## INPUTS')
input_md.append(f'- Container volume capacity: {container_volume}')
input_md.append(f'- Container weight capacity: {container_weight}')
input_md.append(f'- Items:')
input_md.append('')
input_md.append('| id | weight | volume | group_id |')
input_md.append('|----|--------|--------|----------|')
for i in range(num_items):
    input_md.append(f'| {item_ids[i]} | {item_weights[i]} | {item_volumes[i]} | {item_group_ids[i]} |')
input_md.append('')
print(f'****************')
print(f'INPUTS')
print(f'Container volume capacity: {container_volume}')
print(f'Container weight capacity: {container_weight}')
print('Item details:')
for i in range(num_items):
    print(f'  Item {item_ids[i]}: weight={item_weights[i]}, volume={item_volumes[i]}, group_id={item_group_ids[i]}')
print(f'****************')


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

# Grouping constraints: items with same group_id must be in the same container
for group_items in group_to_items.values():
    if len(group_items) > 1:
        for j in range(max_containers):
            # All x[i, j] for i in group_items must be equal for each container j
            first = group_items[0]
            for other in group_items[1:]:
                model.Add(x[first, j] == x[other, j])

# Objective: minimize number of containers used
model.Minimize(sum(y[j] for j in range(max_containers)))


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
print(f'Solver status: {status_dict.get(status, status)}')


# Prepare output markdown
output_md = []
output_md.append('## OUTPUTS')
output_md.append(f'Solver status: {status_dict.get(status, status)}')

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print(f'\nMinimum containers used: {int(solver.ObjectiveValue())}')
    output_md.append(f'- Minimum containers used: {int(solver.ObjectiveValue())}')
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
        print(f'Container {new_j}: items {[f"{item_ids[i]}(group_id={item_group_ids[i]})" for i in items_in_container]}, total loaded weight: {total_weight} ({pct_weight:.1f}% of max), total loaded volume: {total_volume} ({pct_volume:.1f}% of max)')
else:
    print('No solution found.')
    output_md.append('No solution found.')

# Write markdown file
now = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
md_filename = f'container_bin_packing_result_{now}.md'
with open(md_filename, 'w', encoding='utf-8') as f:
    f.write('# Container Bin Packing Result\n\n')
    f.write('\n'.join(input_md))
    f.write('\n---\n')
    f.write('\n'.join(output_md))
print(f'\nResults also written to {md_filename}')

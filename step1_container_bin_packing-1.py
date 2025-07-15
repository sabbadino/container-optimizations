

import json
import sys
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
item_volumes = [item['volume'] for item in data['items']]
item_weights = [item['weight'] for item in data['items']]
num_items = len(data['items'])

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

# Objective: minimize number of containers used
model.Minimize(sum(y[j] for j in range(max_containers)))

# Solve
solver = cp_model.CpSolver()
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

if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    print(f'Container volume capacity: {container_volume}')
    print(f'Container weight capacity: {container_weight}')
    print('Item weights:')
    for i in range(num_items):
        print(f'  Item {i}: weight={item_weights[i]}, volume={item_volumes[i]}')
    print(f'\nMinimum containers used: {int(solver.ObjectiveValue())}')
    for j in range(max_containers):
        if solver.Value(y[j]):
            items_in_container = [i for i in range(num_items) if solver.Value(x[i, j])]
            total_weight = sum(item_weights[i] for i in items_in_container)
            total_volume = sum(item_volumes[i] for i in items_in_container)
            print(f'Container {j}: items {items_in_container}, total loaded weight: {total_weight}, total loaded volume: {total_volume}')
else:
    print('No solution found.')

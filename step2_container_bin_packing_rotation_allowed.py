




import sys
from ortools.sat.python import cp_model
from load_utils import load_data_from_json

# Usage: python container_bin_packing-1-geometry.py <input_json_file>
if len(sys.argv) < 2:
    print("Usage: python container_bin_packing-1-geometry.py <input_json_file>")
    sys.exit(1)

input_file = sys.argv[1]
container, boxes = load_data_from_json(input_file)

# Early check: if total box volume > container volume, exit
container_volume = container[0] * container[1] * container[2]
total_box_volume = sum(box['size'][0] * box['size'][1] * box['size'][2] for box in boxes)
if total_box_volume > container_volume:
    print(f"No solution: total box volume ({total_box_volume}) exceeds container volume ({container_volume}).")
    sys.exit(0)


model = cp_model.CpModel()
n = len(boxes)


# Variables: position of each box (lower-left-bottom corner)
x = [model.NewIntVar(0, container[0], f'x_{i}') for i in range(n)]
y = [model.NewIntVar(0, container[1], f'y_{i}') for i in range(n)]
z = [model.NewIntVar(0, container[2], f'z_{i}') for i in range(n)]


# For each box, determine allowed orientations and create orientation variables
perms_list = []
orient = []
for i, box in enumerate(boxes):
    l0, w0, h0 = box['size']
    rot = box.get('rotation', 'free')
    if rot == 'free':
        perms = [
            (l0, w0, h0), (l0, h0, w0), (w0, l0, h0),
            (w0, h0, l0), (h0, l0, w0), (h0, w0, l0)
        ]
    elif rot == 'z':
        perms = [
            (l0, w0, h0), (w0, l0, h0)
        ]
    else:  # 'none' or unspecified
        perms = [(l0, w0, h0)]
    perms_list.append(perms)
    orient.append([model.NewBoolVar(f'orient_{i}_{k}') for k in range(len(perms))])
    model.Add(sum(orient[-1]) == 1)

# Effective dimensions for each box
l_eff = [model.NewIntVar(0, container[0], f'l_eff_{i}') for i in range(n)]
w_eff = [model.NewIntVar(0, container[1], f'w_eff_{i}') for i in range(n)]
h_eff = [model.NewIntVar(0, container[2], f'h_eff_{i}') for i in range(n)]

# Link orientation to effective dimensions
for i in range(n):
    for k, (l, w, h) in enumerate(perms_list[i]):
        model.Add(l_eff[i] == l).OnlyEnforceIf(orient[i][k])
        model.Add(w_eff[i] == w).OnlyEnforceIf(orient[i][k])
        model.Add(h_eff[i] == h).OnlyEnforceIf(orient[i][k])

# No overlap constraint (manual for 3D, using effective dimensions)
for i in range(n):
    for j in range(i + 1, n):
        # At least one of the following must be true:
        # i is left of j, i is right of j, i is in front of j, i is behind j, i is below j, i is above j
        no_overlap = []
        no_overlap.append(model.NewBoolVar(f'i{i}_left_of_j{j}'))
        model.Add(x[i] + l_eff[i] <= x[j]).OnlyEnforceIf(no_overlap[-1])
        no_overlap.append(model.NewBoolVar(f'i{i}_right_of_j{j}'))
        model.Add(x[j] + l_eff[j] <= x[i]).OnlyEnforceIf(no_overlap[-1])
        no_overlap.append(model.NewBoolVar(f'i{i}_front_of_j{j}'))
        model.Add(y[i] + w_eff[i] <= y[j]).OnlyEnforceIf(no_overlap[-1])
        no_overlap.append(model.NewBoolVar(f'i{i}_behind_of_j{j}'))
        model.Add(y[j] + w_eff[j] <= y[i]).OnlyEnforceIf(no_overlap[-1])
        no_overlap.append(model.NewBoolVar(f'i{i}_below_j{j}'))
        model.Add(z[i] + h_eff[i] <= z[j]).OnlyEnforceIf(no_overlap[-1])
        no_overlap.append(model.NewBoolVar(f'i{i}_above_j{j}'))
        model.Add(z[j] + h_eff[j] <= z[i]).OnlyEnforceIf(no_overlap[-1])
        model.AddBoolOr(no_overlap)

# Inside container (using effective dimensions)
for i in range(n):
    model.Add(x[i] + l_eff[i] <= container[0])
    model.Add(y[i] + w_eff[i] <= container[1])
    model.Add(z[i] + h_eff[i] <= container[2])


# No floating: each box is on the floor or on top of another box (using effective dimensions)
on_floor_vars = []
for i in range(n):
    on_floor = model.NewBoolVar(f'on_floor_{i}')
    on_floor_vars.append(on_floor)
    model.Add(z[i] == 0).OnlyEnforceIf(on_floor)
    on_another = []
    for j in range(n):
        if i == j:
            continue
        above = model.NewBoolVar(f'above_{i}_{j}')
        model.Add(z[i] == z[j] + h_eff[j]).OnlyEnforceIf(above)
        # Must overlap in x and y
        model.Add(x[i] < x[j] + l_eff[j]).OnlyEnforceIf(above)
        model.Add(x[i] + l_eff[i] > x[j]).OnlyEnforceIf(above)
        model.Add(y[i] < y[j] + w_eff[j]).OnlyEnforceIf(above)
        model.Add(y[i] + w_eff[i] > y[j]).OnlyEnforceIf(above)
        on_another.append(above)
    model.AddBoolOr([on_floor] + on_another)

# Prefer boxes on the floor when possible
model.Maximize(sum(on_floor_vars))

# Solve
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30  
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

if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
    for i in range(n):
        # Find which orientation is selected
        orient_val = [solver.Value(orient[i][k]) for k in range(len(orient[i]))]
        orient_idx = orient_val.index(1)
        l, w, h = perms_list[i][orient_idx]
        print(f'Box {i}: pos=({solver.Value(x[i])}, {solver.Value(y[i])}, {solver.Value(z[i])}), size=({l}, {w}, {h}), orientation={orient_idx}, rotation_type={boxes[i].get("rotation", "free")}')

    from visualization_utils import visualize_solution
    visualize_solution(container, boxes, perms_list, orient, x, y, z, solver, n)
else:
    print('No solution found.')

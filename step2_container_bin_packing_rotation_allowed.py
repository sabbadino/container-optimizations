




import sys
from ortools.sat.python import cp_model
from load_utils import load_data_from_json

# Usage: python container_bin_packing-1-geometry.py <input_json_file>
if len(sys.argv) < 2:
    print("Usage: python container_bin_packing-1-geometry.py <input_json_file>")
    sys.exit(1)



input_file = sys.argv[1]
container, boxes, symmetry_mode, max_time = load_data_from_json(input_file)
print(f'symmetry_mode:  {symmetry_mode}')

import time
solver = cp_model.CpSolver()

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



# Symmetry breaking for identical boxes (same size and allowed rotations)
from model_constraints import add_symmetry_breaking_for_identical_boxes
add_symmetry_breaking_for_identical_boxes(model, boxes, x, y, z, symmetry_mode)


from model_constraints import add_no_overlap_constraint
add_no_overlap_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)


from model_constraints import add_inside_container_constraint
add_inside_container_constraint(model, n, x, y, z, l_eff, w_eff, h_eff, container)




from model_constraints import add_no_floating_constraint, get_total_floor_area_covered

# Add no floating constraint
on_floor_vars = add_no_floating_constraint(model, n, x, y, z, l_eff, w_eff, h_eff)
# Maximize total covered floor area
area_vars = get_total_floor_area_covered(model, n, on_floor_vars, l_eff, w_eff, container)
model.Maximize(sum(area_vars))


# Solve

solver.parameters.max_time_in_seconds = max_time
print(f'Solver max_time_in_seconds: {max_time}')
start_time = time.time()
status = solver.Solve(model)
elapsed_time = time.time() - start_time

# Print model status
status_dict = {
    cp_model.OPTIMAL: 'OPTIMAL',
    cp_model.FEASIBLE: 'FEASIBLE',
    cp_model.INFEASIBLE: 'INFEASIBLE',
    cp_model.MODEL_INVALID: 'MODEL_INVALID',
    cp_model.UNKNOWN: 'UNKNOWN',
}

print(f'Solver status: {status_dict.get(status, status)}')
print(f'Solver time: {elapsed_time:.3f} seconds')

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

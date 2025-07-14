


import sys
import json
from ortools.sat.python import cp_model

# Usage: python container_bin_packing-1-geometry.py <input_json_file>
if len(sys.argv) < 2:
    print("Usage: python container_bin_packing-1-geometry.py <input_json_file>")
    sys.exit(1)

input_file = sys.argv[1]
with open(input_file, 'r') as f:
    data = json.load(f)
container = tuple(data['container'])
boxes = [tuple(b) for b in data['boxes']]

# Early check: if total box volume > container volume, exit
container_volume = container[0] * container[1] * container[2]
total_box_volume = sum(l * w * h for (l, w, h) in boxes)
if total_box_volume > container_volume:
    print(f"No solution: total box volume ({total_box_volume}) exceeds container volume ({container_volume}).")
    sys.exit(0)

model = cp_model.CpModel()
n = len(boxes)


# Variables: position of each box (lower-left-bottom corner)
x = [model.NewIntVar(0, container[0], f'x_{i}') for i in range(n)]
y = [model.NewIntVar(0, container[1], f'y_{i}') for i in range(n)]
z = [model.NewIntVar(0, container[2], f'z_{i}') for i in range(n)]

# Orientation variables: 6 possible orientations for each box
orient = [[model.NewBoolVar(f'orient_{i}_{k}') for k in range(6)] for i in range(n)]
for i in range(n):
    model.Add(sum(orient[i]) == 1)

# Effective dimensions for each box
l_eff = [model.NewIntVar(0, container[0], f'l_eff_{i}') for i in range(n)]
w_eff = [model.NewIntVar(0, container[1], f'w_eff_{i}') for i in range(n)]
h_eff = [model.NewIntVar(0, container[2], f'h_eff_{i}') for i in range(n)]

# Link orientation to effective dimensions
for i in range(n):
    l0, w0, h0 = boxes[i]
    perms = [
        (l0, w0, h0), (l0, h0, w0), (w0, l0, h0),
        (w0, h0, l0), (h0, l0, w0), (h0, w0, l0)
    ]
    for k, (l, w, h) in enumerate(perms):
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
solver.parameters.max_time_in_seconds = 20  
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
        orient_val = [solver.Value(orient[i][k]) for k in range(6)]
        orient_idx = orient_val.index(1)
        l0, w0, h0 = boxes[i]
        perms = [
            (l0, w0, h0), (l0, h0, w0), (w0, l0, h0),
            (w0, h0, l0), (h0, l0, w0), (h0, w0, l0)
        ]
        l, w, h = perms[orient_idx]
        print(f'Box {i}: pos=({solver.Value(x[i])}, {solver.Value(y[i])}, {solver.Value(z[i])}), size=({l}, {w}, {h}), orientation={orient_idx}')

    # Visualization
    try:
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except ImportError:
        print("matplotlib is not installed. Skipping visualization.")
        sys.exit(0)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Draw container as wireframe
    cx, cy, cz = container
    r = [0, cx]
    for s, e in [([0,0,0],[cx,0,0]), ([0,0,0],[0,cy,0]), ([0,0,0],[0,0,cz]),
                 ([cx,0,0],[cx,cy,0]), ([cx,0,0],[cx,0,cz]),
                 ([0,cy,0],[cx,cy,0]), ([0,cy,0],[0,cy,cz]),
                 ([0,0,cz],[cx,0,cz]), ([0,0,cz],[0,cy,cz]),
                 ([cx,cy,0],[cx,cy,cz]), ([cx,0,cz],[cx,cy,cz]), ([0,cy,cz],[cx,cy,cz])]:
        ax.plot3D(*zip(s, e), color="black", linewidth=0.5)

    # Draw each box as a colored solid
    import random
    colors = plt.cm.get_cmap('tab20', n)
    for i in range(n):
        xi = solver.Value(x[i])
        yi = solver.Value(y[i])
        zi = solver.Value(z[i])
        orient_val = [solver.Value(orient[i][k]) for k in range(6)]
        orient_idx = orient_val.index(1)
        l0, w0, h0 = boxes[i]
        perms = [
            (l0, w0, h0), (l0, h0, w0), (w0, l0, h0),
            (w0, h0, l0), (h0, l0, w0), (h0, w0, l0)
        ]
        l, w, h = perms[orient_idx]
        # Vertices of the box
        verts = [
            [xi, yi, zi],
            [xi + l, yi, zi],
            [xi + l, yi + w, zi],
            [xi, yi + w, zi],
            [xi, yi, zi + h],
            [xi + l, yi, zi + h],
            [xi + l, yi + w, zi + h],
            [xi, yi + w, zi + h],
        ]
        faces = [
            [verts[0], verts[1], verts[2], verts[3]],
            [verts[4], verts[5], verts[6], verts[7]],
            [verts[0], verts[1], verts[5], verts[4]],
            [verts[2], verts[3], verts[7], verts[6]],
            [verts[1], verts[2], verts[6], verts[5]],
            [verts[4], verts[7], verts[3], verts[0]],
        ]
        box = Poly3DCollection(faces, alpha=0.6, facecolor=colors(i), edgecolor='k')
        ax.add_collection3d(box)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_xlim(0, cx)
    ax.set_ylim(0, cy)
    ax.set_zlim(0, cz)
    ax.set_box_aspect([cx, cy, cz])
    plt.title('3D Container Packing Solution')
    plt.show()
else:
    print('No solution found.')
